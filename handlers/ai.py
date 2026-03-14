"""
AI Handler — /ai command
- AI title + description + tags generation (Gemini)
- AI caption generation (Whisper)
- Inline "✨ AI Suggest" button in upload confirmation
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from core.middlewares import apply_middlewares
from services.ai_service import generate_metadata, generate_captions, regenerate_title
from services.yt_manager import upload_caption
from utils.logger import log

# FSM: pending AI jobs {user_id: {state, data}}
_ai_states: dict = {}

STATE_WAIT_HINT   = "wait_hint"
STATE_WAIT_VIDEO  = "wait_video_caption"


def set_ai_state(uid: int, state: str, **kwargs):
    _ai_states[uid] = {"state": state, **kwargs}

def get_ai_state(uid: int) -> dict:
    return _ai_states.get(uid, {})

def clear_ai_state(uid: int):
    _ai_states.pop(uid, None)


def register(app: Client):

    # ─── /ai ────────────────────────────────────────────────────

    @app.on_message(filters.command("ai") & filters.private)
    async def cmd_ai(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        await message.reply(
            "🤖 <b>AI Tools</b>\n\n"
            "What do you want to generate?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ AI Metadata", callback_data="ai_metadata_start")],
                [InlineKeyboardButton("🎙 AI Captions (Whisper)", callback_data="ai_caption_start")],
                [InlineKeyboardButton("« Back", callback_data="back_start")],
            ]),
            parse_mode="html"
        )

    # ─── AI METADATA ────────────────────────────────────────────

    @app.on_callback_query(filters.regex("^ai_metadata_start$"))
    async def cb_metadata_start(client: Client, cq: CallbackQuery):
        set_ai_state(cq.from_user.id, STATE_WAIT_HINT)
        await cq.message.edit_text(
            "✨ <b>AI Metadata Generator</b>\n\n"
            "Send a short description or topic of your video.\n\n"
            "<i>Example: 'Kerala road trip highlights 2026'</i>\n\n"
            "Send /cancel to abort.",
            parse_mode="html"
        )

    # ─── AI CAPTION START ────────────────────────────────────────

    @app.on_callback_query(filters.regex("^ai_caption_start$"))
    async def cb_caption_start(client: Client, cq: CallbackQuery):
        set_ai_state(cq.from_user.id, STATE_WAIT_VIDEO)
        await cq.message.edit_text(
            "🎙 <b>AI Caption Generator</b>\n\n"
            "Send the video file you want to generate captions for.\n"
            "Whisper will transcribe the audio automatically.\n\n"
            "⚠️ Large files take a few minutes.\n\n"
            "Send /cancel to abort.",
            parse_mode="html"
        )

    # ─── INLINE AI SUGGEST (from upload confirmation) ───────────

    @app.on_callback_query(filters.regex(r"^ai_suggest:(.+)$"))
    async def cb_ai_suggest(client: Client, cq: CallbackQuery):
        """Called from upload confirmation screen — generate metadata for pending video"""
        pending_key = cq.matches[0].group(1)

        # Import pending dict from video handler
        from handlers.video import _pending
        data = _pending.get(pending_key)
        if not data:
            await cq.answer("Session expired. Resend the video.", show_alert=True)
            return

        await cq.message.edit_text("🤖 Generating AI metadata...")
        try:
            result = await generate_metadata(
                title_hint=data["title"],
                language=data.get("lang", "en")
            )

            # Update pending with AI title
            _pending[pending_key]["title"] = result["title"]
            _pending[pending_key]["ai_description"] = result["description"]
            _pending[pending_key]["ai_tags"] = result["tags"]

            from utils.messages import Messages
            from utils.keyboards import Keyboards
            await cq.message.edit_text(
                Messages.upload_confirm(result["title"], data["size"], data["privacy"])
                + f"\n\n✨ <b>AI Generated:</b>\n"
                f"📝 Desc: <i>{result['description'][:100]}...</i>\n"
                f"🏷 Tags: <i>{', '.join(result['tags'][:4])}...</i>",
                reply_markup=Keyboards.upload_confirm(pending_key, ai_applied=True),
                parse_mode="html"
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ AI failed: {e}")

    # ─── APPLY AI TO YOUTUBE AFTER UPLOAD ───────────────────────

    @app.on_callback_query(filters.regex(r"^ai_apply_yt:([^:]+):(.+)$"))
    async def cb_ai_apply_yt(client: Client, cq: CallbackQuery):
        """Apply AI-generated description + tags to uploaded video"""
        video_id = cq.matches[0].group(1)
        pending_key = cq.matches[0].group(2)

        from handlers.video import _pending
        data = _pending.get(pending_key, {})
        description = data.get("ai_description", "")
        tags = data.get("ai_tags", [])

        if not description and not tags:
            await cq.answer("No AI data found.", show_alert=True)
            return

        await cq.message.edit_text("⏳ Applying AI metadata to YouTube...")
        try:
            from services.yt_manager import update_video
            updates = {}
            if description:
                updates["description"] = description
            if tags:
                updates["tags"] = tags
            await update_video(cq.from_user.id, video_id, updates)
            await cq.message.edit_text(
                "✅ <b>AI Metadata Applied!</b>\n\n"
                f"📝 Description and tags updated on YouTube.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔗 View on YouTube ↗", url=f"https://youtube.com/watch?v={video_id}")
                ]]),
                parse_mode="html"
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    # ─── REGENERATE TITLE ────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^ai_regen_title:(.+)$"))
    async def cb_regen_title(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
        from handlers.video import _pending
        data = _pending.get(pending_key)
        if not data:
            await cq.answer("Session expired.", show_alert=True)
            return
        await cq.answer("⏳ Regenerating...")
        try:
            new_title = await regenerate_title(data["title"])
            _pending[pending_key]["title"] = new_title
            from utils.messages import Messages
            from utils.keyboards import Keyboards
            await cq.message.edit_text(
                Messages.upload_confirm(new_title, data["size"], data["privacy"]),
                reply_markup=Keyboards.upload_confirm(pending_key),
                parse_mode="html"
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)

    # ─── FSM TEXT — metadata hint ────────────────────────────────

    @app.on_message(filters.text & filters.private)
    async def ai_fsm_text(client: Client, message: Message):
        state_data = get_ai_state(message.from_user.id)
        if not state_data or state_data.get("state") != STATE_WAIT_HINT:
            return

        text = message.text.strip()
        if text == "/cancel":
            clear_ai_state(message.from_user.id)
            await message.reply("❌ Cancelled.")
            return

        clear_ai_state(message.from_user.id)
        msg = await message.reply("🤖 Generating metadata with Gemini...")
        try:
            result = await generate_metadata(title_hint=text)
            tags_str = "\n".join(f"  • {t}" for t in result["tags"])
            await msg.edit_text(
                f"✨ <b>AI Metadata</b>\n\n"
                f"📌 <b>Title:</b>\n<code>{result['title']}</code>\n\n"
                f"📝 <b>Description:</b>\n<i>{result['description']}</i>\n\n"
                f"🏷 <b>Tags:</b>\n{tags_str}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Regenerate", callback_data="ai_metadata_start")],
                    [InlineKeyboardButton("« Back", callback_data="back_start")],
                ]),
                parse_mode="html"
            )
        except Exception as e:
            await msg.edit_text(f"❌ {e}")

    # ─── FSM VIDEO — Whisper captions ───────────────────────────

    @app.on_message((filters.video | filters.document) & filters.private)
    async def ai_fsm_video(client: Client, message: Message):
        state_data = get_ai_state(message.from_user.id)
        if not state_data or state_data.get("state") != STATE_WAIT_VIDEO:
            return

        clear_ai_state(message.from_user.id)
        media = message.video or message.document

        # Size check — Whisper on large files takes too long in bot context
        size_mb = (media.file_size or 0) / (1024 * 1024)
        if size_mb > 500:
            await message.reply("❌ File too large for AI captions. Max 500MB.")
            return

        msg = await message.reply(
            f"🎙 <b>Transcribing audio...</b>\n\n"
            f"📁 {size_mb:.1f} MB — this may take a few minutes.",
            parse_mode="html"
        )

        try:
            # Download video
            file_path = await message.download()

            await msg.edit_text("🎙 Audio extracted. Transcribing with Whisper...")

            result = await generate_captions(file_path)

            lang = result["language_detected"]
            segments = result["segment_count"]
            duration = int(result["duration_seconds"])

            # Send the SRT file
            await message.reply_document(
                document=result["srt_path"],
                caption=(
                    f"✅ <b>Captions Ready!</b>\n\n"
                    f"🌐 Language: <b>{lang}</b>\n"
                    f"📝 Segments: <b>{segments}</b>\n"
                    f"⏱ Duration: <b>{duration}s</b>\n\n"
                    f"Upload this .srt to YouTube via /manage → 📝 Captions"
                ),
                parse_mode="html"
            )
            await msg.delete()

            # Cleanup
            import os
            try:
                os.remove(file_path)
                os.remove(result["srt_path"])
            except Exception:
                pass

        except Exception as e:
            await msg.edit_text(f"❌ Caption generation failed: {e}")
