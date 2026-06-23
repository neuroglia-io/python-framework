"""Agent-to-Agent (A2A) protocol module.

Provides types and utilities for inter-agent communication
in the AIX distributed agent ecosystem.

This module defines:
- TaskPriority, TaskStatus: Enums for task lifecycle
- AgentIdentity: Identity for A2A routing
- TaskRequest: Delegation request from source to target agent
- TaskResponse: Response from target back to source

The protocol supports:
- Capability-based routing (via target_team_id + required_capabilities)
- Direct agent addressing (via target_agent_id)
- Synchronous and asynchronous delegation patterns
- Context sharing between agents

Examples:
    ```python
    from neuroglia.a2a import (
        TaskRequest,
        TaskResponse,
        AgentIdentity,
        TaskPriority,
        TaskStatus,
    )

    # Create delegation request
    request = TaskRequest(
        task_id="task-123",
        correlation_id="corr-456",
        source=AgentIdentity(
            agent_id="personal-agent",
            agent_type="personal",
            owner_id="user-789"
        ),
        target_team_id="research-team",
        intent="analyze_document",
        description="Analyze quarterly report",
        priority=TaskPriority.HIGH
    )

    # Handle response
    response = TaskResponse(
        task_id="task-123",
        correlation_id="corr-456",
        responder=AgentIdentity(
            agent_id="team-agent",
            agent_type="team_member",
            team_id="research-team"
        ),
        status=TaskStatus.COMPLETED,
        result={"insights": [...]}
    )
    ```

See Also:
    - Agent Module: neuroglia.data.agent
    - Implementation Plan: /docs/specs/personal-agent-implementation-plan.md
"""

from neuroglia.a2a.protocol import (
    AgentIdentity,
    TaskPriority,
    TaskRequest,
    TaskResponse,
    TaskStatus,
)

__all__ = [
    "TaskPriority",
    "TaskStatus",
    "AgentIdentity",
    "TaskRequest",
    "TaskResponse",
]
