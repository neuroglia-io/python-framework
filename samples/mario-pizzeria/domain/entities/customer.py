"""
Customer entity for Mario's Pizzeria domain.

This module contains both the CustomerState (data) and Customer (behavior)
classes following the state separation pattern with multipledispatch event handlers.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from api.dtos import CustomerDto
from domain.events import (
    CustomerActiveOrderAddedEvent,
    CustomerActiveOrderRemovedEvent,
    CustomerContactUpdatedEvent,
    CustomerRegisteredEvent,
)
from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_from, map_to


@dataclass
class CustomerState(AggregateState[str]):
    """
    State object for Customer aggregate.

    Contains all customer data that needs to be persisted.
    State mutations are handled through @dispatch event handlers.
    """

    name: Optional[str] = None
    email: Optional[str] = None
    phone: str = ""
    address: str = ""
    user_id: Optional[str] = None  # Keycloak user ID for profile linkage
    active_orders: list[str] = field(default_factory=list)  # List of active order IDs

    @dispatch(CustomerRegisteredEvent)
    def on(self, event: CustomerRegisteredEvent) -> None:
        """Handle CustomerRegisteredEvent to initialize customer state"""
        self.id = event.aggregate_id
        self.name = event.name
        self.email = event.email
        self.phone = event.phone
        self.address = event.address
        self.user_id = event.user_id

    @dispatch(CustomerContactUpdatedEvent)
    def on(self, event: CustomerContactUpdatedEvent) -> None:
        """Handle CustomerContactUpdatedEvent to update contact information"""
        self.phone = event.phone
        self.address = event.address

    @dispatch(CustomerActiveOrderAddedEvent)
    def on(self, event: CustomerActiveOrderAddedEvent) -> None:
        """Handle CustomerActiveOrderAddedEvent to add order to active orders"""
        if event.order_id not in self.active_orders:
            self.active_orders.append(event.order_id)

    @dispatch(CustomerActiveOrderRemovedEvent)
    def on(self, event: CustomerActiveOrderRemovedEvent) -> None:
        """Handle CustomerActiveOrderRemovedEvent to remove order from active orders"""
        if event.order_id in self.active_orders:
            self.active_orders.remove(event.order_id)


@map_from(CustomerDto)
@map_to(CustomerDto)
class Customer(AggregateRoot[CustomerState, str]):
    """
    Customer aggregate root with contact information.

    Uses Neuroglia's AggregateRoot with state separation pattern:
    - All data in CustomerState (persisted)
    - All behavior in Customer aggregate (not persisted)
    - Domain events registered and applied to state via multipledispatch

    Pattern: self.state.on(self.register_event(Event(...)))
    """

    def __init__(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__()

        # Register event and apply it to state using multipledispatch
        event = CustomerRegisteredEvent(
            aggregate_id=str(uuid4()),
            name=name,
            email=email,
            phone=phone or "",
            address=address or "",
            user_id=user_id,
        )

        self.state.on(self.register_event(event))

    def update_contact_info(self, phone: Optional[str] = None, address: Optional[str] = None) -> None:
        """Update customer contact information"""
        # Only update if there's a change
        new_phone = phone if phone is not None else self.state.phone
        new_address = address if address is not None else self.state.address

        if new_phone != self.state.phone or new_address != self.state.address:
            # Register event and apply it to state
            self.state.on(
                self.register_event(
                    CustomerContactUpdatedEvent(
                        aggregate_id=self.id(),
                        phone=new_phone,
                        address=new_address,
                    )
                )
            )

    def add_active_order(self, order_id: str) -> None:
        """Add an order to customer's active orders"""
        if order_id not in self.state.active_orders:
            add_event = CustomerActiveOrderAddedEvent(
                aggregate_id=self.id(),
                order_id=order_id,
            )
            self.state.on(self.register_event(add_event))

    def remove_active_order(self, order_id: str) -> None:
        """Remove an order from customer's active orders"""
        if order_id in self.state.active_orders:
            remove_event = CustomerActiveOrderRemovedEvent(
                aggregate_id=self.id(),
                order_id=order_id,
            )
            self.state.on(self.register_event(remove_event))

    def get_active_orders(self) -> list[str]:
        """Get list of active order IDs"""
        return self.state.active_orders.copy()

    def has_active_orders(self) -> bool:
        """Check if customer has any active orders"""
        return len(self.state.active_orders) > 0

    def __str__(self) -> str:
        name_str = self.state.name if self.state.name else "Unknown"
        email_str = self.state.email if self.state.email else "no-email"
        return f"{name_str} ({email_str})"
