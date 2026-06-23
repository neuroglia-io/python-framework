"""
Neuroglia - A comprehensive Python framework for building maintainable microservices.

This package provides a clean architecture foundation with CQRS, dependency injection,
event-driven architecture, and domain-driven design patterns built on FastAPI.

This file provides type stubs for external usage while avoiding circular imports.
For full functionality, import modules directly.

See full documentation at https://bvandewe.github.io/pyneuro/

"""

# Core types for type hints - these should always be available
__all__ = [
    # Core dependency injection
    "ServiceCollection",
    "ServiceProvider",
    "ServiceLifetime",
    "ServiceDescriptor",
    # CQRS mediation
    "Mediator",
    "Command",
    "Query",
    "Request",
    "CommandHandler",
    "QueryHandler",
    "RequestHandler",
    # Core framework
    "OperationResult",
    # Domain abstractions
    "Entity",
    "DomainEvent",
    "Repository",
    # Agent module
    "BaseAgentState",
    "TeamMembership",
    "KnowledgeScope",
    "AgentCapability",
    # A2A protocol
    "TaskRequest",
    "TaskResponse",
    "AgentIdentity",
    "TaskPriority",
    "TaskStatus",
    # Conversation building blocks
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    "ExecutionContext",
    "Session",
    # Optional components (import may fail)
    "ControllerBase",
    "EventStore",
    "EventSourcingRepository",
    "ResourceController",
    "StateMachine",
    "EventBus",
    "EventHandler",
    "CloudEvent",
    "WebApplicationBuilder",
    "WebApplication",
    "HostedService",
    "Mapper",
    "MongoRepository",
    "InMemoryRepository",
    "QueryableRepository",
    "ResourceWatcher",
    "Reconciler",
    "Observable",
    "Observer",
    # Utils
    "CamelCaseConverter",
    "to_camel_case",
    "to_snake_case",
    "to_pascal_case",
    "to_kebab_case",
    "CamelModel",
]

# Framework metadata
__version__ = "0.9.0"
__author__ = "Neuroglia Team"
__email__ = "team@neuroglia.io"
__license__ = "Apache"

# Dynamic imports with error handling to avoid circular imports


