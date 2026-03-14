import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "gramuploader")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/callback")
    OAUTH_BASE_URL = os.getenv("OAUTH_BASE_URL", "http://localhost:8000")
    OAUTH_SERVER_HOST = os.getenv("OAUTH_SERVER_HOST", "0.0.0.0")
    OAUTH_SERVER_PORT = int(os.getenv("OAUTH_SERVER_PORT", 8000))
    FREE_UPLOADS_PER_DAY = int(os.getenv("FREE_UPLOADS_PER_DAY", 2))
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 2000))
    MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
    START_IMAGE_URL = os.getenv("START_IMAGE_URL", "https://i.imgur.com/placeholder.jpg")
    OWNER_URL = os.getenv("OWNER_URL", "https://t.me/owner")
    SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/support")
    PREMIUM_URL = os.getenv("PREMIUM_URL", "https://t.me/support")
    # AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium/large
