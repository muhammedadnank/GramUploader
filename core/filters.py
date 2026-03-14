from pyrogram import filters
from pyrogram.types import Message
from config import Config


def admin_filter():
    async def func(_, __, message: Message):
        return message.from_user and message.from_user.id in Config.ADMIN_IDS
    return filters.create(func)


def youtube_connected_filter():
    from database.db import user_repo
    async def func(_, __, message: Message):
        if not message.from_user:
            return False
        user = await user_repo.find(message.from_user.id)
        return user is not None and user.youtube_connected
    return filters.create(func)


# Export
is_admin = admin_filter()
is_youtube_connected = youtube_connected_filter()