def __getattr__(name: str):
    """Dynamic attribute access for lazy loading of framework components."""

    # Core dependency injection
    if name in ["ServiceCollection", "ServiceProvider", "ServiceLifetime", "ServiceDescriptor"]:
        try:
            from .dependency_injection import (
                ServiceCollection,
                ServiceDescriptor,
                ServiceLifetime,
                ServiceProvider,
            )

            if name == "ServiceCollection":
                return ServiceCollection
            elif name == "ServiceProvider":
                return ServiceProvider
            elif name == "ServiceLifetime":
                return ServiceLifetime
            elif name == "ServiceDescriptor":
                return ServiceDescriptor
        except ImportError:
            pass

    # CQRS mediation
    elif name in [
        "Mediator",
        "Command",
        "Query",
        "Request",
        "CommandHandler",
        "QueryHandler",
        "RequestHandler",
    ]:
        try:
            from .mediation import (
                Command,
                CommandHandler,
                Mediator,
                Query,
                QueryHandler,
                Request,
                RequestHandler,
            )

            if name == "Mediator":
                return Mediator
            elif name == "Command":
                return Command
            elif name == "Query":
                return Query
            elif name == "Request":
                return Request
            elif name == "CommandHandler":
                return CommandHandler
            elif name == "QueryHandler":
                return QueryHandler
            elif name == "RequestHandler":
                return RequestHandler
        except ImportError:
            pass

    # Core framework types
    elif name == "OperationResult":
        try:
            from .core import OperationResult

            return OperationResult
        except ImportError:
            pass

    # Agent module
    elif name in ["BaseAgentState", "TeamMembership", "KnowledgeScope", "AgentCapability"]:
        try:
            from .data.agent import (
                AgentCapability,
                BaseAgentState,
                KnowledgeScope,
                TeamMembership,
            )

            if name == "BaseAgentState":
                return BaseAgentState
            elif name == "TeamMembership":
                return TeamMembership
            elif name == "KnowledgeScope":
                return KnowledgeScope
            elif name == "AgentCapability":
                return AgentCapability
        except ImportError:
            pass

    # A2A protocol
    elif name in ["TaskRequest", "TaskResponse", "AgentIdentity", "TaskPriority", "TaskStatus"]:
        try:
            from .a2a import (
                AgentIdentity,
                TaskPriority,
                TaskRequest,
                TaskResponse,
                TaskStatus,
            )

            if name == "TaskRequest":
                return TaskRequest
            elif name == "TaskResponse":
                return TaskResponse
            elif name == "AgentIdentity":
                return AgentIdentity
            elif name == "TaskPriority":
                return TaskPriority
            elif name == "TaskStatus":
                return TaskStatus
        except ImportError:
            pass

    # Conversation building blocks
    elif name in ["Message", "MessageRole", "ToolCall", "ToolResult", "ExecutionContext", "Session"]:
        try:
            from .data.conversation import (
                ExecutionContext,
                Message,
                MessageRole,
                Session,
                ToolCall,
                ToolResult,
            )

            if name == "Message":
                return Message
            elif name == "MessageRole":
                return MessageRole
            elif name == "ToolCall":
                return ToolCall
            elif name == "ToolResult":
                return ToolResult
            elif name == "ExecutionContext":
                return ExecutionContext
            elif name == "Session":
                return Session
        except ImportError:
            pass

    # Domain abstractions
    elif name in ["Entity", "DomainEvent"]:
        try:
            from .data.abstractions import DomainEvent, Entity

            if name == "Entity":
                return Entity
            elif name == "DomainEvent":
                return DomainEvent
        except ImportError:
            pass

    elif name == "Repository":
        try:
            from .data.infrastructure.abstractions import Repository

            return Repository
        except ImportError:
            pass

    # MVC Controllers
    elif name == "ControllerBase":
        try:
            from .mvc import ControllerBase

            return ControllerBase
        except ImportError:
            pass

    # Event sourcing
    elif name in ["EventStore", "EventSourcingRepository"]:
        try:
            from .data.infrastructure.event_sourcing import (
                EventSourcingRepository,
                EventStore,
            )

            if name == "EventStore":
                return EventStore
            elif name == "EventSourcingRepository":
                return EventSourcingRepository
        except ImportError:
            pass

    # Resource oriented architecture
    elif name in ["ResourceController", "StateMachine"]:
        try:
            from .data.resources import ResourceController, StateMachine

            if name == "ResourceController":
                return ResourceController
            elif name == "StateMachine":
                return StateMachine
        except ImportError:
            pass

    # Event handling
    elif name in ["EventBus", "EventHandler", "CloudEvent"]:
        try:
            from .eventing import CloudEvent, EventBus, EventHandler

            if name == "EventBus":
                return EventBus
            elif name == "EventHandler":
                return EventHandler
            elif name == "CloudEvent":
                return CloudEvent
        except ImportError:
            pass

    # Hosting
    elif name in ["WebApplicationBuilder", "WebApplication", "HostedService"]:
        try:
            from .hosting import HostedService
            from .hosting.web import WebApplication, WebApplicationBuilder

            if name == "WebApplicationBuilder":
                return WebApplicationBuilder
            elif name == "WebApplication":
                return WebApplication
            elif name == "HostedService":
                return HostedService
        except ImportError:
            pass

    # Mapping
    elif name == "Mapper":
        try:
            from .mapping import Mapper

            return Mapper
        except ImportError:
            pass

    # Repository implementations
    elif name == "MongoRepository":
        try:
            from .data.infrastructure.mongo import MongoRepository

            return MongoRepository
        except ImportError:
            pass

    elif name == "InMemoryRepository":
        try:
            from .data.infrastructure.memory import InMemoryRepository

            return InMemoryRepository
        except ImportError:
            pass

    elif name == "QueryableRepository":
        try:
            from .data.queryable import QueryableRepository

            return QueryableRepository
        except ImportError:
            pass

    # Resource watching
    elif name in ["ResourceWatcher", "Reconciler"]:
        try:
            from .data.resources import Reconciler, ResourceWatcher

            if name == "ResourceWatcher":
                return ResourceWatcher
            elif name == "Reconciler":
                return Reconciler
        except ImportError:
            pass

    # Reactive programming
    elif name in ["Observable", "Observer"]:
        try:
            from .reactive import Observable, Observer

            if name == "Observable":
                return Observable
            elif name == "Observer":
                return Observer
        except ImportError:
            pass

    # Utils
    elif name in [
        "CamelCaseConverter",
        "to_camel_case",
        "to_snake_case",
        "to_pascal_case",
        "to_kebab_case",
        "CamelModel",
    ]:
        try:
            from .utils import (
                CamelCaseConverter,
                CamelModel,
                to_camel_case,
                to_kebab_case,
                to_pascal_case,
                to_snake_case,
            )

            if name == "CamelCaseConverter":
                return CamelCaseConverter
            elif name == "to_camel_case":
                return to_camel_case
            elif name == "to_snake_case":
                return to_snake_case
            elif name == "to_pascal_case":
                return to_pascal_case
            elif name == "to_kebab_case":
                return to_kebab_case
            elif name == "CamelModel":
                return CamelModel
        except ImportError:
            pass

    # Validation
    elif name in [
        "BusinessRule",
        "BusinessRuleValidator",
        "ValidationResult",
        "ValidationError",
        "rule",
        "conditional_rule",
        "when",
        "ValidatorBase",
        "PropertyValidator",
        "EntityValidator",
        "CompositeValidator",
        "validate_with",
        "required",
        "min_length",
        "max_length",
        "email_format",
        "numeric_range",
        "custom_validator",
        "ValidationException",
        "BusinessRuleViolationException",
        "ConditionalValidationException",
    ]:
        try:
            from .validation import (
                BusinessRule,
                BusinessRuleValidator,
                BusinessRuleViolationException,
                CompositeValidator,
                ConditionalValidationException,
                EntityValidator,
                PropertyValidator,
                ValidationError,
                ValidationException,
                ValidationResult,
                ValidatorBase,
                conditional_rule,
                custom_validator,
                email_format,
                max_length,
                min_length,
                numeric_range,
                required,
                rule,
                validate_with,
                when,
            )

            if name == "BusinessRule":
                return BusinessRule
            elif name == "BusinessRuleValidator":
                return BusinessRuleValidator
            elif name == "ValidationResult":
                return ValidationResult
            elif name == "ValidationError":
                return ValidationError
            elif name == "rule":
                return rule
            elif name == "conditional_rule":
                return conditional_rule
            elif name == "when":
                return when
            elif name == "ValidatorBase":
                return ValidatorBase
            elif name == "PropertyValidator":
                return PropertyValidator
            elif name == "EntityValidator":
                return EntityValidator
            elif name == "CompositeValidator":
                return CompositeValidator
            elif name == "validate_with":
                return validate_with
            elif name == "required":
                return required
            elif name == "min_length":
                return min_length
            elif name == "max_length":
                return max_length
            elif name == "email_format":
                return email_format
            elif name == "numeric_range":
                return numeric_range
            elif name == "custom_validator":
                return custom_validator
            elif name == "ValidationException":
                return ValidationException
            elif name == "BusinessRuleViolationException":
                return BusinessRuleViolationException
            elif name == "ConditionalValidationException":
                return ConditionalValidationException
        except ImportError:
            pass

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
