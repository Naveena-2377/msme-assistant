from pydantic import BaseModel
from typing import Optional


class SaleRequest(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[float] = None  # defaults to the product's stored unit_price


class StockAdjustmentRequest(BaseModel):
    product_id: int
    new_stock: int
    reason: str
