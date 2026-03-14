"""
AI Handler — /ai command
Gemini-powered metadata generation (title, description, tags).
Manual .srt caption upload is handled separately via /manage → Captions.
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from core.middlewares import apply_middlewares
from services.ai_service import generate_metadata, regenerate_title
from utils.logger import log

# FSM state for metadata hint input
_ai_states: dict = {}

STATE_WAIT_HINT = "wait_hint"


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
            "🤖 <b>AI Tools</b>\n\nWhat do you want to generate?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ AI Metadata", callback_data="ai_metadata_start")],
                [InlineKeyboardButton("« Back", callback_data="back_start")],
            ]),
            parse_mode="HTML"
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
            parse_mode="HTML"
        )

    # ─── INLINE AI SUGGEST (from upload confirmation) ───────────

    @app.on_callback_query(filters.regex(r"^ai_suggest:(.+)$"))
    async def cb_ai_suggest(client: Client, cq: CallbackQuery):
        pending_key = cq.matches[0].group(1)
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
                parse_mode="HTML"
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ AI failed: {e}")

    # ─── APPLY AI TO YOUTUBE AFTER UPLOAD ───────────────────────

    @app.on_callback_query(filters.regex(r"^ai_apply_yt:([^:]+):(.+)$"))
    async def cb_ai_apply_yt(client: Client, cq: CallbackQuery):
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
            from services.youtube_manager import update_video
            updates = {}
            if description:
                updates["description"] = description
            if tags:
                updates["tags"] = tags
            await update_video(cq.from_user.id, video_id, updates)
            await cq.message.edit_text(
                "✅ <b>AI Metadata Applied!</b>\n\n"
                "📝 Description and tags updated on YouTube.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔗 View on YouTube ↗", url=f"https://youtube.com/watch?v={video_id}")
                ]]),
                parse_mode="HTML"
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
                parse_mode="HTML"
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)
