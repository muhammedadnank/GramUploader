import asyncio
from pyrogram import Client
from config import Config
from core.bot import get_app, notify_admin
from handlers import register_all
from services.queue_worker import start_worker
from services.oauth_server import run_oauth_server, set_main_loop
from utils.logger import log
import threading


async def recover_stuck_jobs():
    from database.db import upload_repo
    from database.models import UploadStatus
    stuck = await upload_repo.get_stuck_jobs()
    if not stuck:
        return
    log.warning(f"Recovering {len(stuck)} stuck upload(s) from previous session...")
    for doc in stuck:
        await upload_repo.update(doc["_id"], {
            "status": UploadStatus.FAILED.value,  # FIX #1: .value for string storage
            "error": "Bot restarted during upload. Please resend the video."
        })
    log.info(f"Marked {len(stuck)} stuck job(s) as failed.")


async def main():
    app = get_app()

    # Pass main event loop to OAuth server for DB calls
    set_main_loop(asyncio.get_running_loop())

    if not Config.ADMIN_IDS:
        log.warning("⚠️  ADMIN_IDS is empty — no admin will have access to admin commands!")
    if not Config.BOT_TOKEN:
        log.error("BOT_TOKEN is not set. Exiting.")
        return
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET:
        log.warning("⚠️  GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set — OAuth will fail!")

    register_all(app)

    await app.start()
    log.info("Bot started successfully")

    # FIX #19: create DB indexes on startup (idempotent — safe to call every time)
    from database.db import ensure_indexes
    await ensure_indexes()
    log.info("Database indexes ensured")

    await recover_stuck_jobs()

    asyncio.create_task(start_worker(app))

    for admin_id in Config.ADMIN_IDS:
        try:
            await app.send_message(admin_id, "✅ Bot started successfully!")
        except Exception:
            pass

    await asyncio.Event().wait()


if __name__ == "__main__":
    oauth_thread = threading.Thread(target=run_oauth_server, daemon=True)
    oauth_thread.start()
    log.info(f"OAuth server starting on port {Config.OAUTH_SERVER_PORT}")

    asyncio.run(main())