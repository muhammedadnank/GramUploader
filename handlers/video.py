import time
from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram import enums
from pyrogram.types import Message, CallbackQuery
from database.db import user_repo, upload_repo
from database.models import Upload, UploadStatus
from services.queue_worker import enqueue, queue_size
from core.middlewares import apply_middlewares
from utils.messages import Messages
from utils.keyboards import Keyboards
from utils.validators import is_within_size_limit, sanitize_title
from utils.formatters import format_size
from utils.logger import log
from config import Config

# Temp store for pending confirmations {pending_key: {data..., _ts: float}}
_pending: dict = {}

# Per-user upload title edit FSM {user_id: pending_key}
_pending_edit: dict = {}

# TTL for pending confirmations (10 minutes)
_PENDING_TTL = 600


def _cleanup_pending():
    """Remove expired pending entries."""
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v.get("_ts", 0) > _PENDING_TTL]
    for k in expired:
        _pending.pop(k, None)


async def handle_video_upload(client: Client, message: Message):
    """
    Core video/document upload logic.
    Called directly for filters.video messages, and from fsm_router as a
    fallback when a document arrives with no active FSM state.
    """
    if not await apply_middlewares(client, message):
        return

    user = await user_repo.find(message.from_user.id)

    if not user or not user.youtube_connected:
        await message.reply(
            Messages.not_connected(),
            reply_markup=Keyboards.connect(message.from_user.id),
            parse_mode=enums.ParseMode.HTML
        )
        return

    uploads_today = await user_repo.get_uploads_today(message.from_user.id)
    plan = user.plan.value
    if plan == "free" and uploads_today >= Config.FREE_UPLOADS_PER_DAY:
        await message.reply(
            Messages.daily_limit(Config.FREE_UPLOADS_PER_DAY),
            reply_markup=Keyboards.premium(),
            parse_mode=enums.ParseMode.HTML
        )
        return

    media = message.video or message.document

    if not is_within_size_limit(media.file_size or 0):
        await message.reply(
            Messages.file_too_large(media.file_size or 0, Config.MAX_FILE_SIZE_MB),
            parse_mode=enums.ParseMode.HTML
        )
        return

    user_settings = user.get_settings() if user else {}
    default_privacy = user_settings.get("privacy", "public")

    raw_title = (
        message.caption
        or (media.file_name if hasattr(media, "file_name") else None)
        or f"Video_{message.id}"
    )
    title = sanitize_title(raw_title)

    _cleanup_pending()

    pending_key = f"{message.from_user.id}:{message.id}"
    _pending[pending_key] = {
        "telegram_id": message.from_user.id,
        "message_id": message.id,
        "chat_id": message.chat.id,
        "file_id": media.file_id,
        "title": title,
        "size": media.file_size or 0,
        "privacy": default_privacy,
        "_ts": time.time(),
    }

    await message.reply(
        Messages.upload_confirm(title, media.file_size or 0, default_privacy),
        reply_markup=Keyboards.upload_confirm(pending_key),
        parse_mode=enums.ParseMode.HTML
    )


def register(app: Client):

    # Only filters.video here — documents are handled by fsm_router
    # (which checks FSM state first, then falls back to handle_video_upload)
    @app.on_message(filters.video & filters.private)
    async def handle_video(client: Client, message: Message):
        await handle_video_upload(client, message)

    # ─── CONFIRMATION CALLBACKS ─────────────────────────────────

    @app.on_callback_query(filters.regex(r"^upload_confirm:(.+)$"))
    async def cb_upload_confirm(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        data = _pending.pop(pending_key, None)

        if not data:
            await cq.answer("⚠️ Session expired. Please resend the video.", show_alert=True)
            await cq.message.delete()
            return

        upload = Upload(
            telegram_id=data["telegram_id"],
            file_id=data["file_id"],
            title=data["title"],
            size=data["size"],
        )
        upload_id = await upload_repo.create(upload)
        await user_repo.increment_uploads_today(data["telegram_id"])

        position = queue_size() + 1
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
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^upload_cancel:(.+)$"))
    async def cb_upload_cancel(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        _pending.pop(pending_key, None)
        try:
            await cq.message.edit_text("❌ Upload cancelled.")
        except MessageNotModified:
            pass

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
            parse_mode=enums.ParseMode.HTML
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
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^upload_edit_title:(.+)$"))
    async def cb_upload_edit_title(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return
        current_title = _pending[pending_key]["title"]
        _pending_edit[cq.from_user.id] = pending_key
        await cq.message.edit_text(
            f"✏️ <b>Edit Title</b>\n\n"
            f"Current: <code>{current_title[:80]}</code>\n\n"
            f"Send the new title as a message.\n"
            f"Send /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )
