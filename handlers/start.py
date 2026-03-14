from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram import enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import user_repo, upload_repo
from core.middlewares import apply_middlewares
from utils.messages import Messages
from utils.keyboards import Keyboards
from utils.logger import log
from config import Config

ITEMS_PER_PAGE = 5


def register(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        user = await user_repo.find(message.from_user.id)
        connected = bool(user and user.youtube_connected)
        caption = Messages.start_caption(mention=message.from_user.mention, connected=connected)
        kb = Keyboards.start(message.from_user.id, connected)
        try:
            await message.reply_photo(
                photo=Config.START_IMAGE_URL,
                caption=caption,
                reply_markup=kb,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            await message.reply(caption, reply_markup=kb, parse_mode=enums.ParseMode.HTML)

    @app.on_message(filters.command("connect") & filters.private)
    async def connect(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        user = await user_repo.find(message.from_user.id)
        if user and user.youtube_connected:
            await message.reply(Messages.already_connected(), reply_markup=Keyboards.reconnect(message.from_user.id), parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply(Messages.connect_text(), reply_markup=Keyboards.connect(message.from_user.id), parse_mode=enums.ParseMode.HTML)

    @app.on_message(filters.command("history") & filters.private)
    async def history(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        await _send_history(client, message.from_user.id, message.chat.id, page=1)

    @app.on_message(filters.command("quota") & filters.private)
    async def quota(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        user = await user_repo.find(message.from_user.id)
        used = await user_repo.get_uploads_today(message.from_user.id)
        plan = user.plan.value if user else "free"
        limit = Config.FREE_UPLOADS_PER_DAY if plan == "free" else "∞"
        await message.reply(Messages.quota_text(used, limit, plan), reply_markup=Keyboards.back_to_start(), parse_mode=enums.ParseMode.HTML)

    @app.on_message(filters.command("settings") & filters.private)
    async def settings_cmd(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        await _send_settings(client, message.from_user.id, message.chat.id)

    @app.on_callback_query(filters.regex("^help$"))
    async def cb_help(client, cq: CallbackQuery):
        await cq.message.edit_text(Messages.help_text(), reply_markup=Keyboards.back_to_start(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex("^about$"))
    async def cb_about(client, cq: CallbackQuery):
        await cq.message.edit_text(Messages.about_text(), reply_markup=Keyboards.back_to_start(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex("^quota$"))
    async def cb_quota(client, cq: CallbackQuery):
        user = await user_repo.find(cq.from_user.id)
        used = await user_repo.get_uploads_today(cq.from_user.id)
        plan = user.plan.value if user else "free"
        limit = Config.FREE_UPLOADS_PER_DAY if plan == "free" else "∞"
        await cq.message.edit_text(Messages.quota_text(used, limit, plan), reply_markup=Keyboards.back_to_start(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex("^settings$"))
    async def cb_settings(client, cq: CallbackQuery):
        await _send_settings(client, cq.from_user.id, cq.message.chat.id, cq.message)

    @app.on_callback_query(filters.regex("^premium$"))
    async def cb_premium(client, cq: CallbackQuery):
        await cq.message.edit_text(
            "💎 <b>Premium Plan</b>\n\n✅ Unlimited uploads/day\n✅ Private & Unlisted\n✅ Priority queue\n✅ Custom descriptions\n\nTap below to upgrade!",
            reply_markup=Keyboards.premium(), parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^history:(\d+)$"))
    async def cb_history(client, cq: CallbackQuery):
        page = int(cq.matches[0].group(1))
        await _send_history(client, cq.from_user.id, cq.message.chat.id, page, edit_message=cq.message)

    @app.on_callback_query(filters.regex("^back_start$"))
    async def cb_back_start(client, cq: CallbackQuery):
        user = await user_repo.find(cq.from_user.id)
        connected = bool(user and user.youtube_connected)
        try:
            await cq.message.edit_caption(
                caption=Messages.start_caption(mention=cq.from_user.mention, connected=connected),
                reply_markup=Keyboards.start(cq.from_user.id, connected),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            await cq.message.edit_text(
                Messages.start_caption(mention=cq.from_user.mention, connected=connected),
                reply_markup=Keyboards.start(cq.from_user.id, connected),
                parse_mode=enums.ParseMode.HTML
            )

    @app.on_callback_query(filters.regex("^close$"))
    async def cb_close(client, cq: CallbackQuery):
        await cq.message.delete()

    @app.on_callback_query(filters.regex(r"^set_default_privacy:(\w+)$"))
    async def cb_set_privacy(client, cq: CallbackQuery):
        privacy = cq.matches[0].group(1)
        await user_repo.upsert(cq.from_user.id, {"settings.privacy": privacy})
        await _send_settings(client, cq.from_user.id, cq.message.chat.id, cq.message)
        await cq.answer(f"Default privacy: {privacy}")

    @app.on_callback_query(filters.regex(r"^set_lang:(\w+)$"))
    async def cb_set_lang(client, cq: CallbackQuery):
        lang = cq.matches[0].group(1)
        await user_repo.upsert(cq.from_user.id, {"settings.lang": lang})
        await _send_settings(client, cq.from_user.id, cq.message.chat.id, cq.message)
        await cq.answer("Language updated!")

    @app.on_callback_query(filters.regex("^toggle_autotitle$"))
    async def cb_toggle_autotitle(client, cq: CallbackQuery):
        user = await user_repo.find(cq.from_user.id)
        current = user.get_settings().get("auto_title", True) if user else True
        await user_repo.upsert(cq.from_user.id, {"settings.auto_title": not current})
        await _send_settings(client, cq.from_user.id, cq.message.chat.id, cq.message)
        await cq.answer("Auto-title toggled!")

    @app.on_callback_query(filters.regex("^noop$"))
    async def cb_noop(client, cq: CallbackQuery):
        await cq.answer()

    @app.on_callback_query(filters.regex("^mgr_open$"))
    async def cb_manage_open(client, cq: CallbackQuery):
        msg = await cq.message.edit_text("⏳ Fetching your videos...")
        try:
            from services.youtube_manager import get_my_videos
            from utils.manage.keyboards import ManagerKeyboards
            from utils.manage.messages import ManagerMessages
            data = await get_my_videos(cq.from_user.id)
            videos = data["items"]
            if not videos:
                await msg.edit_text("📭 No videos found.\n\nUpload a video first!")
                return
            await msg.edit_text(
                ManagerMessages.video_list_header(len(videos)),
                reply_markup=ManagerKeyboards.video_list(
                    videos,
                    next_token=data.get("nextPageToken"),
                    prev_token=data.get("prevPageToken")
                ),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await msg.edit_text(f"❌ {e}")

    @app.on_callback_query(filters.regex("^ai_menu$"))
    async def cb_ai_menu(client, cq: CallbackQuery):
        await cq.message.edit_text(
            "🤖 <b>AI Tools</b>\n\nWhat do you want to generate?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ AI Metadata", callback_data="ai_metadata_start")],
                [InlineKeyboardButton("« Back", callback_data="back_start")],
            ]),
            parse_mode=enums.ParseMode.HTML
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _send_history(client, telegram_id, chat_id, page, edit_message=None):
    all_uploads = await upload_repo.get_user_uploads(telegram_id, limit=50)
    if not all_uploads:
        text = Messages.history_empty()
        kb = Keyboards.back_to_start()
    else:
        total_pages = max(1, (len(all_uploads) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        page = max(1, min(page, total_pages))
        start = (page - 1) * ITEMS_PER_PAGE
        page_uploads = all_uploads[start:start + ITEMS_PER_PAGE]
        text = Messages.history_page(page_uploads, page, total_pages)
        kb = Keyboards.history(page, total_pages)
    if edit_message:
        await edit_message.edit_text(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
    else:
        await client.send_message(chat_id, text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)


async def _send_settings(client, telegram_id, chat_id, edit_message=None):
    user = await user_repo.find(telegram_id)
    settings = user.get_settings() if user else {}
    privacy = settings.get("privacy", "public")
    lang = settings.get("lang", "en")
    auto_title = settings.get("auto_title", True)
    text = Messages.settings_text(privacy, lang, auto_title)
    kb = Keyboards.settings(privacy, lang, auto_title)
    if edit_message:
        await edit_message.edit_text(text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)
    else:
        await client.send_message(chat_id, text, reply_markup=kb, parse_mode=enums.ParseMode.HTML)