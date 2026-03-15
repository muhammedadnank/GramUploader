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
from handlers.video import _pending, _pending_edit, _pending_thumb

# Temp store for pending confirmations {pending_key: {data..., _ts: float}}
_pending: dict = {}

# Per-user upload title edit FSM {user_id: pending_key}
_pending_edit: dict = {}

# Per-user Short thumbnail wait FSM {user_id: pending_key}
_pending_thumb: dict = {}

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
    plan = user.plan if isinstance(user.plan, str) else user.plan.value
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
    # File type detection
    file_name = getattr(media, "file_name", None) or ""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if message.video:
        file_type = "mp4"
    elif ext in ("mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "mpeg", "3gp"):
        file_type = ext
    else:
        file_type = ext or "unknown"

    # UPGRADE #5: capture duration from message.video if available
    duration = getattr(message.video, "duration", None) if message.video else None

    # Auto-detect Shorts: duration ≤ 180s (YouTube Shorts max = 3 minutes since Oct 2024)
    is_short = bool(duration and int(duration) <= 180)

    # Quota warning: is this the last free upload today?
    quota_warning = False
    if plan == "free":
        if uploads_today == Config.FREE_UPLOADS_PER_DAY - 1:
            quota_warning = True

    _pending[pending_key] = {
        "telegram_id": message.from_user.id,
        "message_id": message.id,
        "chat_id": message.chat.id,
        "file_id": media.file_id,
        "title": title,
        "size": media.file_size or 0,
        "privacy": default_privacy,
        "file_type": file_type,
        "duration": duration,
        "is_short": is_short,
        "thumb_path": None,   # set when user sends thumbnail photo
        "_ts": time.time(),
    }

    await message.reply(
        Messages.upload_confirm(title, media.file_size or 0, default_privacy,
                                file_type=file_type, quota_warning=quota_warning,
                                duration=duration, is_short=is_short, has_thumb=False),
        reply_markup=Keyboards.upload_confirm(pending_key, is_short=is_short, has_thumb=False),
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
        await cq.answer()  # FIX #4
        pending_key = cq.matches[0].group(1)
        data = _pending.pop(pending_key, None)

        if not data:
            await cq.answer("⚠️ Session expired. Please resend the video.", show_alert=True)
            await cq.message.delete()
            return

        title = data["title"]
        privacy = data["privacy"]

        # Shorts: append #Shorts to title, force public privacy
        if data.get("is_short"):
            if "#Shorts" not in title:
                title = (title + " #Shorts")[:100]
            privacy = "public"  # Shorts don't work as private/unlisted

        upload = Upload(
            telegram_id=data["telegram_id"],
            file_id=data["file_id"],
            title=title,
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
            "title": title,
            "privacy": privacy,
            "thumb_path": data.get("thumb_path"),
            "duration": data.get("duration"),
            "is_short": data.get("is_short", False),
        })

        try:
            await cq.message.edit_text(
                Messages.upload_queued(title, data["size"], position),
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass

    @app.on_callback_query(filters.regex(r"^upload_cancel:(.+)$"))
    async def cb_upload_cancel(client: Client, cq: CallbackQuery):
        await cq.answer()  # FIX #4
        pending_key = cq.matches[0].group(1)
        data = _pending.pop(pending_key, None)
        # Clean up thumb file if it was downloaded
        if data and data.get("thumb_path"):
            try:
                import os
                if os.path.exists(data["thumb_path"]):
                    os.remove(data["thumb_path"])
            except Exception:
                pass
        # Clear thumbnail FSM if user was in it
        _pending_thumb.pop(cq.from_user.id, None)
        try:
            await cq.message.edit_text("❌ Upload cancelled.")
        except MessageNotModified:
            pass

    @app.on_callback_query(filters.regex(r"^upload_privacy:(.+)$"))
    async def cb_upload_privacy(client: Client, cq: CallbackQuery):
        await cq.answer()  # FIX #4
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
        is_short = data.get("is_short", False)
        has_thumb = bool(data.get("thumb_path"))
        try:
            await cq.message.edit_text(
                Messages.upload_confirm(data["title"], data["size"], privacy,
                                        file_type=data.get("file_type", ""),
                                        duration=data.get("duration"),
                                        is_short=is_short, has_thumb=has_thumb),
                reply_markup=Keyboards.upload_confirm(pending_key, is_short=is_short, has_thumb=has_thumb),
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass
        await cq.answer(f"Privacy set to {privacy}")

    @app.on_callback_query(filters.regex(r"^upload_back:(.+)$"))
    async def cb_upload_back(client: Client, cq: CallbackQuery):
        await cq.answer()  # FIX #4
        pending_key = cq.matches[0].group(1)
        data = _pending.get(pending_key)
        if not data:
            await cq.answer("Session expired.", show_alert=True)
            return
        is_short = data.get("is_short", False)
        has_thumb = bool(data.get("thumb_path"))
        try:
            await cq.message.edit_text(
                Messages.upload_confirm(data["title"], data["size"], data["privacy"],
                                        file_type=data.get("file_type", ""),
                                        duration=data.get("duration"),
                                        is_short=is_short, has_thumb=has_thumb),
                reply_markup=Keyboards.upload_confirm(pending_key, is_short=is_short, has_thumb=has_thumb),
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass

    @app.on_callback_query(filters.regex(r"^upload_toggle_shorts:(.+)$"))
    async def cb_toggle_shorts(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return
        # Flip the toggle
        current = _pending[pending_key].get("is_short", False)
        _pending[pending_key]["is_short"] = not current
        # If turning ON → force public (Shorts need public)
        if not current:
            _pending[pending_key]["privacy"] = "public"
        data = _pending[pending_key]
        is_short = data["is_short"]
        has_thumb = bool(data.get("thumb_path"))
        await cq.answer("📱 Shorts ON" if is_short else "📱 Shorts OFF")
        try:
            await cq.message.edit_text(
                Messages.upload_confirm(data["title"], data["size"], data["privacy"],
                                        file_type=data.get("file_type", ""),
                                        duration=data.get("duration"),
                                        is_short=is_short, has_thumb=has_thumb),
                reply_markup=Keyboards.upload_confirm(pending_key, is_short=is_short, has_thumb=has_thumb),
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass

    @app.on_callback_query(filters.regex(r"^upload_add_thumb:(.+)$"))
    async def cb_upload_add_thumb(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return
        # Enter thumbnail wait FSM
        _pending_thumb[cq.from_user.id] = pending_key
        await cq.answer()
        try:
            await cq.message.edit_text(
                "🖼 <b>Send Thumbnail</b>\n\n"
                "Send a photo to use as the Short thumbnail.\n"
                "It will be prepended as the first 2 seconds of the video.\n\n"
                "Send /cancel to abort.",
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass

    @app.on_callback_query(filters.regex(r"^upload_edit_title:(.+)$"))
    async def cb_upload_edit_title(client: Client, cq: CallbackQuery):
        await cq.answer()  # FIX #4
        pending_key = cq.matches[0].group(1)
        if pending_key not in _pending:
            await cq.answer("Session expired.", show_alert=True)
            return
        current_title = _pending[pending_key]["title"]
        _pending_edit[cq.from_user.id] = pending_key
        try:
            await cq.message.edit_text(
                f"✏️ <b>Edit Title</b>\n\n"
                f"Current: <code>{current_title[:80]}</code>\n\n"
                f"Send the new title as a message.\n"
                f"Send /cancel to abort.",
                parse_mode=enums.ParseMode.HTML
            )
        except MessageNotModified:
            pass
