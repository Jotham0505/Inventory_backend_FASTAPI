from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId
from app.db import db
from app.models.inventory import InventoryItemCreate, InventoryItemDB

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

@router.get("/", response_model=List[InventoryItemDB])
async def list_items():
    items = []
    async for doc in db.inventory.find():
        doc["id"] = str(doc["_id"])
        items.append(InventoryItemDB(**doc))
    return items

@router.post("/", response_model=InventoryItemDB, status_code=status.HTTP_201_CREATED)
async def create_item(item: InventoryItemCreate):
    res = await db.inventory.insert_one(item.dict())
    created = await db.inventory.find_one({"_id": res.inserted_id})
    created["id"] = str(created["_id"])
    return InventoryItemDB(**created)

@router.put("/{item_id}", response_model=InventoryItemDB)
async def update_item(item_id: str, item: InventoryItemCreate):
    res = await db.inventory.update_one({"_id": ObjectId(item_id)}, {"$set": item.dict()})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.inventory.find_one({"_id": ObjectId(item_id)})
    updated["id"] = str(updated["_id"])
    return InventoryItemDB(**updated)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    res = await db.inventory.delete_one({"_id": ObjectId(item_id)})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Item not found")
