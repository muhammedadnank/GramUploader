import asyncio
from pyrogram import Client
from config import Config
from core.bot import get_app, notify_admin
from handlers import register_all
from services.queue_worker import start_worker
from services.oauth_server import run_oauth_server
from utils.logger import log
import threading


async def main():
    app = get_app()

    # Register all handlers
    register_all(app)

    await app.start()
    log.info("Bot started successfully")

    # Start queue worker
    asyncio.create_task(start_worker(app))

    # Notify admins
    for admin_id in Config.ADMIN_IDS:
        try:
            await app.send_message(admin_id, "✅ Bot started successfully!")
        except Exception:
            pass

    await asyncio.Event().wait()


if __name__ == "__main__":
    # Start OAuth server in background thread
    oauth_thread = threading.Thread(
        target=run_oauth_server, daemon=True
    )
    oauth_thread.start()
    log.info(f"OAuth server starting on port {Config.OAUTH_SERVER_PORT}")

    asyncio.run(main())
