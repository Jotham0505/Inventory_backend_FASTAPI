# app/routers/inventory.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from app.models.inventory import InventoryItemCreate, InventoryItemDB
from pydantic import BaseModel

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# ---- Pydantic bodies used in endpoints ----
class QuantityChange(BaseModel):
    change: int

class SalesUpdateBody(BaseModel):
    item_id: str
    date: str  # YYYY-MM-DD
    count: int

class SalesAdjust(BaseModel):
    date: str   # 'YYYY-MM-DD'
    change: int

class SetQuantityBody(BaseModel):
    quantity: int

# ---- CRUD ----
@router.get("/", response_model=List[InventoryItemDB])
async def list_items():
    items = []
    async for doc in db.inventory.find():
        doc["id"] = str(doc["_id"])
        items.append(InventoryItemDB(**doc))
    return items

@router.post("/", response_model=InventoryItemDB, status_code=status.HTTP_201_CREATED)
async def create_item(item: InventoryItemCreate):
    # When creating, the frontend may send initial quantity but you can store as-is.
    res = await db.inventory.insert_one(item.dict())
    created = await db.inventory.find_one({"_id": res.inserted_id})
    created["id"] = str(created["_id"])
    return InventoryItemDB(**created)

@router.get("/{item_id}", response_model=InventoryItemDB)
async def get_item(item_id: str):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    doc = await db.inventory.find_one({"_id": obj})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    doc["id"] = str(doc["_id"])
    return InventoryItemDB(**doc)

@router.put("/{item_id}", response_model=InventoryItemDB)
async def update_item(item_id: str, item: InventoryItemCreate):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")

    res = await db.inventory.update_one({"_id": obj}, {"$set": item.dict()})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.inventory.find_one({"_id": obj})
    updated["id"] = str(updated["_id"])
    return InventoryItemDB(**updated)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    res = await db.inventory.delete_one({"_id": obj})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Item not found")

# ---- Adjust quantity endpoint (kept for compatibility; not required if you use sales.adjust) ----
@router.patch("/{item_id}/quantity", response_model=InventoryItemDB)
async def adjust_quantity(item_id: str, payload: QuantityChange):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    res = await db.inventory.update_one({"_id": obj}, {"$inc": {"quantity": payload.change}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.inventory.find_one({"_id": obj})
    updated["id"] = str(updated["_id"])
    return InventoryItemDB(**updated)

# ---- NEW: adjust sales for a specific date and update remaining quantity atomically ----
@router.patch("/{item_id}/sales/adjust", response_model=InventoryItemDB)
async def adjust_sales(item_id: str, payload: SalesAdjust):
    """
    Body: {"date": "YYYY-MM-DD", "change": 1}
    change > 0 => record sale(s) and decrement quantity
    change < 0 => undo sale(s) and increment quantity
    """
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")

    change = int(payload.change)
    date_field = f"sales.{payload.date}"

    if change > 0:
        # Only allow sale if enough stock exists
        filter_q = {"_id": obj, "quantity": {"$gte": change}}
        update_q = {"$inc": {date_field: change, "quantity": -change}}
    else:
        # Undoing sales: allow, and increase stock
        filter_q = {"_id": obj}
        update_q = {"$inc": {date_field: change, "quantity": -change}}

    res = await db.inventory.update_one(filter_q, update_q)
    if res.matched_count == 0:
        raise HTTPException(status_code=400, detail="Item not found or insufficient stock")

    updated = await db.inventory.find_one({"_id": obj})
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found after update")
    updated["id"] = str(updated["_id"])
    # ensure sales exists
    if "sales" not in updated:
        updated["sales"] = {}
    return InventoryItemDB(**updated)

# ---- Set quantity explicitly (manual override) ----
@router.patch("/{item_id}/set_quantity", response_model=InventoryItemDB)
async def set_quantity(item_id: str, payload: SetQuantityBody):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    if payload.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    res = await db.inventory.update_one({"_id": obj}, {"$set": {"quantity": payload.quantity}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.inventory.find_one({"_id": obj})
    updated["id"] = str(updated["_id"])
    return InventoryItemDB(**updated)

# ---- Sales endpoints ----
@router.post("/sales/update")
async def update_sales(data: SalesUpdateBody):
    """
    Keep for backward compatibility if desired. Body:
    {"item_id":"...", "date":"YYYY-MM-DD", "count": 5}
    This sets sales.<date> = count (overwrites).
    """
    try:
        obj = ObjectId(data.item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")

    res = await db.inventory.update_one({"_id": obj}, {"$set": {f"sales.{data.date}": data.count}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Sales updated", "date": data.date, "count": data.count}

@router.get("/{item_id}/sales/{date}")
async def get_sales(item_id: str, date: str):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    item = await db.inventory.find_one({"_id": obj})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    count = item.get("sales", {}).get(date, 0)
    return {"date": date, "count": count}

@router.delete("/{item_id}/sales/{date}")
async def delete_sales(item_id: str, date: str):
    try:
        obj = ObjectId(item_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid item id")
    res = await db.inventory.update_one({"_id": obj}, {"$unset": {f"sales.{date}": ""}})
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sales entry not found")
    return {"message": "Sales entry deleted", "date": date}
