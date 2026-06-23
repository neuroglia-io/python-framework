"""External payment service integration for Mario's Pizzeria.

Demonstrates HTTP Service Client usage with:
- Payment processing API calls
- Retry policies for network failures
- Circuit breaker for service reliability
- Authentication with Bearer tokens
- Comprehensive error handling
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
import logging

from neuroglia.integration.http_service_client import (
    HttpServiceClientException,
    HttpRequestOptions,
    RetryPolicy,
    create_authenticated_client,
)


class PaymentStatus(Enum):
    """Payment processing status."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class PaymentRequest:
    """Payment request data."""

    order_id: str
    amount: Decimal
    currency: str = "USD"
    customer_email: str = ""
    customer_name: str = ""
    description: str = ""


@dataclass
class PaymentResponse:
    """Payment response data."""

    payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None


class PaymentServiceException(Exception):
    """Payment service specific exception."""

    def __init__(
        self, message: str, payment_id: Optional[str] = None, status_code: Optional[int] = None
    ):
        super().__init__(message)
        self.payment_id = payment_id
        self.status_code = status_code


class ExternalPaymentService:
    """External payment service client using HTTP Service Client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0, max_retries: int = 3):
        """
        Initialize payment service client.

        Args:
            base_url: Payment API base URL
            api_key: API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.logger = logging.getLogger(__name__)

        # Configure HTTP client options for payment processing
        options = HttpRequestOptions(
            timeout=timeout,
            max_retries=max_retries,
            retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            retry_delay=1.0,
            retry_multiplier=2.0,
            retry_max_delay=30.0,
            circuit_breaker_failure_threshold=5,
            circuit_breaker_timeout=120.0,  # 2 minutes
            circuit_breaker_success_threshold=3,
            headers={"Content-Type": "application/json", "User-Agent": "MarioPizzeria/1.0"},
        )

        # Create authenticated HTTP client
        async def token_provider():
            return api_key

        self.http_client = create_authenticated_client(
            base_url=base_url, token_provider=token_provider, options=options
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.close()

    async def process_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """
        Process a payment through the external service.

        Args:
            payment_request: Payment details

        Returns:
            PaymentResponse: Payment processing result

        Raises:
            PaymentServiceException: If payment processing fails
        """
        try:
            self.logger.info(f"Processing payment for order {payment_request.order_id}")

            # Prepare payment data
            payment_data = {
                "order_id": payment_request.order_id,
                "amount": float(payment_request.amount),
                "currency": payment_request.currency,
                "customer": {
                    "email": payment_request.customer_email,
                    "name": payment_request.customer_name,
                },
                "description": payment_request.description,
                "metadata": {"source": "mario_pizzeria", "version": "1.0"},
            }

            # Make payment request
            response = await self.http_client.post_json("/payments", payment_data)

            # Parse response
            payment_response = PaymentResponse(
                payment_id=response["payment_id"],
                status=PaymentStatus(response["status"]),
                amount=Decimal(str(response["amount"])),
                currency=response["currency"],
                transaction_id=response.get("transaction_id"),
                error_message=response.get("error_message"),
            )

            self.logger.info(
                f"Payment {payment_response.payment_id} processed with status: "
                f"{payment_response.status.value}"
            )

            return payment_response

        except HttpServiceClientException as e:
            error_msg = f"Payment processing failed for order {payment_request.order_id}: {e}"
            self.logger.error(error_msg)

            # Try to extract payment ID from error response if available
            payment_id = None
            if e.response_body:
                try:
                    import json

                    error_data = json.loads(e.response_body)
                    payment_id = error_data.get("payment_id")
                except:
                    pass

            raise PaymentServiceException(
                error_msg, payment_id=payment_id, status_code=e.status_code
            )

        except Exception as e:
            error_msg = (
                f"Unexpected error processing payment for order {payment_request.order_id}: {e}"
            )
            self.logger.error(error_msg)
            raise PaymentServiceException(error_msg)

    async def get_payment_status(self, payment_id: str) -> PaymentResponse:
        """
        Get payment status from external service.

        Args:
            payment_id: Payment identifier

        Returns:
            PaymentResponse: Current payment status

        Raises:
            PaymentServiceException: If status check fails
        """
        try:
            self.logger.debug(f"Checking status for payment {payment_id}")

            response = await self.http_client.get_json(f"/payments/{payment_id}")

            payment_response = PaymentResponse(
                payment_id=response["payment_id"],
                status=PaymentStatus(response["status"]),
                amount=Decimal(str(response["amount"])),
                currency=response["currency"],
                transaction_id=response.get("transaction_id"),
                error_message=response.get("error_message"),
            )

            return payment_response

        except HttpServiceClientException as e:
            error_msg = f"Failed to get payment status for {payment_id}: {e}"
            self.logger.error(error_msg)
            raise PaymentServiceException(
                error_msg, payment_id=payment_id, status_code=e.status_code
            )

        except Exception as e:
            error_msg = f"Unexpected error checking payment status for {payment_id}: {e}"
            self.logger.error(error_msg)
            raise PaymentServiceException(error_msg, payment_id=payment_id)

    async def refund_payment(
        self, payment_id: str, amount: Optional[Decimal] = None
    ) -> PaymentResponse:
        """
        Refund a payment through the external service.

        Args:
            payment_id: Payment to refund
            amount: Partial refund amount (None for full refund)

        Returns:
            PaymentResponse: Refund result

        Raises:
            PaymentServiceException: If refund fails
        """
        try:
            self.logger.info(f"Processing refund for payment {payment_id}")

            refund_data = {"payment_id": payment_id}
            if amount is not None:
                refund_data["amount"] = float(amount)

            response = await self.http_client.post_json(
                f"/payments/{payment_id}/refund", refund_data
            )

            payment_response = PaymentResponse(
                payment_id=response["payment_id"],
                status=PaymentStatus(response["status"]),
                amount=Decimal(str(response["amount"])),
                currency=response["currency"],
                transaction_id=response.get("transaction_id"),
                error_message=response.get("error_message"),
            )

            self.logger.info(f"Refund processed for payment {payment_id}")
            return payment_response

        except HttpServiceClientException as e:
            error_msg = f"Refund failed for payment {payment_id}: {e}"
            self.logger.error(error_msg)
            raise PaymentServiceException(
                error_msg, payment_id=payment_id, status_code=e.status_code
            )

        except Exception as e:
            error_msg = f"Unexpected error processing refund for payment {payment_id}: {e}"
            self.logger.error(error_msg)
            raise PaymentServiceException(error_msg, payment_id=payment_id)

    async def get_circuit_breaker_health(self) -> Dict[str, Any]:
        """
        Get circuit breaker health status for monitoring.

        Returns:
            Dict with circuit breaker statistics
        """
        stats = self.http_client.get_circuit_breaker_stats()

        return {
            "state": stats.state.value,
            "failure_count": stats.failure_count,
            "success_count": stats.success_count,
            "total_requests": stats.total_requests,
            "total_failures": stats.total_failures,
            "last_failure_time": (
                stats.last_failure_time.isoformat() if stats.last_failure_time else None
            ),
            "last_success_time": (
                stats.last_success_time.isoformat() if stats.last_success_time else None
            ),
            "health_score": (
                (stats.total_requests - stats.total_failures) / max(stats.total_requests, 1) * 100
                if stats.total_requests > 0
                else 100.0
            ),
        }


# Example usage and configuration
class PaymentServiceConfiguration:
    """Configuration for payment service integration."""

    @staticmethod
    def configure_payment_service(
        builder,
        payment_api_url: str,
        payment_api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Configure payment service in the DI container.

        Args:
            builder: Application builder
            payment_api_url: Payment API base URL
            payment_api_key: API authentication key
            timeout: Request timeout
            max_retries: Maximum retry attempts
        """

        def create_payment_service(sp) -> ExternalPaymentService:
            return ExternalPaymentService(
                base_url=payment_api_url,
                api_key=payment_api_key,
                timeout=timeout,
                max_retries=max_retries,
            )

        builder.services.add_scoped(ExternalPaymentService, factory=create_payment_service)

        return builder


# Sample implementation for Mario's Pizzeria order processing
async def process_pizza_order_payment(
    payment_service: ExternalPaymentService,
    order_id: str,
    total_amount: Decimal,
    customer_email: str,
    customer_name: str,
) -> PaymentResponse:
    """
    Example function showing how to integrate payment processing with pizza orders.

    Args:
        payment_service: Configured payment service
        order_id: Pizza order identifier
        total_amount: Order total
        customer_email: Customer email
        customer_name: Customer name

    Returns:
        PaymentResponse: Payment processing result
    """

    payment_request = PaymentRequest(
        order_id=order_id,
        amount=total_amount,
        currency="USD",
        customer_email=customer_email,
        customer_name=customer_name,
        description=f"Mario's Pizzeria Order #{order_id}",
    )

    try:
        # Process payment with retry and circuit breaker protection
        payment_result = await payment_service.process_payment(payment_request)

        if payment_result.status == PaymentStatus.COMPLETED:
            logging.info(f"Payment successful for order {order_id}: {payment_result.payment_id}")
            return payment_result
        else:
            logging.warning(
                f"Payment not completed for order {order_id}: {payment_result.status.value}"
            )
            return payment_result

    except PaymentServiceException as e:
        logging.error(f"Payment failed for order {order_id}: {e}")
        # In a real application, you might want to:
        # - Save the failed payment attempt
        # - Notify the customer
        # - Put the order on hold
        # - Try alternative payment methods
        raise
