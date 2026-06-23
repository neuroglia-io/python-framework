"""
Portable test demonstrating kurrentdbclient AsyncPersistentSubscription bug.

**Bug Description:**
AsyncPersistentSubscription.init() doesn't propagate subscription_id to _read_reqs,
causing ACKs to be sent with empty subscription_id, which EventStoreDB/KurrentDB ignores.

**Expected Behavior:**
After calling subscription.init(), the _read_reqs.subscription_id should equal
the subscription's _subscription_id (encoded to bytes).

**Actual Behavior (without patch):**
_read_reqs.subscription_id remains empty (b""), causing ACKs to fail silently.

**Impact:**
- Events are redelivered every message_timeout seconds
- Checkpoint never advances in EventStoreDB/KurrentDB
- Events eventually get parked after maxRetryCount attempts
- Read models process the same event multiple times

**Affected Versions:**
- kurrentdbclient: 1.1.1 (and likely all versions)
- esdbclient: 1.1.7 (former package name, same codebase)

**Upstream Issue:**
To be reported to: https://github.com/pyeventsourcing/kurrentdb-client

**Environment:**
- Python: 3.9+
- kurrentdbclient: 1.1.2
- EventStoreDB/KurrentDB: 23.10+ (any version supporting persistent subscriptions)

**How to Run:**
    # As a pytest test
    pytest tests/cases/test_kurrentdb_subscription_id_bug.py -v -s

    # As a standalone script
    python tests/cases/test_kurrentdb_subscription_id_bug.py
"""

import inspect

import pytest


class TestKurrentDBSubscriptionIdBug:
    """
    Test suite demonstrating the subscription_id propagation bug in kurrentdbclient.

    This test directly inspects the kurrentdbclient source code to demonstrate
    the difference between the sync and async subscription implementations.
    """

    @pytest.mark.asyncio
    async def test_compare_sync_vs_async_subscription_initialization(self):
        """
        Compare sync vs async subscription initialization to show the discrepancy.

        **Key Finding:**
        PersistentSubscription.__init__() (sync) has this line:
            self._read_reqs.subscription_id = subscription_id.encode()

        But AsyncPersistentSubscription.init() (async) is missing it!

        This test demonstrates the difference by inspecting the source code.

        **This is a PORTABLE TEST** - it can be run anywhere kurrentdbclient is installed.
        """
        try:
            from kurrentdbclient.persistent import (
                AsyncPersistentSubscription,
                PersistentSubscription,
            )
        except ImportError:
            pytest.skip("kurrentdbclient not installed")

        # Inspect the sync version's __init__
        sync_init_source = inspect.getsource(PersistentSubscription.__init__)

        # Check if sync version has the subscription_id propagation
        has_sync_propagation = "_read_reqs.subscription_id" in sync_init_source

        # Inspect the async version's init
        async_init_source = inspect.getsource(AsyncPersistentSubscription.init)

        # Check if async version has the subscription_id propagation
        has_async_propagation = "_read_reqs.subscription_id" in async_init_source

        # Report findings
        print("\n" + "=" * 80)
        print("KURRENTDBCLIENT SUBSCRIPTION_ID PROPAGATION ANALYSIS")
        print("=" * 80)
        print(f"\nSync PersistentSubscription.__init__():")
        print(f"  - Propagates subscription_id to _read_reqs: {has_sync_propagation}")

        print(f"\nAsync AsyncPersistentSubscription.init():")
        print(f"  - Propagates subscription_id to _read_reqs: {has_async_propagation}")

        if has_sync_propagation and not has_async_propagation:
            print("\n⚠️  BUG CONFIRMED:")
            print("   Sync version propagates subscription_id, but async version doesn't!")
            print("   This causes ACKs to fail in async persistent subscriptions.")
            print("\n   Expected code in AsyncPersistentSubscription.init():")
            print("       self._read_reqs.subscription_id = self._subscription_id.encode()")
            print("\n   Impact:")
            print("   - ACKs sent with empty subscription_id")
            print("   - EventStoreDB/KurrentDB ignores these ACKs")
            print("   - Events redelivered every message_timeout seconds")
            print("   - Checkpoint never advances")
            print("   - Events eventually parked after maxRetryCount")
        elif has_async_propagation:
            print("\n✅ BUG FIXED:")
            print("   Async version now propagates subscription_id correctly!")
            print("   The Neuroglia patch may no longer be necessary.")
        else:
            print("\n⚠️  UNEXPECTED:")
            print("   Neither version propagates subscription_id (code may have been refactored)")

        print("=" * 80 + "\n")

        # Assert that the bug exists (or has been fixed upstream)
        if not has_async_propagation:
            pytest.fail(
                "BUG REPRODUCED: AsyncPersistentSubscription.init() does not propagate subscription_id to _read_reqs!\n"
                "\n"
                "This is a critical bug that causes ACKs to fail silently.\n"
                "\n"
                "Expected code in AsyncPersistentSubscription.init():\n"
                "    self._read_reqs.subscription_id = self._subscription_id.encode()\n"
                "\n"
                "Without this, EventStoreDB/KurrentDB ignores ACKs, causing:\n"
                "  - Events redelivered every message_timeout seconds\n"
                "  - Checkpoint never advances\n"
                "  - Events eventually parked after maxRetryCount\n"
                "  - Read models process events multiple times\n"
                "\n"
                "The sync version (PersistentSubscription.__init__) HAS this code,\n"
                "proving it's an oversight in the async implementation."
            )
        else:
            print("✅ Bug appears to be fixed in this version of kurrentdbclient!")
            print("   You may no longer need the Neuroglia patch.")

    @pytest.mark.asyncio
    async def test_show_missing_line_in_async_init(self):
        """
        Show the exact line that's missing in AsyncPersistentSubscription.init().

        This test prints the relevant source code sections to make the bug obvious.
        """
        try:
            from kurrentdbclient.persistent import (
                AsyncPersistentSubscription,
                PersistentSubscription,
            )
        except ImportError:
            pytest.skip("kurrentdbclient not installed")

        print("\n" + "=" * 80)
        print("SOURCE CODE COMPARISON")
        print("=" * 80)

        # Show sync version
        print("\n📄 PersistentSubscription.__init__() [WORKING]:")
        print("-" * 80)
        sync_source = inspect.getsource(PersistentSubscription.__init__)
        # Find and highlight the key line
        for i, line in enumerate(sync_source.split("\n"), 1):
            if "_read_reqs.subscription_id" in line:
                print(f"  {i:3d} >>> {line}  <<<  ✅ KEY LINE PRESENT")
            elif line.strip() and not line.strip().startswith("#"):
                print(f"  {i:3d}     {line}")

        # Show async version
        print("\n📄 AsyncPersistentSubscription.init() [BROKEN]:")
        print("-" * 80)
        async_source = inspect.getsource(AsyncPersistentSubscription.init)
        has_key_line = False
        for i, line in enumerate(async_source.split("\n"), 1):
            if "_read_reqs.subscription_id" in line:
                print(f"  {i:3d} >>> {line}  <<<  ✅ KEY LINE PRESENT")
                has_key_line = True
            elif line.strip() and not line.strip().startswith("#"):
                print(f"  {i:3d}     {line}")

        if not has_key_line:
            print("\n  ❌ KEY LINE MISSING: self._read_reqs.subscription_id = self._subscription_id.encode()")
            print("     This line must be added to fix ACK delivery!")

        print("=" * 80 + "\n")

        # Check if bug exists
        if not has_key_line:
            pytest.fail("The critical line is MISSING from AsyncPersistentSubscription.init():\n" "    self._read_reqs.subscription_id = self._subscription_id.encode()\n" "\n" "This must be added (likely after 'await self._init()') to fix ACK delivery.")


