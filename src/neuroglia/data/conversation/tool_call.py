"""Tool call and result value objects.

Provides universal representations for LLM tool invocation
requests and results, compatible with OpenAI, Anthropic,
Google Gemini, and Ollama formats.

Examples:
    ```python
    from neuroglia.data.conversation import ToolCall, ToolResult

    # Create a tool call
    call = ToolCall.create(
        tool_name="search_documents",
        arguments={"query": "Python best practices"}
    )

    # Create a tool result
    result = ToolResult(
        call_id=call.call_id,
        tool_name=call.tool_name,
        success=True,
        result={"documents": [...]},
        execution_time_ms=150.5
    )
    ```
"""

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Request from LLM to execute a tool.

    Universal representation of tool invocation requests,
    compatible with OpenAI, Anthropic, Google Gemini, and Ollama formats.

    Attributes:
        call_id: Unique identifier for this call (for result correlation)
        tool_name: Name of the tool to execute
        arguments: Arguments to pass to the tool

    Examples:
        ```python
        call = ToolCall.create(
            tool_name="search",
            arguments={"query": "Python patterns"}
        )
        ```
    """

    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    @classmethod
    def create(cls, tool_name: str, arguments: dict[str, Any]) -> "ToolCall":
        """Factory method to create a new tool call with generated ID."""
        return cls(
            call_id=str(uuid.uuid4()),
            tool_name=tool_name,
            arguments=arguments,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolCall":
        """Deserialize from dictionary."""
        return cls(
            call_id=data["call_id"],
            tool_name=data["tool_name"],
            arguments=data["arguments"],
        )

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI tool_calls format.

        Returns format compatible with OpenAI chat completions API.
        """
        import json

        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.tool_name,
                "arguments": json.dumps(self.arguments),
            },
        }

    def to_anthropic_format(self) -> dict[str, Any]:
        """Convert to Anthropic tool_use format.

        Returns format compatible with Anthropic Messages API.
        """
        return {
            "type": "tool_use",
            "id": self.call_id,
            "name": self.tool_name,
            "input": self.arguments,
        }

    def to_gemini_format(self) -> dict[str, Any]:
        """Convert to Google Gemini functionCall format.

        Returns format compatible with Gemini API.
        """
        return {
            "functionCall": {
                "name": self.tool_name,
                "args": self.arguments,
            }
        }


@dataclass
class ToolResult:
    """Result of tool execution.

    Captures success/failure state and execution metadata
    for tool invocations.

    Attributes:
        call_id: ID of the original tool call (for correlation)
        tool_name: Name of the tool that was executed
        success: Whether the tool execution succeeded
        result: Result data (if successful)
        error: Error message (if failed)
        execution_time_ms: Execution duration in milliseconds

    Examples:
        ```python
        result = ToolResult(
            call_id="call-123",
            tool_name="search",
            success=True,
            result={"documents": ["doc1", "doc2"]},
            execution_time_ms=250.0
        )
        ```
    """

    call_id: str
    tool_name: str
    success: bool
    result: Any
    error: str | None = None
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolResult":
        """Deserialize from dictionary."""
        return cls(
            call_id=data["call_id"],
            tool_name=data["tool_name"],
            success=data["success"],
            result=data["result"],
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms"),
        )

    def to_openai_tool_message(self) -> dict[str, Any]:
        """Convert to OpenAI tool response message format.

        Returns format compatible with OpenAI chat completions API.
        """
        import json

        content = json.dumps(self.result) if self.success else f"Error: {self.error}"
        return {
            "role": "tool",
            "tool_call_id": self.call_id,
            "content": content,
        }

    def to_anthropic_tool_result(self) -> dict[str, Any]:
        """Convert to Anthropic tool_result format.

        Returns format compatible with Anthropic Messages API.
        """
        import json

        if self.success:
            return {
                "type": "tool_result",
                "tool_use_id": self.call_id,
                "content": json.dumps(self.result) if not isinstance(self.result, str) else self.result,
            }
        else:
            return {
                "type": "tool_result",
                "tool_use_id": self.call_id,
                "is_error": True,
                "content": self.error or "Unknown error",
            }

    def to_gemini_function_response(self) -> dict[str, Any]:
        """Convert to Google Gemini functionResponse format.

        Returns format compatible with Gemini API.
        """
        return {
            "functionResponse": {
                "name": self.tool_name,
                "response": {
                    "result": self.result if self.success else {"error": self.error},
                },
            }
        }
