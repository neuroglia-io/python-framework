"""Order DTOs for Mario's Pizzeria API"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Domain enums are available if needed for validation


class PizzaDto(BaseModel):
    """DTO for pizza information"""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    size: str = Field(..., description="Pizza size: small, medium, or large")
    toppings: list[str] = Field(default_factory=list)
    base_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        """Validate pizza size"""
        if v not in ["small", "medium", "large"]:
            raise ValueError("Size must be: small, medium, or large")
        return v

    class Config:
        from_attributes = True


class CreatePizzaDto(BaseModel):
    """DTO for creating a new pizza in an order"""

    name: str = Field(..., min_length=1, max_length=100)
    size: str = Field(..., description="Pizza size: small, medium, or large")
    toppings: list[str] = Field(default_factory=list)

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        """Validate pizza size"""
        if v not in ["small", "medium", "large"]:
            raise ValueError("Size must be: small, medium, or large")
        return v


class CustomerDto(BaseModel):
    """DTO for customer information"""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = Field(None, max_length=200)

    class Config:
        from_attributes = True


class OrderDto(BaseModel):
    """DTO for complete order information"""

    id: str
    customer: Optional[CustomerDto] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    pizzas: list[PizzaDto] = Field(default_factory=list)
    status: str
    order_time: datetime
    confirmed_time: Optional[datetime] = None
    cooking_started_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = None
    total_amount: Decimal
    pizza_count: int
    payment_method: Optional[str] = None

    # User tracking fields - who performed each operation
    chef_name: Optional[str] = None
    ready_by_name: Optional[str] = None
    delivery_name: Optional[str] = None

    class Config:
        from_attributes = True


class CreateOrderDto(BaseModel):
    """DTO for creating a new order"""

    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_address: str = Field(..., min_length=5, max_length=200)
    customer_email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    pizzas: list[CreatePizzaDto] = Field(..., min_length=1)
    payment_method: str = Field(..., description="Payment method: cash, credit_card, debit_card")
    notes: Optional[str] = Field(None, max_length=500)
    estimated_ready_time: Optional[datetime] = None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v):
        """Validate payment method"""
        valid_methods = ["cash", "credit_card", "debit_card"]
        if v not in valid_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(valid_methods)}')
        return v

    class Config:
        from_attributes = True


class UpdateOrderStatusDto(BaseModel):
    """DTO for updating order status"""

    status: str = Field(..., description="New order status")
    notes: Optional[str] = Field(None, max_length=500)
    estimated_ready_time: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate order status"""
        valid_statuses = ["pending", "confirmed", "cooking", "ready", "delivered", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v

    class Config:
        from_attributes = True
