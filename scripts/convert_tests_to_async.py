#!/usr/bin/env python3
"""
Script to convert sync EventStore tests to async tests for AsyncioEventStoreDBClient.

This script updates test files to:
1. Add asyncio and AsyncMock imports
2. Convert Mock to AsyncMock for subscriptions
3. Replace __iter__ with __aiter__ and AsyncIteratorMock
4. Add @pytest.mark.asyncio decorator and async def
5. Replace eventstore._consume_events_async() with await eventstore._consume_events_async()
6. Replace mock.ack() with AsyncMock() that supports await
"""

import re
import sys
from pathlib import Path


def convert_test_file(file_path: Path) -> str:
    """Convert a test file from sync to async"""
    content = file_path.read_text()

    # 1. Update imports
    if "from unittest.mock import Mock" in content and "AsyncMock" not in content:
        content = content.replace("from unittest.mock import Mock", "from unittest.mock import Mock, AsyncMock")

    if "import asyncio" not in content:
        # Add asyncio import after other standard library imports
        content = re.sub(r"(import logging\n)", r"import asyncio\n\1", content)

    # 2. Add AsyncIteratorMock class if not present
    if "class AsyncIteratorMock" not in content:
        helper_class = '''

# Helper for async iteration mocking
class AsyncIteratorMock:
    """Mock async iterator for testing async for loops"""

    def __init__(self, items):
        self.items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration

'''
        # Insert before first test class or @dataclass
        content = re.sub(r"(# Test Domain Event|class Test)", helper_class + r"\1", content, count=1)

    # 3. Convert test methods to async
    # Find all test methods and make them async
    def convert_test_method(match):
        indent = match.group(1)
        method_name = match.group(2)
        params = match.group(3)

        # Add @pytest.mark.asyncio decorator
        decorator = f"{indent}@pytest.mark.asyncio\n"
        # Make method async
        method_def = f"{indent}async def {method_name}({params}):"

        return decorator + method_def

    content = re.sub(r"^(\s+)def (test_\w+)\((.*?)\):$", convert_test_method, content, flags=re.MULTILINE)

    # 4. Convert Mock subscriptions to AsyncMock
    # Replace mock_subscription = Mock() with AsyncMock()
    content = re.sub(r"mock_subscription = Mock\(\)", "mock_subscription = AsyncMock()", content)

    # 5. Replace __iter__ with __aiter__ and AsyncIteratorMock
    content = re.sub(r"mock_subscription\.__iter__ = Mock\(return_value=iter\(\[(.*?)\]\)\)", r"mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([\1]))", content)

    # 6. Convert ack/nack to AsyncMock
    content = re.sub(r"mock_subscription\.ack = Mock\(\)", "mock_subscription.ack = AsyncMock()", content)
    content = re.sub(r"mock_subscription\.nack = Mock\(\)", "mock_subscription.nack = AsyncMock()", content)
    content = re.sub(r"mock_subscription\.stop = Mock\(\)", "mock_subscription.stop = AsyncMock()", content)

    # 7. Add await to _consume_events_async calls
    content = re.sub(r"(\s+)eventstore\._consume_events_async\(", r"\1await eventstore._consume_events_async(", content)

    # 8. Fix asyncio.run() calls to just await
    content = re.sub(r"asyncio\.run\(ackable_event\.ack_async\(\)\)", "await ackable_event.ack_async()", content)
    content = re.sub(r"asyncio\.run\(ackable_event\.nack_async\(\)\)", "await ackable_event.nack_async()", content)

    # 9. Fix observe_async calls
    content = re.sub(r"asyncio\.run\(store\.observe_async\(", "await store.observe_async(", content)

    return content


def main():
    """Convert test files"""
    repo_root = Path(__file__).parent.parent
    test_files = [
        repo_root / "tests/cases/test_event_store_tombstone_handling.py",
        repo_root / "tests/cases/test_persistent_subscription_ack_delivery.py",
    ]

    for test_file in test_files:
        if not test_file.exists():
            print(f"Warning: {test_file} not found", file=sys.stderr)
            continue

        print(f"Converting {test_file.name}...")
        converted_content = convert_test_file(test_file)

        # Write back
        test_file.write_text(converted_content)
        print(f"  ✓ Converted {test_file.name}")

    print("\n✅ All test files converted to async")


if __name__ == "__main__":
    main()
