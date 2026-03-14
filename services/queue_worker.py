import asyncio
from collections import deque
from pyrogram import Client
from database.db import upload_repo
from database.models import UploadStatus
from services.youtube_uploader import upload_to_youtube
from utils.formatters import make_progress_bar, format_size
from utils.logger import log
from bson import ObjectId

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
                    await upload_repo.update(upload_id, {
                        "status": UploadStatus.FAILED,
                        "error": str(e)
                    })
                try:
                    await app.send_message(
                        job["telegram_id"],
                        f"❌ Upload failed: {str(e)}"
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

    await upload_repo.update(upload_id, {"status": UploadStatus.DOWNLOADING})

    # Download progress
    last_dl_progress = [0]

    async def download_progress(current, total):
        if total == 0:
            return
        percent = int((current / total) * 100)
        if percent - last_dl_progress[0] >= 10:
            last_dl_progress[0] = percent
            bar = make_progress_bar(percent)
            try:
                await status_msg.edit_text(
                    f"📥 Downloading...\n{bar} {percent}%\n"
                    f"📁 {format_size(current)} / {format_size(total)}"
                )
            except Exception:
                pass  # Ignore flood wait on edit
            await upload_repo.update(upload_id, {"progress_download": percent})

    # Download file
    msg = await app.get_messages(chat_id, message_id)
    if not msg or not (msg.video or msg.document):
        raise Exception("Original message not found or has no media.")

    file_path = await msg.download(progress=download_progress)

    await upload_repo.update(upload_id, {
        "status": UploadStatus.UPLOADING,
        "progress_download": 100
    })

    try:
        await status_msg.edit_text(
            f"✅ Downloaded!\n📤 Uploading to YouTube...\n"
            f"{make_progress_bar(0)} 0%"
        )
    except Exception:
        pass

    # Upload progress
    last_ul_progress = [0]

    async def upload_progress(percent: int):
        if percent - last_ul_progress[0] >= 10:
            last_ul_progress[0] = percent
            bar = make_progress_bar(percent)
            try:
                await status_msg.edit_text(
                    f"✅ Downloaded!\n📤 Uploading to YouTube...\n"
                    f"{bar} {percent}%"
                )
            except Exception:
                pass
            await upload_repo.update(upload_id, {"progress_upload": percent})

    # Upload to YouTube
    video_id = await upload_to_youtube(
        telegram_id=telegram_id,
        file_path=file_path,
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
        progress_callback=upload_progress
    )

    youtube_url = f"https://youtube.com/watch?v={video_id}"
    await upload_repo.update(upload_id, {
        "status": UploadStatus.DONE,
        "youtube_id": video_id,
        "progress_upload": 100
    })

    try:
        await status_msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n\n"
            f"🎬 {title}\n"
            f"🔗 {youtube_url}",
            parse_mode="html"
        )
    except Exception:
        await app.send_message(chat_id, f"✅ Upload done!\n🔗 {youtube_url}")
