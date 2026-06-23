"""State machine implementation for resource state management.

This module provides a concrete implementation of state machines for managing
resource lifecycle states with validation and transition tracking.
"""

import logging
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from .abstractions import StateMachine, StateTransition

log = logging.getLogger(__name__)

TState = TypeVar("TState", bound=Enum)


class StateTransitionError(Exception):
    """Base exception for state transition errors."""

    def __init__(
        self,
        message: str,
        current_state: Optional[Enum] = None,
        target_state: Optional[Enum] = None,
    ):
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class InvalidStateTransitionError(StateTransitionError):
    """Exception raised when an invalid state transition is attempted."""

    def __init__(self, current_state: Enum, target_state: Enum):
        message = f"Invalid transition from {current_state} to {target_state}"
        super().__init__(message, current_state, target_state)


class TransitionValidator(Generic[TState]):
    """Validates state transitions based on defined rules."""

    def __init__(self, transitions: dict[TState, list[TState]]):
        self.transitions = transitions

    def validate_transition(self, current: TState, target: TState) -> bool:
        """Validate if transition from current to target state is allowed."""
        if current not in self.transitions:
            log.warning(f"No transitions defined for state {current}")
            return False

        valid_targets = self.transitions[current]
        is_valid = target in valid_targets

        if not is_valid:
            log.warning(f"Invalid transition from {current} to {target}. Valid targets: {valid_targets}")

        return is_valid

    def get_valid_transitions(self, current: TState) -> list[TState]:
        """Get all valid target states from the current state."""
        return self.transitions.get(current, [])


class StateMachineEngine(Generic[TState], StateMachine[TState]):
    """Concrete implementation of a state machine engine."""

    def __init__(
        self,
        initial_state: TState,
        transitions: dict[TState, list[TState]],
        transition_callbacks: Optional[dict[str, Any]] = None,
    ):
        super().__init__(initial_state, transitions)
        self.validator = TransitionValidator(transitions)
        self.transition_callbacks = transition_callbacks or {}
        self.transition_history: list[StateTransition[TState]] = []

    def can_transition_to(self, current: TState, target: TState) -> bool:
        """Check if transition from current to target state is valid."""
        return self.validator.validate_transition(current, target)

    def get_valid_transitions(self, current: TState) -> list[TState]:
        """Get all valid transitions from the current state."""
        return self.validator.get_valid_transitions(current)

    def execute_transition(
        self,
        current: TState,
        target: TState,
        condition: Optional[str] = None,
        action: Optional[str] = None,
    ) -> StateTransition[TState]:
        """Execute a state transition with validation and callbacks."""

        # Validate the transition
        if not self.can_transition_to(current, target):
            raise InvalidStateTransitionError(current, target)

        # Create transition record
        transition = StateTransition(from_state=current, to_state=target, condition=condition, action=action)

        # Execute pre-transition callback if defined
        callback_key = f"{current}_to_{target}"
        if callback_key in self.transition_callbacks:
            try:
                self.transition_callbacks[callback_key](transition)
            except Exception as e:
                log.error(f"Pre-transition callback failed for {transition}: {e}")
                raise StateTransitionError(f"Transition callback failed: {e}", current, target)

        # Record the transition
        self.transition_history.append(transition)

        log.info(f"Executed state transition: {transition}")
        return transition

    def get_transition_history(self) -> list[StateTransition[TState]]:
        """Get the history of all state transitions."""
        return self.transition_history.copy()

    def get_last_transition(self) -> Optional[StateTransition[TState]]:
        """Get the most recent state transition."""
        return self.transition_history[-1] if self.transition_history else None

    def register_transition_callback(self, from_state: TState, to_state: TState, callback: Any) -> None:
        """Register a callback to be executed during specific transitions."""
        callback_key = f"{from_state}_to_{to_state}"
        self.transition_callbacks[callback_key] = callback
        log.debug(f"Registered transition callback for {from_state} -> {to_state}")

    def clear_history(self) -> None:
        """Clear the transition history."""
        self.transition_history.clear()
        log.debug("Cleared state transition history")
