from motor.motor_asyncio import AsyncIOMotorCollection
from database.models import Upload, UploadStatus
from datetime import datetime, date
from typing import Optional
from bson import ObjectId


class UploadRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.col = collection

    async def create(self, upload: Upload) -> ObjectId:
        doc = upload.model_dump()
        result = await self.col.insert_one(doc)
        return result.inserted_id

    async def find(self, upload_id: ObjectId) -> Optional[Upload]:
        doc = await self.col.find_one({"_id": upload_id})
        return Upload(**doc) if doc else None

    async def update(self, upload_id: ObjectId, data: dict):
        await self.col.update_one(
            {"_id": upload_id},
            {"$set": data}
        )

    async def set_status(self, upload_id: ObjectId, status: UploadStatus, extra: dict = {}):
        await self.col.update_one(
            {"_id": upload_id},
            {"$set": {"status": status.value, **extra}}
        )

    async def get_user_uploads(self, telegram_id: int, limit: int = 10) -> list[Upload]:
        cursor = self.col.find(
            {"telegram_id": telegram_id}
        ).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Upload(**d) for d in docs]

    async def count(self) -> int:
        return await self.col.count_documents({})

    async def count_today(self) -> int:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return await self.col.count_documents({
            "created_at": {"$gte": today}
        })

    async def count_by_status(self, status: UploadStatus) -> int:
        return await self.col.count_documents({"status": status.value})
