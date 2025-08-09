from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId
from app.db import db
from app.models.inventory import InventoryItemCreate, InventoryItemDB
from app.models.inventory import SalesUpdate

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
    

@router.post("/sales/update")
async def update_sales(data: SalesUpdate):
    date_str = data.date.isoformat()
    res = await db.inventory.update_one(
        {"_id": ObjectId(data.item_id)},
        {"$set": {f"sales.{date_str}": data.count}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Sales updated", "date": date_str, "count": data.count}

@router.get("/{item_id}/sales/{date}")
async def get_sales(item_id: str, date: str):  # date as YYYY-MM-DD string
    item = await db.inventory.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    count = item.get("sales", {}).get(date, 0)
    return {"date": date, "count": count}

@router.delete("/{item_id}/sales/{date}")
async def delete_sales(item_id: str, date: str):
    res = await db.inventory.update_one(
        {"_id": ObjectId(item_id)},
        {"$unset": {f"sales.{date}": ""}}
    )
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sales entry not found")
    return {"message": "Sales entry deleted", "date": date}


#@router.get("/fix-missing-descriptions")
#async def fix_missing_descriptions():
#    result = await db["inventory"].update_many(
#        {"description": {"$exists": False}},
#        {"$set": {"description": ""}}
#    )
#    return {"updated_count": result.modified_count}

# this is the missing desccriptions fix