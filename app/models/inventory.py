# app/models/inventory.py
from pydantic import BaseModel, Field

class InventoryItemCreate(BaseModel):
    name: str
    quantity: int
    price: float
    supplier: str

class InventoryItemDB(InventoryItemCreate):
    id: str = Field(alias="id")
