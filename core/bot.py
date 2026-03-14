from pyrogram import Client
from config import Config
from utils.logger import log

_app: Client | None = None


def get_app() -> Client:
    global _app
    if _app is None:
        _app = Client(
            "gramuploader",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
    return _app


async def notify_admin(text: str):
    """Send message to all admins"""
    app = get_app()
    for admin_id in Config.ADMIN_IDS:
        try:
            await app.send_message(admin_id, text)
        except Exception as e:
            log.error(f"Failed to notify admin {admin_id}: {e}")
