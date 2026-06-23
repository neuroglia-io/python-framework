"""Kitchen DTOs for Mario's Pizzeria API"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# from .order_dtos import OrderDto  # Available if needed


class KitchenOrderDto(BaseModel):
    """DTO for kitchen view of orders"""

    id: str
    customer_name: str
    pizzas: list[str] = Field(default_factory=list)  # Simplified pizza descriptions
    status: str
    order_time: datetime
    cooking_started_time: Optional[datetime] = None
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class KitchenStatusDto(BaseModel):
    """DTO for overall kitchen status"""

    pending_orders: list[KitchenOrderDto] = Field(default_factory=list)
    cooking_orders: list[KitchenOrderDto] = Field(default_factory=list)
    ready_orders: list[KitchenOrderDto] = Field(default_factory=list)
    total_pending: int = 0
    total_cooking: int = 0
    total_ready: int = 0
    average_wait_time_minutes: Optional[float] = None

    class Config:
        from_attributes = True


class UpdateKitchenOrderDto(BaseModel):
    """DTO for updating kitchen order status"""

    order_id: str = Field(..., min_length=1)
    action: str = Field(..., description="Action: start_cooking, mark_ready, or complete")
    estimated_ready_time: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        from_attributes = True