class TestACKDeliveryDemonstration:
    """
    Documentation class explaining the bug's practical impact.

    The bug (now fixed in kurrentdbclient 1.1.2) caused the following issues:

    1. **Symptom**: Events redelivered every message_timeout seconds (default 30s)
    2. **Root Cause**: _read_reqs.subscription_id was empty (b"")
    3. **Impact**: EventStoreDB/KurrentDB ignored ACKs without subscription_id
    4. **Result**:
       - Checkpoint never advanced
       - Events eventually parked after maxRetryCount
       - Read models processed same events multiple times

    **The Fix** (now in kurrentdbclient 1.1.2, line 20 of AsyncPersistentSubscription.init()):
        self._read_reqs.subscription_id = subscription_id.encode()

    This test class serves as documentation of the historical issue.
    """


# Standalone test runner for sharing with maintainers
if __name__ == "__main__":
    """
    Run this test standalone to demonstrate the bug to kurrentdbclient maintainers.

    Usage:
        python test_kurrentdb_subscription_id_bug.py

    Requirements:
        pip install pytest pytest-asyncio kurrentdbclient
    """
    import sys

    print("=" * 80)
    print("KURRENTDBCLIENT SUBSCRIPTION_ID BUG REPRODUCTION TEST")
    print("=" * 80)
    print("\nThis test demonstrates the AsyncPersistentSubscription.init() bug")
    print("where subscription_id is not propagated to _read_reqs.\n")

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])

    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
        print("\nThe bug appears to be FIXED in your version of kurrentdbclient!")
        print("The patch in Neuroglia may no longer be necessary.")
    else:
        print("❌ TESTS FAILED")
        print("\nThe bug is PRESENT in your version of kurrentdbclient.")
        print("\nWorkaround: Apply the patch in neuroglia.data.infrastructure.event_sourcing.patches")
        print("Upstream fix needed: AsyncPersistentSubscription.init() should include:")
        print("    self._read_reqs.subscription_id = self._subscription_id.encode()")
    print("=" * 80 + "\n")

    sys.exit(exit_code)
