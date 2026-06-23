"""Conversation building blocks for AI agent systems.

Provides universal value objects for message handling, tool execution,
and execution context. Services build domain-specific aggregates
using these building blocks.

This module defines:
- Message, MessageRole, MessageStatus: LLM message representation
- ToolCall, ToolResult: Tool execution primitives
- ExecutionContext, LlmMessageSnapshot: ReAct loop state
- Session: Session lifecycle tracking

Architecture:
    These are VALUE OBJECTS, not aggregates. Services compose with these
    to build domain-specific aggregates:
    - Agent-Host uses these in Conversation aggregate (with scoring, templates)
    - Agent-Runtime uses these in AgentTask aggregate (with task-scoped execution)

NOT included: Full Conversation aggregate (too domain-specific)

Examples:
    ```python
    from neuroglia.data.conversation import (
        Message,
        MessageRole,
        ToolCall,
        ToolResult,
        ExecutionContext,
    )

    # Create messages
    user_msg = Message.create_user_message("Hello!")
    assistant_msg = Message.create_assistant_message(
        content="I'll search for that.",
        tool_calls=[ToolCall.create("search", {"query": "test"})]
    )

    # Use execution context for ReAct loops
    context = ExecutionContext(max_iterations=50)
    context.add_message("user", "Hello!")

    while context.can_continue():
        # ... execute agent loop
        context.iteration += 1

    # Convert to LLM format
    openai_messages = [msg.to_openai_format() for msg in messages]
    ```

See Also:
    - Agent Module: neuroglia.data.agent
    - A2A Protocol: neuroglia.a2a
"""

from neuroglia.data.conversation.execution_context import (
    ExecutionContext,
    LlmMessageSnapshot,
)
from neuroglia.data.conversation.message import Message, MessageRole, MessageStatus
from neuroglia.data.conversation.session import Session
from neuroglia.data.conversation.tool_call import ToolCall, ToolResult

__all__ = [
    # Message
    "Message",
    "MessageRole",
    "MessageStatus",
    # Tool execution
    "ToolCall",
    "ToolResult",
    # Execution
    "ExecutionContext",
    "LlmMessageSnapshot",
    # Session
    "Session",
]
