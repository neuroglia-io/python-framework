"""
CloudEvents implementation for standardized event representation and communication.

This module provides a complete implementation of the CloudEvents specification v1.0,
enabling standardized event formats for event-driven architectures, microservice
communication, and inter-system event exchange.

Key Features:
    - Full CloudEvents v1.0 specification compliance
    - Support for structured and binary content modes
    - Extensible attribute system for custom metadata
    - JSON serialization and deserialization support
    - Integration with event sourcing and CQRS patterns

Examples:
    ```python
    from datetime import datetime
    from neuroglia.eventing.cloud_events import CloudEvent

    # Create a basic CloudEvent
    event = CloudEvent(
        id="order-123",
        source="/orders/service",
        type="order.created",
        subject="order/123",
        data={"orderId": "123", "total": 99.99},
        time=datetime.utcnow()
    )

    # Access attributes
    event_id = event.get_attribute("id")
    custom_attr = event.get_attribute("custom_extension")
    ```

See Also:
    - CloudEvents Specification: https://cloudevents.io/
    - Event-Driven Patterns: https://bvandewe.github.io/pyneuro/patterns/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class CloudEventSpecVersion:
    """
    Exposes all supported versions of the CloudEvents specification for standardized event handling.

    This class provides version constants for the CloudEvents specification, ensuring
    compatibility with different versions of the CloudEvents standard for event-driven
    architectures and inter-service communication.

    Examples:
        ```python
        # Use specific version
        event = CloudEvent(
            id="event-123",
            source="/orders/service",
            type="order.created",
            specversion=CloudEventSpecVersion.v1_0
        )

        # Version validation
        if event.specversion == CloudEventSpecVersion.v1_0:
            # Handle v1.0 specific logic
            pass
        ```

    See Also:
        - CloudEvents Specification: https://cloudevents.io/
        - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/patterns/
    """

    v1_0: str = "1.0"
    """Version 1.0 of the CloudEvents specification - the current stable version."""


@dataclass
class CloudEvent:
    """
    Represents a standardized CloudEvent for event-driven architecture and inter-service communication.

    This class implements the CloudEvents specification, providing a standardized format for
    describing events in a common way across different systems, platforms, and protocols.
    CloudEvents enable interoperability, portability, and consistency in event-driven architectures.

    Key Features:
        - CloudEvents v1.0 specification compliance
        - Structured and binary content mode support
        - Extensible attribute system for custom metadata
        - JSON serialization compatibility
        - Integration with event sourcing and CQRS patterns

    Examples:
        ```python
        from datetime import datetime
        from neuroglia.eventing import CloudEvent

        # Basic event creation
        event = CloudEvent(
            id="order-123-created",
            source="/orders/service",
            type="com.example.orders.created",
            subject="order/123",
            data={"orderId": "123", "customerId": "456", "total": 99.99},
            time=datetime.utcnow()
        )

        # Domain event publishing
        class OrderCreatedEvent(CloudEvent):
            def __init__(self, order_id: str, customer_id: str, total: Decimal):
                super().__init__(
                    id=f"order-{order_id}-created",
                    source="/orders/domain",
                    type="order.created.v1",
                    subject=f"order/{order_id}",
                    data={
                        "orderId": order_id,
                        "customerId": customer_id,
                        "total": str(total)
                    }
                )

        # Event handling
        @cloudevent("order.created.v1")
        class OrderCreatedHandler:
            async def handle(self, event: CloudEvent):
                order_data = event.data
                await self.process_order(order_data["orderId"])

        # Binary data events
        binary_event = CloudEvent(
            id="file-uploaded",
            source="/storage/service",
            type="file.uploaded",
            datacontenttype="application/pdf",
            data_base64="base64encodeddata..."
        )

        # Extension attributes
        event_with_extensions = CloudEvent(
            id="custom-event",
            source="/custom/service",
            type="custom.event",
            # Extension attributes
            correlation_id="corr-123",
            tenant_id="tenant-456"
        )
        ```

    Attributes:
        id (str): Unique identifier for the event within the scope of its source
        source (str): URI identifying the context/source that produced the event
        type (str): Event type identifier using reverse DNS naming convention
        specversion (str): CloudEvents specification version (defaults to '1.0')
        time (Optional[datetime]): Timestamp when the event was produced
        subject (Optional[str]): Subject of the event in producer's context
        datacontenttype (Optional[str]): MIME type of event data (defaults to 'application/json')
        dataschema (Optional[str]): URI referencing the schema of the event data
        data (Optional[Any]): Event payload for structured content mode
        data_base64 (Optional[str]): Base64-encoded binary event data
        sequencetype (Optional[str]): Type of event sequence for ordering
        sequence (Optional[int]): Sequence number for event ordering

    See Also:
        - CloudEvents Specification: https://cloudevents.io/
        - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/patterns/
        - Domain Events Guide: https://bvandewe.github.io/pyneuro/features/
    """

    id: str
    """ Gets/sets string that uniquely identifies the cloud event in the scope of its source. """

    source: str
    """ Gets/sets the cloud event's source. Must be an absolute URI. """

    type: str
    """ Gets/sets the cloud event's source. Should be a reverse DNS domain name, which must only contain lowercase alphanumeric, '-' and '.' characters. """

    specversion: str = "1.0"  # Default value for specversion
    """ Gets/sets the version of the CloudEvents specification which the event uses. Defaults to '1.0'. """

    sequencetype: Optional[str] = None
    """ Gets/sets the type of the sequence. """

    sequence: Optional[int] = None
    """ Gets/sets the sequence of the event. """

    time: Optional[datetime] = None
    """ Gets/sets the date and time at which the event has been produced. """

    subject: Optional[str] = None
    """ Gets/sets value that describes the subject of the event in the context of the event producer. """

    datacontenttype: Optional[str] = "application/json"  # Default value for datacontenttype
    """ Gets/sets the cloud event's data content type. Defaults to 'application/json'. """

    dataschema: Optional[str] = None
    """ Gets/sets an URI, if any, that references the versioned schema of the event's data. """

    data: Optional[Any] = None
    """ Gets/sets the event's data, if any. Only used if the event has been formatted using the structured mode. """

    data_base64: Optional[str] = None
    """ Gets/sets the event's binary data, encoded in base 64. Used if the event has been formatted using the binary mode. """

    _extra_attributes: dict[str, Any] = field(default_factory=dict, repr=False)

    def __init__(self, **kwargs):
        self._extra_attributes = {}
        for key, value in kwargs.items():
            if key in CloudEvent.__dataclass_fields__:
                setattr(self, key, value)
            else:
                self._extra_attributes[key] = value
        super().__init__()

    def get_attribute(self, name: str) -> Optional[Any]:
        """
        Retrieves the value of a CloudEvent attribute by name, including extension attributes.

        This method provides unified access to both standard CloudEvent attributes
        and custom extension attributes, enabling flexible event metadata handling.

        Args:
            name (str): The name of the attribute to retrieve

        Returns:
            Optional[Any]: The attribute value if found, None otherwise

        Raises:
            ValueError: If the attribute name is empty or None

        Examples:
            ```python
            event = CloudEvent(
                id="evt-123",
                source="/service",
                type="event.type",
                correlation_id="corr-456"  # Extension attribute
            )

            # Standard attributes
            event_id = event.get_attribute("id")  # "evt-123"
            source = event.get_attribute("source")  # "/service"

            # Extension attributes
            corr_id = event.get_attribute("correlation_id")  # "corr-456"

            # Non-existent attribute
            missing = event.get_attribute("nonexistent")  # None
            ```
        """
        if not name:
            raise ValueError("Attribute name cannot be empty or None.")
        return self.__dict__[name] if name in self.__dict__.keys() else None
