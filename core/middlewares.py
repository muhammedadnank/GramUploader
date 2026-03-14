from pyrogram import Client
from pyrogram.types import Message
from database.db import user_repo
from utils.logger import log
from config import Config
from collections import defaultdict
from datetime import datetime
import time

# Simple in-memory rate limiter
_rate_data: dict = defaultdict(list)
RATE_LIMIT = 5       # max requests
RATE_WINDOW = 10     # per N seconds


def is_rate_limited(telegram_id: int) -> bool:
    now = time.time()
    history = _rate_data[telegram_id]
    # Remove old entries
    _rate_data[telegram_id] = [t for t in history if now - t < RATE_WINDOW]
    if len(_rate_data[telegram_id]) >= RATE_LIMIT:
        return True
    _rate_data[telegram_id].append(now)
    return False


async def apply_middlewares(client: Client, message: Message) -> bool:
    """
    Run all middlewares. Returns False if request should be blocked.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return False

    # 1. Maintenance mode
    if Config.MAINTENANCE_MODE and user_id not in Config.ADMIN_IDS:
        await message.reply("🔧 Bot is under maintenance. Please try later.")
        log.info(f"Blocked {user_id} — maintenance mode")
        return False

    # 2. Auto upsert user
    await user_repo.upsert(user_id, {
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
    })

    # 3. Ban check
    user = await user_repo.find(user_id)
    if user and user.is_banned:
        await message.reply("🚫 You are banned from using this bot.")
        log.warning(f"Banned user {user_id} tried to use bot")
        return False

    # 4. Rate limit
    if is_rate_limited(user_id):
        await message.reply("⏳ Too many requests. Please slow down.")
        log.info(f"Rate limited user {user_id}")
        return False

    return True