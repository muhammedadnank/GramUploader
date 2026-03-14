"""
Central FSM Router
==================
Sole handler for filters.text, filters.photo, filters.document in private chats.
Registered LAST in handlers/__init__.py so all command/callback handlers take priority.

Priority order (text messages):
  1. Upload title edit  (video._pending_edit)
  2. AI metadata hint   (ai._ai_states  STATE_WAIT_HINT)
  3. Manage FSM         (manage._states  edit/schedule/playlist/caption)

Priority order (document messages):
  1. Manage caption SRT (manage._states STATE_CAPTION_FILE)
  2. Video upload       (fallback → handle_video_upload)

Priority order (photo messages):
  1. Manage thumbnail   (manage._states STATE_THUMBNAIL)
"""

from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram import enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.logger import log


def register(app: Client):

    # ── TEXT ─────────────────────────────────────────────────────────────────

    @app.on_message(filters.text & filters.private)
    async def fsm_text_router(client: Client, message: Message):
        user_id = message.from_user.id
        text = message.text.strip()

        # ── 1. Upload title edit ────────────────────────────────────────────
        from handlers.video import _pending, _pending_edit
        if user_id in _pending_edit:
            pending_key = _pending_edit.pop(user_id)
            if text == "/cancel":
                await message.reply("❌ Cancelled.")
                return
            if pending_key in _pending:
                from utils.validators import sanitize_title
                _pending[pending_key]["title"] = sanitize_title(text)
                from utils.messages import Messages
                from utils.keyboards import Keyboards
                data = _pending[pending_key]
                await message.reply(
                    Messages.upload_confirm(data["title"], data["size"], data["privacy"]),
                    reply_markup=Keyboards.upload_confirm(pending_key),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await message.reply("⚠️ Session expired. Please resend the video.")
            return

        # ── 3. Manage FSM ───────────────────────────────────────────────────
        from handlers.manage import get_state, clear_state, set_state
        from handlers.manage import (
            STATE_EDIT_TITLE, STATE_EDIT_DESC, STATE_EDIT_TAGS,
            STATE_CAPTION_LANG, STATE_SCHEDULE, STATE_NEW_PLAYLIST
        )
        state_data = get_state(user_id)
        if not state_data:
            return

        state = state_data.get("state")
        video_id = state_data.get("video_id")

        if text == "/cancel":
            clear_state(user_id)
            await message.reply("❌ Cancelled.")
            return

        try:
            from services.youtube_manager import update_video, add_to_playlist, create_playlist, upload_caption
            from utils.manage.messages import ManagerMessages

            if state == STATE_EDIT_TITLE:
                await update_video(user_id, video_id, {"title": text})
                clear_state(user_id)
                await message.reply(ManagerMessages.update_success("Title"), parse_mode=enums.ParseMode.HTML)

            elif state == STATE_EDIT_DESC:
                await update_video(user_id, video_id, {"description": text})
                clear_state(user_id)
                await message.reply(ManagerMessages.update_success("Description"), parse_mode=enums.ParseMode.HTML)

            elif state == STATE_EDIT_TAGS:
                tags = [t.strip() for t in text.split(",") if t.strip()]
                await update_video(user_id, video_id, {"tags": tags})
                clear_state(user_id)
                await message.reply(ManagerMessages.update_success("Tags"), parse_mode=enums.ParseMode.HTML)

            elif state == STATE_CAPTION_LANG:
                srt_path = state_data.get("srt_path")
                await upload_caption(user_id, video_id, srt_path, language=text)
                clear_state(user_id)
                await message.reply(ManagerMessages.update_success("Caption"), parse_mode=enums.ParseMode.HTML)

            elif state == STATE_SCHEDULE:
                from datetime import datetime, timezone
                try:
                    dt = datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                except ValueError:
                    await message.reply(
                        "❌ Invalid format. Use <code>YYYY-MM-DD HH:MM</code>\n"
                        "Example: <code>2026-04-01 18:00</code>\n\nSend /cancel to abort.",
                        parse_mode=enums.ParseMode.HTML
                    )
                    return
                publish_at = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                await update_video(user_id, video_id, {"publishAt": publish_at})
                clear_state(user_id)
                await message.reply(f"✅ Scheduled for <b>{text} UTC</b>", parse_mode=enums.ParseMode.HTML)

            elif state == STATE_NEW_PLAYLIST:
                result = await create_playlist(user_id, title=text)
                playlist_id = result["id"]
                await add_to_playlist(user_id, video_id, playlist_id)
                clear_state(user_id)
                await message.reply(
                    f"✅ Playlist <b>{text}</b> created and video added!",
                    parse_mode=enums.ParseMode.HTML
                )

        except Exception as e:
            clear_state(user_id)
            await message.reply(f"❌ Error: {e}")

    # ── PHOTO ─────────────────────────────────────────────────────────────────

    @app.on_message(filters.photo & filters.private)
    async def fsm_photo_router(client: Client, message: Message):
        user_id = message.from_user.id
        from handlers.manage import get_state, clear_state, STATE_THUMBNAIL
        state_data = get_state(user_id)
        if not state_data or state_data.get("state") != STATE_THUMBNAIL:
            return
        video_id = state_data.get("video_id")
        msg = await message.reply("⏳ Setting thumbnail...")
        try:
            from services.youtube_manager import set_thumbnail
            path = await message.download()
            await set_thumbnail(user_id, video_id, path)
            clear_state(user_id)
            await msg.edit_text("✅ Thumbnail updated!")
        except Exception as e:
            clear_state(user_id)
            await msg.edit_text(f"❌ {e}")

    # ── DOCUMENT ──────────────────────────────────────────────────────────────

    @app.on_message(filters.document & filters.private)
    async def fsm_document_router(client: Client, message: Message):
        user_id = message.from_user.id

        # ── 1. Manage FSM: .srt caption file ───────────────────────────────
        from handlers.manage import get_state, set_state, STATE_CAPTION_FILE, STATE_CAPTION_LANG
        state_data = get_state(user_id)
        if state_data and state_data.get("state") == STATE_CAPTION_FILE:
            video_id = state_data.get("video_id")
            fname = message.document.file_name or ""
            if not fname.endswith(".srt"):
                await message.reply("❌ Please send a .srt file.")
                return
            path = await message.download()
            set_state(user_id, STATE_CAPTION_LANG, video_id=video_id, srt_path=path)
            from utils.manage.messages import ManagerMessages
            await message.reply(ManagerMessages.caption_lang_prompt(), parse_mode=enums.ParseMode.HTML)
            return

        # ── 2. Fallback: normal video/document upload ───────────────────────
        from handlers.video import handle_video_upload
        await handle_video_upload(client, message)