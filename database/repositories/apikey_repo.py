from motor.motor_asyncio import AsyncIOMotorCollection
from database.models import APIKey
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId


class APIKeyRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.col = collection

    async def get_active(self) -> Optional[dict]:
        return await self.col.find_one({
            "active": True,
            "units_used": {"$lt": 8000}
        })

    async def add(self, key: str):
        api_key = APIKey(
            key=key,
            reset_at=datetime.utcnow() + timedelta(days=1)
        )
        await self.col.insert_one(api_key.model_dump())

    async def increment_usage(self, key_id: ObjectId, units: int):
        # FIX: guard against None key_id (can happen if doc has no _id mapped)
        if key_id is None:
            return
        await self.col.update_one(
            {"_id": key_id},
            {"$inc": {"units_used": units}}
        )

    async def reset_daily(self):
        now = datetime.utcnow()
        await self.col.update_many(
            {"reset_at": {"$lte": now}},
            {"$set": {
                "units_used": 0,
                "reset_at": now + timedelta(days=1)
            }}
        )

    async def list_all(self) -> list[dict]:
        cursor = self.col.find({})
        return await cursor.to_list(length=None)

    async def deactivate(self, key_id: ObjectId):
        await self.col.update_one(
            {"_id": key_id},
            {"$set": {"active": False}}
        )
