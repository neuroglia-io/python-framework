"""
Customer event handlers for Mario's Pizzeria.

These handlers process customer-related domain events to implement side effects like
welcome emails, profile updates, CRM synchronization, and customer analytics.
"""

import logging
from typing import Any

from domain.events import (
    CustomerContactUpdatedEvent,
    CustomerProfileCreatedEvent,
    CustomerRegisteredEvent,
)

from neuroglia.mediation import DomainEventHandler

# Set up logger
logger = logging.getLogger(__name__)


class CustomerRegisteredEventHandler(DomainEventHandler[CustomerRegisteredEvent]):
    """Handles new customer registration events"""

    async def handle_async(self, event: CustomerRegisteredEvent) -> Any:
        """Process customer registered event"""
        logger.info(f"👋 New customer registered: {event.name} ({event.email}) - ID: {event.aggregate_id}")

        # In a real application, you might:
        # - Send welcome email/SMS
        # - Create loyalty account
        # - Add to marketing lists (with consent)
        # - Send first-order discount code
        # - Update customer analytics

        return None


class CustomerProfileCreatedEventHandler(DomainEventHandler[CustomerProfileCreatedEvent]):
    """
    Handles customer profile creation events.

    This is triggered when a profile is explicitly created (via UI or auto-created from Keycloak).
    This is a distinct business event from general customer registration.
    """

    async def handle_async(self, event: CustomerProfileCreatedEvent) -> Any:
        """Process customer profile created event"""
        logger.info(f"✨ Customer profile created for {event.name} ({event.email}) - " f"Customer ID: {event.aggregate_id}, User ID: {event.user_id}")

        # In a real application, you might:
        # - Send welcome/onboarding email with profile setup confirmation
        # - Create initial loyalty account with welcome bonus
        # - Send first-order discount code
        # - Add to marketing lists (with consent)
        # - Trigger onboarding workflow
        # - Send SMS confirmation of profile creation
        # - Update CRM systems with new profile
        # - Initialize recommendation engine with user preferences
        # - Track profile creation source (web, mobile, SSO auto-creation)

        return None


class CustomerContactUpdatedEventHandler(DomainEventHandler[CustomerContactUpdatedEvent]):
    """Handles customer contact information updates"""

    async def handle_async(self, event: CustomerContactUpdatedEvent) -> Any:
        """Process customer contact updated event"""
        logger.info(f"📝 Customer {event.aggregate_id} contact info updated: " f"Phone: {event.phone}, Address: {event.address}")

        # In a real application, you might:
        # - Update external CRM systems
        # - Validate new contact information
        # - Send confirmation to new phone/email
        # - Update marketing preferences
        # - Audit contact changes for compliance

        return None
