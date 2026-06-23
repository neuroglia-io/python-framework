"""Tests for Conversation building blocks.

Tests cover:
- Message, MessageRole, MessageStatus: LLM message representation
- ToolCall, ToolResult: Tool execution primitives
- ExecutionContext, LlmMessageSnapshot: ReAct loop state
- Session: Session lifecycle tracking

Coverage Target: 90%+
"""

import json
from datetime import datetime, timezone

from neuroglia.data.conversation import (
    ExecutionContext,
    LlmMessageSnapshot,
    Message,
    MessageRole,
    MessageStatus,
    Session,
    ToolCall,
    ToolResult,
)

# =============================================================================
# MessageRole and MessageStatus Tests
# =============================================================================


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_all_roles_exist(self) -> None:
        """Test all message roles are defined."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"

    def test_role_from_string(self) -> None:
        """Test creating role from string value."""
        assert MessageRole("system") == MessageRole.SYSTEM
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT
        assert MessageRole("tool") == MessageRole.TOOL


class TestMessageStatus:
    """Tests for MessageStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all message statuses are defined."""
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.STREAMING.value == "streaming"
        assert MessageStatus.COMPLETED.value == "completed"
        assert MessageStatus.ERROR.value == "error"


# =============================================================================
# ToolCall Tests
# =============================================================================


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_creation(self) -> None:
        """Test creating ToolCall directly."""
        call = ToolCall(
            call_id="call-123",
            tool_name="search",
            arguments={"query": "Python patterns"},
        )

        assert call.call_id == "call-123"
        assert call.tool_name == "search"
        assert call.arguments == {"query": "Python patterns"}

    def test_create_factory(self) -> None:
        """Test create() factory method generates ID."""
        call = ToolCall.create(
            tool_name="calculator",
            arguments={"expression": "2 + 2"},
        )

        assert call.call_id  # Should have generated ID
        assert len(call.call_id) == 36  # UUID format
        assert call.tool_name == "calculator"
        assert call.arguments == {"expression": "2 + 2"}

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        call = ToolCall(
            call_id="call-ser",
            tool_name="analyze",
            arguments={"data": [1, 2, 3]},
        )

        data = call.to_dict()

        assert data["call_id"] == "call-ser"
        assert data["tool_name"] == "analyze"
        assert data["arguments"] == {"data": [1, 2, 3]}

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "call_id": "call-deser",
            "tool_name": "translate",
            "arguments": {"text": "Hello", "target": "es"},
        }

        call = ToolCall.from_dict(data)

        assert call.call_id == "call-deser"
        assert call.tool_name == "translate"
        assert call.arguments == {"text": "Hello", "target": "es"}

    def test_to_openai_format(self) -> None:
        """Test conversion to OpenAI format."""
        call = ToolCall(
            call_id="call-openai",
            tool_name="get_weather",
            arguments={"city": "Seattle"},
        )

        openai = call.to_openai_format()

        assert openai["id"] == "call-openai"
        assert openai["type"] == "function"
        assert openai["function"]["name"] == "get_weather"
        assert json.loads(openai["function"]["arguments"]) == {"city": "Seattle"}

    def test_to_anthropic_format(self) -> None:
        """Test conversion to Anthropic format."""
        call = ToolCall(
            call_id="call-anthropic",
            tool_name="search_docs",
            arguments={"query": "API reference"},
        )

        anthropic = call.to_anthropic_format()

        assert anthropic["type"] == "tool_use"
        assert anthropic["id"] == "call-anthropic"
        assert anthropic["name"] == "search_docs"
        assert anthropic["input"] == {"query": "API reference"}

    def test_to_gemini_format(self) -> None:
        """Test conversion to Gemini format."""
        call = ToolCall(
            call_id="call-gemini",
            tool_name="lookup",
            arguments={"key": "value"},
        )

        gemini = call.to_gemini_format()

        assert "functionCall" in gemini
        assert gemini["functionCall"]["name"] == "lookup"
        assert gemini["functionCall"]["args"] == {"key": "value"}

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        original = ToolCall.create(
            tool_name="complex_tool",
            arguments={"nested": {"data": [1, 2, 3]}, "flag": True},
        )

        data = original.to_dict()
        restored = ToolCall.from_dict(data)

        assert restored.call_id == original.call_id
        assert restored.tool_name == original.tool_name
        assert restored.arguments == original.arguments


# =============================================================================
# ToolResult Tests
# =============================================================================


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_creation_success(self) -> None:
        """Test creating successful ToolResult."""
        result = ToolResult(
            call_id="call-123",
            tool_name="search",
            success=True,
            result={"documents": ["doc1", "doc2"]},
            execution_time_ms=150.5,
        )

        assert result.call_id == "call-123"
        assert result.tool_name == "search"
        assert result.success is True
        assert result.result == {"documents": ["doc1", "doc2"]}
        assert result.error is None
        assert result.execution_time_ms == 150.5

    def test_creation_failure(self) -> None:
        """Test creating failed ToolResult."""
        result = ToolResult(
            call_id="call-fail",
            tool_name="connect",
            success=False,
            result=None,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.result is None
        assert result.error == "Connection timeout"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        result = ToolResult(
            call_id="call-ser",
            tool_name="analyze",
            success=True,
            result={"score": 0.95},
            execution_time_ms=250.0,
        )

        data = result.to_dict()

        assert data["call_id"] == "call-ser"
        assert data["tool_name"] == "analyze"
        assert data["success"] is True
        assert data["result"] == {"score": 0.95}
        assert data["error"] is None
        assert data["execution_time_ms"] == 250.0

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "call_id": "call-deser",
            "tool_name": "validate",
            "success": False,
            "result": None,
            "error": "Validation failed",
            "execution_time_ms": 50.0,
        }

        result = ToolResult.from_dict(data)

        assert result.call_id == "call-deser"
        assert result.tool_name == "validate"
        assert result.success is False
        assert result.error == "Validation failed"

    def test_to_openai_tool_message(self) -> None:
        """Test conversion to OpenAI tool message format."""
        result = ToolResult(
            call_id="call-openai",
            tool_name="get_weather",
            success=True,
            result={"temp": 72, "condition": "sunny"},
        )

        msg = result.to_openai_tool_message()

        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "call-openai"
        assert json.loads(msg["content"]) == {"temp": 72, "condition": "sunny"}

    def test_to_openai_tool_message_error(self) -> None:
        """Test conversion to OpenAI tool message for error."""
        result = ToolResult(
            call_id="call-error",
            tool_name="fetch",
            success=False,
            result=None,
            error="Network error",
        )

        msg = result.to_openai_tool_message()

        assert msg["role"] == "tool"
        assert "Error: Network error" in msg["content"]

    def test_to_anthropic_tool_result_success(self) -> None:
        """Test conversion to Anthropic format for success."""
        result = ToolResult(
            call_id="call-anthropic",
            tool_name="search",
            success=True,
            result={"found": True, "items": ["a", "b"]},
        )

        anthropic = result.to_anthropic_tool_result()

        assert anthropic["type"] == "tool_result"
        assert anthropic["tool_use_id"] == "call-anthropic"
        assert "is_error" not in anthropic

    def test_to_anthropic_tool_result_error(self) -> None:
        """Test conversion to Anthropic format for error."""
        result = ToolResult(
            call_id="call-anthropic-err",
            tool_name="upload",
            success=False,
            result=None,
            error="File too large",
        )

        anthropic = result.to_anthropic_tool_result()

        assert anthropic["type"] == "tool_result"
        assert anthropic["is_error"] is True
        assert anthropic["content"] == "File too large"

    def test_to_gemini_function_response(self) -> None:
        """Test conversion to Gemini format."""
        result = ToolResult(
            call_id="call-gemini",
            tool_name="lookup",
            success=True,
            result={"value": 42},
        )

        gemini = result.to_gemini_function_response()

        assert "functionResponse" in gemini
        assert gemini["functionResponse"]["name"] == "lookup"
        assert gemini["functionResponse"]["response"]["result"] == {"value": 42}

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        original = ToolResult(
            call_id="call-rt",
            tool_name="process",
            success=True,
            result={"complex": {"nested": [1, 2, 3]}},
            execution_time_ms=175.25,
        )

        data = original.to_dict()
        restored = ToolResult.from_dict(data)

        assert restored.call_id == original.call_id
        assert restored.tool_name == original.tool_name
        assert restored.success == original.success
        assert restored.result == original.result
        assert restored.execution_time_ms == original.execution_time_ms


# =============================================================================
# Message Tests
# =============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_user_message(self) -> None:
        """Test factory for user messages."""
        msg = Message.create_user_message("Hello, how can you help?")

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, how can you help?"
        assert msg.status == MessageStatus.COMPLETED
        assert msg.tool_calls == []
        assert msg.tool_results == []
        assert msg.id  # Should have generated ID

    def test_create_user_message_with_metadata(self) -> None:
        """Test user message factory with metadata."""
        msg = Message.create_user_message("Test", source="web", priority=1)

        assert msg.metadata == {"source": "web", "priority": 1}

    def test_create_assistant_message(self) -> None:
        """Test factory for assistant messages."""
        msg = Message.create_assistant_message("I can help with that!")

        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "I can help with that!"
        assert msg.tool_calls == []

    def test_create_assistant_message_with_tool_calls(self) -> None:
        """Test assistant message factory with tool calls."""
        tool_call = ToolCall.create("search", {"query": "test"})
        msg = Message.create_assistant_message(
            "Let me search for that.",
            tool_calls=[tool_call],
        )

        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].tool_name == "search"

    def test_create_system_message(self) -> None:
        """Test factory for system messages."""
        msg = Message.create_system_message("You are a helpful assistant.")

        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are a helpful assistant."

    def test_create_tool_message(self) -> None:
        """Test factory for tool messages."""
        result = ToolResult(
            call_id="call-tool",
            tool_name="search",
            success=True,
            result={"found": True},
        )
        msg = Message.create_tool_message(result)

        assert msg.role == MessageRole.TOOL
        assert len(msg.tool_results) == 1
        assert msg.metadata["tool_call_id"] == "call-tool"
        assert msg.metadata["tool_name"] == "search"

    def test_create_tool_message_error(self) -> None:
        """Test tool message factory with error result."""
        result = ToolResult(
            call_id="call-err",
            tool_name="connect",
            success=False,
            result=None,
            error="Connection failed",
        )
        msg = Message.create_tool_message(result)

        assert "Error: Connection failed" in msg.content

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        msg = Message.create_user_message("Test message")

        data = msg.to_dict()

        assert data["id"] == msg.id
        assert data["role"] == "user"
        assert data["content"] == "Test message"
        assert data["status"] == "completed"
        assert "created_at" in data
        assert data["tool_calls"] == []
        assert data["tool_results"] == []

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "msg-deser",
            "role": "assistant",
            "content": "Deserialized message",
            "created_at": now.isoformat(),
            "status": "completed",
            "tool_calls": [],
            "tool_results": [],
            "metadata": {"test": True},
        }

        msg = Message.from_dict(data)

        assert msg.id == "msg-deser"
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Deserialized message"
        assert msg.metadata == {"test": True}

    def test_from_dict_with_tool_calls(self) -> None:
        """Test deserialization with tool calls."""
        now = datetime.now(timezone.utc)
        data = {
            "id": "msg-tools",
            "role": "assistant",
            "content": "Using tools",
            "created_at": now.isoformat(),
            "status": "completed",
            "tool_calls": [{"call_id": "call-1", "tool_name": "search", "arguments": {}}],
            "tool_results": [],
            "metadata": {},
        }

        msg = Message.from_dict(data)

        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].tool_name == "search"

    def test_to_openai_format_user(self) -> None:
        """Test OpenAI format for user message."""
        msg = Message.create_user_message("Hello")

        openai = msg.to_openai_format()

        assert openai["role"] == "user"
        assert openai["content"] == "Hello"

    def test_to_openai_format_assistant_with_tools(self) -> None:
        """Test OpenAI format for assistant with tool calls."""
        tool_call = ToolCall.create("search", {"q": "test"})
        msg = Message.create_assistant_message("Searching...", tool_calls=[tool_call])

        openai = msg.to_openai_format()

        assert openai["role"] == "assistant"
        assert len(openai["tool_calls"]) == 1

    def test_to_openai_format_tool(self) -> None:
        """Test OpenAI format for tool message."""
        result = ToolResult(
            call_id="call-openai",
            tool_name="search",
            success=True,
            result={"data": "found"},
        )
        msg = Message.create_tool_message(result)

        openai = msg.to_openai_format()

        assert openai["role"] == "tool"
        assert openai["tool_call_id"] == "call-openai"

    def test_to_anthropic_format_user(self) -> None:
        """Test Anthropic format for user message."""
        msg = Message.create_user_message("Hello")

        anthropic = msg.to_anthropic_format()

        assert anthropic["role"] == "user"
        assert anthropic["content"] == "Hello"

    def test_to_anthropic_format_system(self) -> None:
        """Test Anthropic format for system message (special handling)."""
        msg = Message.create_system_message("You are helpful.")

        anthropic = msg.to_anthropic_format()

        # Anthropic handles system messages differently
        assert "_anthropic_system" in anthropic
        assert anthropic["_anthropic_system"] == "You are helpful."

    def test_to_gemini_format_user(self) -> None:
        """Test Gemini format for user message."""
        msg = Message.create_user_message("Hello")

        gemini = msg.to_gemini_format()

        assert gemini["role"] == "user"
        assert gemini["parts"][0]["text"] == "Hello"

    def test_to_gemini_format_assistant(self) -> None:
        """Test Gemini format for assistant message."""
        msg = Message.create_assistant_message("Hello back!")

        gemini = msg.to_gemini_format()

        assert gemini["role"] == "model"  # Gemini uses "model" not "assistant"

    def test_to_ollama_format(self) -> None:
        """Test Ollama format (should be same as OpenAI)."""
        msg = Message.create_user_message("Hello")

        ollama = msg.to_ollama_format()
        openai = msg.to_openai_format()

        assert ollama == openai

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        tool_call = ToolCall.create("search", {"query": "test"})
        original = Message.create_assistant_message(
            "Searching...",
            tool_calls=[tool_call],
            custom_field="value",
        )

        data = original.to_dict()
        restored = Message.from_dict(data)

        assert restored.id == original.id
        assert restored.role == original.role
        assert restored.content == original.content
        assert len(restored.tool_calls) == len(original.tool_calls)


# =============================================================================
# LlmMessageSnapshot Tests
# =============================================================================


class TestLlmMessageSnapshot:
    """Tests for LlmMessageSnapshot dataclass."""

    def test_creation_simple(self) -> None:
        """Test creating simple snapshot."""
        snapshot = LlmMessageSnapshot(
            role="user",
            content="Hello",
        )

        assert snapshot.role == "user"
        assert snapshot.content == "Hello"
        assert snapshot.tool_calls == []
        assert snapshot.tool_call_id is None
        assert snapshot.name is None

    def test_creation_with_tool_calls(self) -> None:
        """Test creating snapshot with tool calls."""
        snapshot = LlmMessageSnapshot(
            role="assistant",
            content="Searching...",
            tool_calls=[{"id": "call-1", "name": "search"}],
        )

        assert snapshot.tool_calls == [{"id": "call-1", "name": "search"}]

    def test_creation_tool_response(self) -> None:
        """Test creating snapshot for tool response."""
        snapshot = LlmMessageSnapshot(
            role="tool",
            content='{"result": "found"}',
            tool_call_id="call-1",
            name="search",
        )

        assert snapshot.tool_call_id == "call-1"
        assert snapshot.name == "search"

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        snapshot = LlmMessageSnapshot(
            role="assistant",
            content="Test",
            tool_calls=[{"test": True}],
        )

        data = snapshot.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "Test"
        assert data["tool_calls"] == [{"test": True}]

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "role": "user",
            "content": "Hello",
            "tool_calls": [],
            "tool_call_id": None,
            "name": None,
        }

        snapshot = LlmMessageSnapshot.from_dict(data)

        assert snapshot.role == "user"
        assert snapshot.content == "Hello"

    def test_to_openai_format(self) -> None:
        """Test conversion to OpenAI format."""
        snapshot = LlmMessageSnapshot(
            role="assistant",
            content="Response",
            tool_calls=[{"id": "call-1"}],
        )

        openai = snapshot.to_openai_format()

        assert openai["role"] == "assistant"
        assert openai["content"] == "Response"
        assert openai["tool_calls"] == [{"id": "call-1"}]

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        original = LlmMessageSnapshot(
            role="tool",
            content="Result data",
            tool_call_id="call-rt",
            name="process",
        )

        data = original.to_dict()
        restored = LlmMessageSnapshot.from_dict(data)

        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.tool_call_id == original.tool_call_id
        assert restored.name == original.name


# =============================================================================
# ExecutionContext Tests
# =============================================================================


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_creation_defaults(self) -> None:
        """Test creation with default values."""
        context = ExecutionContext()

        assert context.message_snapshot == []
        assert context.iteration == 0
        assert context.max_iterations == 50
        assert context.tools_called == 0
        assert context.pending_tool_call is None
        assert context.suspended_at is None
        assert context.suspension_reason is None
        assert context.started_at is None
        assert context.timeout_seconds == 300

    def test_creation_custom(self) -> None:
        """Test creation with custom values."""
        now = datetime.now(timezone.utc)
        context = ExecutionContext(
            max_iterations=100,
            timeout_seconds=600,
            started_at=now,
        )

        assert context.max_iterations == 100
        assert context.timeout_seconds == 600
        assert context.started_at == now

    def test_is_suspended(self) -> None:
        """Test is_suspended() method."""
        context = ExecutionContext()
        assert context.is_suspended() is False

        context.suspended_at = datetime.now(timezone.utc)
        assert context.is_suspended() is True

    def test_can_continue(self) -> None:
        """Test can_continue() method."""
        context = ExecutionContext(max_iterations=10)

        assert context.can_continue() is True

        context.iteration = 10
        assert context.can_continue() is False

        context.iteration = 5
        assert context.can_continue() is True

    def test_is_timed_out_not_started(self) -> None:
        """Test is_timed_out() when not started."""
        context = ExecutionContext()
        assert context.is_timed_out() is False

    def test_is_timed_out_within_limit(self) -> None:
        """Test is_timed_out() within timeout."""
        context = ExecutionContext(
            timeout_seconds=300,
            started_at=datetime.now(timezone.utc),
        )
        assert context.is_timed_out() is False

    def test_add_message(self) -> None:
        """Test add_message() method."""
        context = ExecutionContext()

        context.add_message("user", "Hello")
        context.add_message(
            "assistant",
            "Hi there",
            tool_calls=[{"id": "call-1"}],
        )
        context.add_message(
            "tool",
            '{"result": "data"}',
            tool_call_id="call-1",
            name="search",
        )

        assert len(context.message_snapshot) == 3
        assert context.message_snapshot[0].role == "user"
        assert context.message_snapshot[1].tool_calls == [{"id": "call-1"}]
        assert context.message_snapshot[2].tool_call_id == "call-1"

    def test_get_messages_for_llm(self) -> None:
        """Test get_messages_for_llm() method."""
        context = ExecutionContext()
        context.add_message("system", "You are helpful.")
        context.add_message("user", "Hello")

        messages = context.get_messages_for_llm()

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_suspend(self) -> None:
        """Test suspend() method."""
        context = ExecutionContext()
        pending_call = {"call_id": "call-pending", "tool_name": "confirm"}

        context.suspend("client_confirmation_required", pending_call)

        assert context.suspended_at is not None
        assert context.suspension_reason == "client_confirmation_required"
        assert context.pending_tool_call == pending_call

    def test_resume(self) -> None:
        """Test resume() method."""
        context = ExecutionContext()
        context.suspend("waiting", {"call": "pending"})

        context.resume()

        assert context.suspended_at is None
        assert context.suspension_reason is None
        assert context.pending_tool_call is None

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        context = ExecutionContext(
            max_iterations=75,
            timeout_seconds=450,
            started_at=now,
        )
        context.iteration = 5
        context.tools_called = 3
        context.add_message("user", "Test")

        data = context.to_dict()

        assert data["iteration"] == 5
        assert data["max_iterations"] == 75
        assert data["tools_called"] == 3
        assert data["timeout_seconds"] == 450
        assert data["started_at"] == now.isoformat()
        assert len(data["message_snapshot"]) == 1

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "message_snapshot": [{"role": "user", "content": "Hi", "tool_calls": []}],
            "iteration": 10,
            "max_iterations": 100,
            "tools_called": 5,
            "pending_tool_call": None,
            "suspended_at": None,
            "suspension_reason": None,
            "started_at": now.isoformat(),
            "timeout_seconds": 600,
        }

        context = ExecutionContext.from_dict(data)

        assert len(context.message_snapshot) == 1
        assert context.iteration == 10
        assert context.max_iterations == 100
        assert context.tools_called == 5
        assert context.started_at == now

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        original = ExecutionContext(
            max_iterations=75,
            timeout_seconds=450,
            started_at=now,
        )
        original.iteration = 12
        original.tools_called = 7
        original.add_message("user", "Test message")
        original.suspend("waiting", {"call": "test"})

        data = original.to_dict()
        restored = ExecutionContext.from_dict(data)

        assert restored.iteration == original.iteration
        assert restored.max_iterations == original.max_iterations
        assert restored.tools_called == original.tools_called
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.started_at == original.started_at
        assert restored.suspension_reason == original.suspension_reason
        assert len(restored.message_snapshot) == len(original.message_snapshot)


# =============================================================================
# Session Tests
# =============================================================================


class TestSession:
    """Tests for Session dataclass."""

    def test_creation_pending(self) -> None:
        """Test creating pending session."""
        now = datetime.now(timezone.utc)
        session = Session(
            session_id="session-123",
            status="pending",
            created_at=now,
        )

        assert session.session_id == "session-123"
        assert session.status == "pending"
        assert session.created_at == now
        assert session.started_at is None
        assert session.paused_at is None
        assert session.completed_at is None
        assert session.execution_context is None
        assert session.accumulated_pause_ms == 0

    def test_creation_active(self) -> None:
        """Test creating active session."""
        now = datetime.now(timezone.utc)
        session = Session(
            session_id="session-active",
            status="active",
            created_at=now,
            started_at=now,
        )

        assert session.status == "active"
        assert session.started_at == now

    def test_is_active(self) -> None:
        """Test is_active() method."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="active", created_at=now)
        assert session.is_active() is True

        session.status = "paused"
        assert session.is_active() is False

    def test_is_paused(self) -> None:
        """Test is_paused() method."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="paused", created_at=now)
        assert session.is_paused() is True

        session.status = "active"
        assert session.is_paused() is False

    def test_is_completed(self) -> None:
        """Test is_completed() method."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="completed", created_at=now)
        assert session.is_completed() is True

        session.status = "terminated"
        assert session.is_completed() is True

        session.status = "active"
        assert session.is_completed() is False

    def test_is_pending(self) -> None:
        """Test is_pending() method."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="pending", created_at=now)
        assert session.is_pending() is True

        session.status = "active"
        assert session.is_pending() is False

    def test_can_resume(self) -> None:
        """Test can_resume() method."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="paused", created_at=now)
        assert session.can_resume() is True

        session.status = "active"
        assert session.can_resume() is False

    def test_get_duration_ms_not_started(self) -> None:
        """Test get_duration_ms() when not started."""
        now = datetime.now(timezone.utc)
        session = Session(session_id="s1", status="pending", created_at=now)
        assert session.get_duration_ms() is None

    def test_get_duration_ms_active(self) -> None:
        """Test get_duration_ms() for active session."""
        now = datetime.now(timezone.utc)
        session = Session(
            session_id="s1",
            status="active",
            created_at=now,
            started_at=now,
        )

        duration = session.get_duration_ms()
        assert duration is not None
        assert duration >= 0  # Should be very small but non-negative

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        now = datetime.now(timezone.utc)
        session = Session(
            session_id="session-ser",
            status="active",
            created_at=now,
            started_at=now,
            accumulated_pause_ms=1000,
        )

        data = session.to_dict()

        assert data["session_id"] == "session-ser"
        assert data["status"] == "active"
        assert data["created_at"] == now.isoformat()
        assert data["started_at"] == now.isoformat()
        assert data["accumulated_pause_ms"] == 1000
        assert data["execution_context"] is None

    def test_to_dict_with_execution_context(self) -> None:
        """Test serialization with execution context."""
        now = datetime.now(timezone.utc)
        context = ExecutionContext(max_iterations=25)
        context.add_message("user", "Hello")

        session = Session(
            session_id="session-ctx",
            status="active",
            created_at=now,
            started_at=now,
            execution_context=context,
        )

        data = session.to_dict()

        assert data["execution_context"] is not None
        assert data["execution_context"]["max_iterations"] == 25

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "session_id": "session-deser",
            "status": "completed",
            "created_at": now.isoformat(),
            "started_at": now.isoformat(),
            "paused_at": None,
            "completed_at": now.isoformat(),
            "execution_context": None,
            "accumulated_pause_ms": 500,
        }

        session = Session.from_dict(data)

        assert session.session_id == "session-deser"
        assert session.status == "completed"
        assert session.completed_at == now
        assert session.accumulated_pause_ms == 500

    def test_from_dict_with_execution_context(self) -> None:
        """Test deserialization with execution context."""
        now = datetime.now(timezone.utc)
        data = {
            "session_id": "session-ctx-deser",
            "status": "active",
            "created_at": now.isoformat(),
            "started_at": now.isoformat(),
            "paused_at": None,
            "completed_at": None,
            "execution_context": {
                "message_snapshot": [],
                "iteration": 5,
                "max_iterations": 50,
                "tools_called": 2,
                "pending_tool_call": None,
                "suspended_at": None,
                "suspension_reason": None,
                "started_at": now.isoformat(),
                "timeout_seconds": 300,
            },
            "accumulated_pause_ms": 0,
        }

        session = Session.from_dict(data)

        assert session.execution_context is not None
        assert session.execution_context.iteration == 5
        assert session.execution_context.tools_called == 2

    def test_round_trip_serialization(self) -> None:
        """Test serialization round-trip preserves data."""
        now = datetime.now(timezone.utc)
        context = ExecutionContext(max_iterations=30)
        context.iteration = 10

        original = Session(
            session_id="session-rt",
            status="active",
            created_at=now,
            started_at=now,
            execution_context=context,
            accumulated_pause_ms=2500,
        )

        data = original.to_dict()
        restored = Session.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.accumulated_pause_ms == original.accumulated_pause_ms
        assert restored.execution_context is not None
        assert restored.execution_context.iteration == 10
