from pyrogram import Client
from handlers import manage, ai, start, video, admin
from utils.logger import log


def register_all(app: Client):
    # manage + ai first — FSM handlers must take priority
    manage.register(app)
    ai.register(app)
    start.register(app)
    video.register(app)
    admin.register(app)
    log.info("All handlers registered")
