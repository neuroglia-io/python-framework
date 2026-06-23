"""Message value object for LLM conversations.

Provides a universal message representation compatible with
OpenAI, Anthropic, Google Gemini, and Ollama formats.

Architecture:
    This is a VALUE OBJECT, not an aggregate. Services extend or
    compose with this to add domain-specific fields.

    Used by:
    - Agent-Host: In Conversation aggregate for user interactions
    - Agent-Runtime: In AgentTask's ExecutionContext for ReAct loops

Examples:
    ```python
    from neuroglia.data.conversation import Message, MessageRole

    # Create user message
    user_msg = Message.create_user_message("Hello, how can you help?")

    # Create assistant message with tool calls
    assistant_msg = Message.create_assistant_message(
        content="I'll search for that information.",
        tool_calls=[ToolCall.create("search", {"query": "info"})]
    )

    # Convert to LLM provider format
    openai_format = assistant_msg.to_openai_format()
    anthropic_format = assistant_msg.to_anthropic_format()
    ```
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neuroglia.data.conversation.tool_call import ToolCall, ToolResult


class MessageRole(str, Enum):
    """Universal message roles for LLM conversations.

    Compatible with all major LLM providers.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageStatus(str, Enum):
    """Processing status of a message.

    Tracks the message lifecycle during streaming and processing.
    """

    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Message:
    """Universal message representation for LLM conversations.

    This is a VALUE OBJECT, not an aggregate. Services extend or
    compose with this to add domain-specific fields.

    Attributes:
        id: Unique message identifier
        role: Message role (system, user, assistant, tool)
        content: Text content of the message
        created_at: Timestamp when message was created
        status: Processing status
        tool_calls: List of tool call requests (for assistant messages)
        tool_results: List of tool execution results (for tool messages)
        metadata: Additional metadata for extensions

    Examples:
        ```python
        # Simple message creation
        msg = Message.create_user_message("Hello!")

        # Assistant with tool calls
        msg = Message.create_assistant_message(
            content="Let me search...",
            tool_calls=[ToolCall.create("search", {"q": "test"})]
        )

        # Convert for OpenAI
        openai_msg = msg.to_openai_format()
        ```
    """

    id: str
    role: MessageRole
    content: str
    created_at: datetime
    status: MessageStatus = MessageStatus.COMPLETED
    tool_calls: list["ToolCall"] = field(default_factory=list)
    tool_results: list["ToolResult"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_user_message(cls, content: str, **metadata: Any) -> "Message":
        """Factory for user messages.

        Args:
            content: The user's message text
            **metadata: Additional metadata to attach

        Returns:
            A new Message with role=USER
        """
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=metadata,
        )

    @classmethod
    def create_assistant_message(
        cls,
        content: str,
        tool_calls: list["ToolCall"] | None = None,
        **metadata: Any,
    ) -> "Message":
        """Factory for assistant messages.

        Args:
            content: The assistant's response text
            tool_calls: Optional list of tool call requests
            **metadata: Additional metadata to attach

        Returns:
            A new Message with role=ASSISTANT
        """
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=datetime.now(timezone.utc),
            tool_calls=tool_calls or [],
            metadata=metadata,
        )

    @classmethod
    def create_system_message(cls, content: str, **metadata: Any) -> "Message":
        """Factory for system messages.

        Args:
            content: The system instruction text
            **metadata: Additional metadata to attach

        Returns:
            A new Message with role=SYSTEM
        """
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.SYSTEM,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=metadata,
        )

    @classmethod
    def create_tool_message(
        cls,
        tool_result: "ToolResult",
        **metadata: Any,
    ) -> "Message":
        """Factory for tool response messages.

        Args:
            tool_result: The result from tool execution
            **metadata: Additional metadata to attach

        Returns:
            A new Message with role=TOOL
        """
        content = json.dumps(tool_result.result) if tool_result.success else f"Error: {tool_result.error}"
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.TOOL,
            content=content,
            created_at=datetime.now(timezone.utc),
            tool_results=[tool_result],
            metadata={
                "tool_call_id": tool_result.call_id,
                "tool_name": tool_result.tool_name,
                **metadata,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Deserialize from dictionary."""
        from neuroglia.data.conversation.tool_call import ToolCall, ToolResult

        return cls(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=MessageStatus(data.get("status", "completed")),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            tool_results=[ToolResult.from_dict(tr) for tr in data.get("tool_results", [])],
            metadata=data.get("metadata", {}),
        )

    # =========================================================================
    # LLM FORMAT CONVERTERS
    # =========================================================================

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI chat completion format.

        Returns a dictionary compatible with OpenAI's chat completions API.
        Handles system, user, assistant, and tool messages.
        """
        msg: dict[str, Any] = {"role": self.role.value, "content": self.content}

        # Add tool calls for assistant messages
        if self.tool_calls and self.role == MessageRole.ASSISTANT:
            msg["tool_calls"] = [tc.to_openai_format() for tc in self.tool_calls]

        # Add tool_call_id for tool messages
        if self.role == MessageRole.TOOL and self.metadata.get("tool_call_id"):
            msg["tool_call_id"] = self.metadata["tool_call_id"]

        return msg

    def to_anthropic_format(self) -> dict[str, Any]:
        """Convert to Anthropic messages format.

        Note: Anthropic handles system messages separately and uses
        content blocks for tool_use. System messages should be passed
        via the `system` parameter at the API call level.
        """
        # For system messages, return a special marker (handled at conversation level)
        if self.role == MessageRole.SYSTEM:
            return {"_anthropic_system": self.content}

        # Map role
        role = "user" if self.role == MessageRole.USER else "assistant"

        # Handle tool messages (user role with tool_result content block)
        if self.role == MessageRole.TOOL:
            return {
                "role": "user",
                "content": [tr.to_anthropic_tool_result() for tr in self.tool_results],
            }

        # Build content blocks
        content: list[dict[str, Any]] = []

        # Add text content
        if self.content:
            content.append({"type": "text", "text": self.content})

        # Add tool_use blocks for assistant messages
        if self.tool_calls and self.role == MessageRole.ASSISTANT:
            for tc in self.tool_calls:
                content.append(tc.to_anthropic_format())

        # Return simple string content if no tool calls
        if len(content) == 1 and content[0]["type"] == "text":
            return {"role": role, "content": self.content}

        return {"role": role, "content": content}

    def to_gemini_format(self) -> dict[str, Any]:
        """Convert to Google Gemini messages format.

        Gemini uses:
        - "model" role instead of "assistant"
        - "parts" array with {"text": ...} or {"functionCall": ...}
        """
        # Map role: Gemini uses "model" not "assistant"
        if self.role == MessageRole.ASSISTANT:
            role = "model"
        elif self.role == MessageRole.TOOL:
            # Tool responses are part of user turn in Gemini
            role = "user"
        else:
            role = self.role.value

        parts: list[dict[str, Any]] = []

        # Add text content
        if self.content:
            parts.append({"text": self.content})

        # Add function calls (Gemini format) for assistant messages
        if self.tool_calls and self.role == MessageRole.ASSISTANT:
            for tc in self.tool_calls:
                parts.append(tc.to_gemini_format())

        # Add function responses for tool messages
        if self.tool_results and self.role == MessageRole.TOOL:
            for tr in self.tool_results:
                parts.append(tr.to_gemini_function_response())

        return {"role": role, "parts": parts}

    # Note: Ollama uses OpenAI-compatible format, so to_openai_format() works
    def to_ollama_format(self) -> dict[str, Any]:
        """Convert to Ollama messages format.

        Ollama uses OpenAI-compatible format.
        """
        return self.to_openai_format()
