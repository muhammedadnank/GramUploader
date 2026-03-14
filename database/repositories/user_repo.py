from motor.motor_asyncio import AsyncIOMotorCollection
from database.models import User, YouTubeToken, Plan
from datetime import datetime
from typing import Optional
from utils.logger import log


class UserRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.col = collection

    async def find(self, telegram_id: int) -> Optional[User]:
        doc = await self.col.find_one({"_id": telegram_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        doc.setdefault("settings", {})  # ensure settings field exists
        try:
            return User(**doc)
        except Exception as e:
            log.error(f"User model parse error for {telegram_id}: {e}")
            return None

    async def upsert(self, telegram_id: int, data: dict):
        await self.col.update_one(
            {"_id": telegram_id},
            {
                "$set": data,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )

    async def set_youtube_token(self, telegram_id: int, token: YouTubeToken):
        await self.col.update_one(
            {"_id": telegram_id},
            {"$set": {
                "youtube_token": token.model_dump(),
                "youtube_connected": True,
                "connected_at": datetime.utcnow()
            }}
        )

    async def get_youtube_token(self, telegram_id: int) -> Optional[YouTubeToken]:
        doc = await self.col.find_one(
            {"_id": telegram_id},
            {"youtube_token": 1}
        )
        if not doc or not doc.get("youtube_token"):
            return None
        return YouTubeToken(**doc["youtube_token"])

    async def increment_uploads_today(self, telegram_id: int):
        today = datetime.utcnow().date().isoformat()
        await self.col.update_one(
            {"_id": telegram_id},
            {"$inc": {f"uploads.{today}": 1}},
            upsert=True
        )

    async def get_uploads_today(self, telegram_id: int) -> int:
        today = datetime.utcnow().date().isoformat()
        doc = await self.col.find_one(
            {"_id": telegram_id},
            {f"uploads.{today}": 1}
        )
        if not doc:
            return 0
        return doc.get("uploads", {}).get(today, 0)

    async def set_plan(self, telegram_id: int, plan: Plan):
        await self.col.update_one(
            {"_id": telegram_id},
            {"$set": {"plan": plan.value}}
        )

    async def ban(self, telegram_id: int, banned: bool = True):
        # upsert=True so ban works even if user has never started the bot
        await self.col.update_one(
            {"_id": telegram_id},
            {"$set": {"is_banned": banned}},
            upsert=True
        )

    async def count(self) -> int:
        return await self.col.count_documents({})

    async def count_connected(self) -> int:
        return await self.col.count_documents({"youtube_connected": True})

    async def get_all_ids(self) -> list[int]:
        cursor = self.col.find({}, {"_id": 1})
        docs = await cursor.to_list(length=None)
        return [d["_id"] for d in docs]