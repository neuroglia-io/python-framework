"""Menu DTOs for Mario's Pizzeria API"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MenuPizzaDto(BaseModel):
    """DTO for pizza menu item"""

    name: str = Field(..., min_length=1, max_length=100)
    base_price: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    available_sizes: dict[str, Decimal] = Field(
        default_factory=lambda: {
            "small": Decimal("0.8"),
            "medium": Decimal("1.0"),
            "large": Decimal("1.3"),
        }
    )
    available_toppings: dict[str, Decimal] = Field(default_factory=dict)
    is_available: bool = Field(default=True)

    class Config:
        from_attributes = True


class MenuDto(BaseModel):
    """DTO for complete pizza menu"""

    pizzas: list[MenuPizzaDto] = Field(default_factory=list)
    last_updated: Optional[str] = None

    class Config:
        from_attributes = True


class CreateMenuPizzaDto(BaseModel):
    """DTO for creating a new menu pizza"""

    name: str = Field(..., min_length=1, max_length=100)
    base_price: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    available_sizes: dict[str, Decimal] = Field(
        default_factory=lambda: {
            "small": Decimal("0.8"),
            "medium": Decimal("1.0"),
            "large": Decimal("1.3"),
        }
    )
    available_toppings: dict[str, Decimal] = Field(default_factory=dict)
    is_available: bool = Field(default=True)

    class Config:
        from_attributes = True


class UpdateMenuPizzaDto(BaseModel):
    """DTO for updating a menu pizza"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_price: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    available_sizes: Optional[dict[str, Decimal]] = None
    available_toppings: Optional[dict[str, Decimal]] = None
    is_available: Optional[bool] = None

    class Config:
        from_attributes = True
