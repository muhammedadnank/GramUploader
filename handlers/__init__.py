from pyrogram import Client
from handlers import manage, ai, start, video, admin, fsm_router
from utils.logger import log


def register_all(app: Client):
    # Register callback-only handlers first
    manage.register(app)
    ai.register(app)
    start.register(app)
    video.register(app)
    admin.register(app)
    # FSM router LAST — it registers text/photo/document handlers.
    # Pyrogram fires the FIRST matching handler, so FSM router must
    # come after all command & callback handlers but be the sole
    # text/photo/document handler.
    fsm_router.register(app)
    log.info("All handlers registered")
