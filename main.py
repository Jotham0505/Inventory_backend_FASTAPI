# main.py
import uvicorn
from fastapi import FastAPI
from app.core.database import db
from app.routers import auth, inventory

app = FastAPI(title="Tea Shop Inventory API")

app.include_router(auth.router)
app.include_router(inventory.router)

@app.get("/ping")
async def ping_db():
    res = await db.command("ping")
    return {"mongo_ok": res.get("ok")}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

