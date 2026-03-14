from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from database.repositories.user_repo import UserRepository
from database.repositories.upload_repo import UploadRepository
from database.repositories.apikey_repo import APIKeyRepository

client = AsyncIOMotorClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[Config.DB_NAME]

# Repository instances (use these everywhere)
user_repo = UserRepository(db.users)
upload_repo = UploadRepository(db.uploads)
apikey_repo = APIKeyRepository(db.api_keys)


async def ensure_indexes():
    """Create indexes for frequently queried fields. Safe to call on every startup."""
    # uploads
    await db.uploads.create_index("telegram_id")
    await db.uploads.create_index("status")
    await db.uploads.create_index("created_at")
    await db.uploads.create_index([("telegram_id", 1), ("created_at", -1)])
    # users
    await db.users.create_index("youtube_connected")
    await db.users.create_index("is_banned")