import asyncio
import os
import time
from collections import deque
from pyrogram import Client
from pyrogram import enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import upload_repo
from database.models import UploadStatus
from services.youtube_uploader import upload_to_youtube
from utils.formatters import make_progress_bar, format_size, format_eta
from utils.messages import Messages
from utils.logger import log
from config import Config

# In-memory queue (use Redis for production)
upload_queue: deque = deque()


def queue_size() -> int:
    return len(upload_queue)


def enqueue(job: dict):
    """Add upload job to queue"""
    upload_queue.append(job)


async def start_worker(app: Client):
    """Background worker that processes upload queue"""
    log.info("Queue worker started...")
    while True:
        if upload_queue:
            job = upload_queue.popleft()
            try:
                await process_job(app, job)
            except Exception as e:
                log.error(f"Worker error: {e}", exc_info=True)
                upload_id = job.get("upload_id")
                if upload_id:
                    # FIX #1: use .value so MongoDB stores the string, not the enum
                    await upload_repo.update(upload_id, {
                        "status": UploadStatus.FAILED.value,
                        "error": str(e)
                    })
                try:
                    await app.send_message(
                        job["telegram_id"],
                        f"❌ <b>Upload Failed</b>\n\n<code>{str(e)[:200]}</code>",
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📋 History", callback_data="history:1")],
                            [InlineKeyboardButton("💬 Support ↗", url=Config.SUPPORT_URL)],
                        ])
                    )
                except Exception as notify_err:
                    log.error(f"Failed to notify user: {notify_err}")
        await asyncio.sleep(1)


async def process_job(app: Client, job: dict):
    telegram_id = job["telegram_id"]
    upload_id = job["upload_id"]
    message_id = job["message_id"]
    chat_id = job["chat_id"]
    title = job["title"]
    privacy = job.get("privacy", "public")
    description = job.get("description", "")
    tags = job.get("tags", [])

    status_msg = await app.send_message(
        chat_id,
        "⏳ Starting download from Telegram..."
    )

    await upload_repo.update(upload_id, {"status": UploadStatus.DOWNLOADING.value})

    # Download progress with speed + ETA
    last_dl_progress = [0]
    dl_start_time = [time.time()]
    dl_last_bytes = [0]
    dl_last_time = [time.time()]

    async def download_progress(current, total):
        if total == 0:
            return
        percent = int((current / total) * 100)
        if percent - last_dl_progress[0] >= 10:
            last_dl_progress[0] = percent
            now = time.time()
            elapsed = now - dl_last_time[0]
            speed = (current - dl_last_bytes[0]) / elapsed if elapsed > 0 else 0
            dl_last_bytes[0] = current
            dl_last_time[0] = now
            remaining = (total - current) / speed if speed > 0 else 0
            try:
                # UPGRADE #3: dual-stage progress via Messages helper
                await status_msg.edit_text(
                    Messages.progress_downloading(
                        percent, current, total,
                        speed=int(speed), eta=int(remaining)
                    ),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
            await upload_repo.update(upload_id, {"progress_download": percent})

    # Download file
    msg = await app.get_messages(chat_id, message_id)
    if not msg or not (msg.video or msg.document):
        raise Exception("Original message not found or has no media.")

    file_path = await msg.download(progress=download_progress)

    await upload_repo.update(upload_id, {
        "status": UploadStatus.UPLOADING.value,
        "progress_download": 100
    })

    try:
        await status_msg.edit_text(
            Messages.progress_uploading(100, 0),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass

    # Upload progress with ETA
    last_ul_progress = [0]
    ul_start_time = [time.time()]

    async def upload_progress(percent: int):
        if percent - last_ul_progress[0] >= 10:
            last_ul_progress[0] = percent
            elapsed = time.time() - ul_start_time[0]
            remaining = (elapsed / percent * (100 - percent)) if percent > 0 else 0
            try:
                # UPGRADE #3: dual-stage progress
                await status_msg.edit_text(
                    Messages.progress_uploading(100, percent, eta=int(remaining)),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass
            await upload_repo.update(upload_id, {"progress_upload": percent})

    # Upload to YouTube
    try:
        video_id = await upload_to_youtube(
            telegram_id=telegram_id,
            file_path=file_path,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
            progress_callback=upload_progress
        )
    finally:
        # FIX #2: always clean up the downloaded temp file
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_err:
            log.warning(f"Could not delete temp file {file_path}: {cleanup_err}")

    youtube_url = f"https://youtube.com/watch?v={video_id}"
    await upload_repo.update(upload_id, {
        "status": UploadStatus.DONE.value,
        "youtube_id": video_id,
        "progress_upload": 100
    })

    # UPGRADE #2: try to send thumbnail as photo for a richer done message
    done_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Watch on YouTube ↗", url=youtube_url)],
        [
            InlineKeyboardButton("🎬 Manage Video", callback_data=f"mgr_video:{video_id}"),
            InlineKeyboardButton("📋 History", callback_data="history:1"),
        ],
    ])
    done_text = Messages.upload_done(title, video_id, privacy)
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    sent_as_photo = False
    try:
        await status_msg.delete()
        await app.send_photo(
            chat_id,
            photo=thumbnail_url,
            caption=done_text,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=done_kb
        )
        sent_as_photo = True
    except Exception:
        pass

    if not sent_as_photo:
        try:
            await status_msg.edit_text(
                done_text,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=done_kb
            )
        except Exception:
            await app.send_message(
                chat_id,
                done_text,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=done_kb
            )
