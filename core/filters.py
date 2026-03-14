from pyrogram import filters
from config import Config


def admin_filter():
    async def func(_, __, update):
        # Works for both Message and CallbackQuery — both have .from_user
        user = getattr(update, "from_user", None)
        return user is not None and user.id in Config.ADMIN_IDS
    return filters.create(func)


def youtube_connected_filter():
    from database.db import user_repo
    async def func(_, __, update):
        user = getattr(update, "from_user", None)
        if not user:
            return False
        db_user = await user_repo.find(user.id)
        return db_user is not None and db_user.youtube_connected
    return filters.create(func)


# Export
is_admin = admin_filter()
is_youtube_connected = youtube_connected_filter()