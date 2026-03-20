from pydantic import BaseModel
from typing import Optional, Literal


class CreateOrder(BaseModel):
    phone_number: str
    network: str
    capacity: int
    email: str
    payment_reference_phone: Optional[str] = None


class OrderResponse(BaseModel):

    reference: str

    status: str


class OrderStatusUpdate(BaseModel):
    status: Literal["completed", "failed"]


# ----- Bundles (admin CRUD) -----


class BundleCreate(BaseModel):
    network: str
    capacity_mb: int
    cost_price_ghs: float
    selling_price_ghs: float
    is_active: bool = True
    display_order: int = 0


class BundleUpdate(BaseModel):
    cost_price_ghs: Optional[float] = None
    selling_price_ghs: Optional[float] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class BundleResponse(BaseModel):
    id: int
    network: str
    capacity_mb: int
    cost_price_ghs: float
    selling_price_ghs: float
    is_active: bool
    display_order: int
