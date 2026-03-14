from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from database.db import user_repo, upload_repo
from database.models import Upload, UploadStatus
from services.queue_worker import enqueue, queue_size
from core.middlewares import apply_middlewares
from utils.messages import Messages
from utils.keyboards import Keyboards
from utils.validators import is_valid_video, is_within_size_limit, sanitize_title
from utils.formatters import format_size
from utils.logger import log
from config import Config

# Temp store for pending confirmations {message_id: upload_data}
_pending: dict = {}


def register(app: Client):

    @app.on_message(
        (filters.video | filters.document) & filters.private
    )
    async def handle_video(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return

        user = await user_repo.find(message.from_user.id)

        # YouTube connected check
        if not user or not user.youtube_connected:
            await message.reply(
                Messages.not_connected(),
                reply_markup=Keyboards.connect(message.from_user.id),
                parse_mode="html"
            )
            return

        # Daily quota check
        uploads_today = await user_repo.get_uploads_today(message.from_user.id)
        plan = user.plan.value
        if plan == "free" and uploads_today >= Config.FREE_UPLOADS_PER_DAY:
            await message.reply(
                Messages.daily_limit(Config.FREE_UPLOADS_PER_DAY),
                reply_markup=Keyboards.premium(),
                parse_mode="html"
            )
            return

        media = message.video or message.document

        # Size check
        if not is_within_size_limit(media.file_size or 0):
            await message.reply(
                Messages.file_too_large(media.file_size or 0, Config.MAX_FILE_SIZE_MB),
                parse_mode="html"
            )
            return

        # Get user settings
        user_settings = user.get_settings() if user else {}
        default_privacy = user_settings.get("privacy", "public")

        # Build title
        raw_title = (
            message.caption
            or (media.file_name if hasattr(media, "file_name") else None)
            or f"Video_{message.id}"
        )
        title = sanitize_title(raw_title)

        # Store pending
        pending_key = f"{message.from_user.id}:{message.id}"
        _pending[pending_key] = {
            "telegram_id": message.from_user.id,
            "message_id": message.id,
            "chat_id": message.chat.id,
            "file_id": media.file_id,
            "title": title,
            "size": media.file_size or 0,
            "privacy": default_privacy,
        }

        # Show confirmation screen
        await message.reply(
            Messages.upload_confirm(title, media.file_size or 0, default_privacy),
            reply_markup=Keyboards.upload_confirm(pending_key),
            parse_mode="html"
        )

    # ─── CONFIRMATION CALLBACKS ─────────────────────────────────

    @app.on_callback_query(filters.regex(r"^upload_confirm:(.+)$"))
    async def cb_upload_confirm(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        data = _pending.pop(pending_key, None)

        if not data:
            await cq.answer("⚠️ Session expired. Please resend the video.", show_alert=True)
            await cq.message.delete()
            return

        # Create upload record
        upload = Upload(
            telegram_id=data["telegram_id"],
            file_id=data["file_id"],
            title=data["title"],
            size=data["size"],
        )
        upload_id = await upload_repo.create(upload)
        await user_repo.increment_uploads_today(data["telegram_id"])

        # Queue position
        position = queue_size() + 1

        # Add to queue
        enqueue({
            "telegram_id": data["telegram_id"],
            "upload_id": upload_id,
            "message_id": data["message_id"],
            "chat_id": data["chat_id"],
            "title": data["title"],
            "privacy": data["privacy"],
        })

        await cq.message.edit_text(
            Messages.upload_queued(data["title"], data["size"], position),
            parse_mode="html"
        )

    @app.on_callback_query(filters.regex(r"^upload_cancel:(.+)$"))
    async def cb_upload_cancel(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        _pending.pop(pending_key, None)
        await cq.message.edit_text("❌ Upload cancelled.")

    @app.on_callback_query(filters.regex(r"^upload_privacy:(.+)$"))
    async def cb_upload_privacy(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return
        await cq.message.edit_reply_markup(
            reply_markup=Keyboards.privacy_select(pending_key)
        )

    @app.on_callback_query(filters.regex(r"^set_privacy:(\w+):(.+)$"))
    async def cb_set_privacy(client: Client, cq: CallbackQuery):
        privacy = cq.matches[0].group(1)
        pending_key = cq.matches[0].group(2)

        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return

        _pending[pending_key]["privacy"] = privacy
        data = _pending[pending_key]

        await cq.message.edit_text(
            Messages.upload_confirm(data["title"], data["size"], privacy),
            reply_markup=Keyboards.upload_confirm(pending_key),
            parse_mode="html"
        )
        await cq.answer(f"Privacy set to {privacy}")

    @app.on_callback_query(filters.regex(r"^upload_back:(.+)$"))
    async def cb_upload_back(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        data = _pending.get(pending_key)
        if not data:
            await cq.answer("Session expired.", show_alert=True)
            return
        await cq.message.edit_text(
            Messages.upload_confirm(data["title"], data["size"], data["privacy"]),
            reply_markup=Keyboards.upload_confirm(pending_key),
            parse_mode="html"
        )
