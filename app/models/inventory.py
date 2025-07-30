# app/models/inventory.py
from pydantic import BaseModel, Field
from typing import Dict
from datetime import date

class InventoryItemCreate(BaseModel):
    name: str
    quantity: int
    price: float
    description: str

class InventoryItemDB(InventoryItemCreate):
    id: str = Field(alias="id")

class SalesUpdate(BaseModel):
    item_id: str
    date: date
    count: int