from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram import enums
from pyrogram.types import Message, CallbackQuery
from database.db import user_repo, upload_repo, apikey_repo
from database.models import UploadStatus
from utils.messages import Messages
from utils.keyboards import Keyboards
from core.filters import is_admin
from utils.logger import log
from config import Config

# Store the broadcast source message per admin {admin_id: Message}
_broadcast_msg: dict = {}


def register(app: Client):

    @app.on_message(filters.command("stats") & is_admin)
    async def stats(client: Client, message: Message):
        total_users = await user_repo.count()
        connected = await user_repo.count_connected()
        total_uploads = await upload_repo.count()
        uploads_today = await upload_repo.count_today()
        done = await upload_repo.count_by_status(UploadStatus.DONE)
        success_rate = (done / total_uploads * 100) if total_uploads > 0 else 0
        keys = await apikey_repo.list_all()
        active_keys = sum(1 for k in keys if k.get("active") and k.get("units_used", 0) < 8000)

        await message.reply(
            Messages.admin_stats(total_users, connected, total_uploads, uploads_today, success_rate, active_keys),
            reply_markup=Keyboards.admin_panel(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_message(filters.command("addkey") & is_admin)
    async def add_key(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /addkey <api_key>")
            return
        key = parts[1].strip()
        await apikey_repo.add(key)
        await message.reply("✅ API key added successfully.")
        log.info(f"Admin {message.from_user.id} added new API key")

    @app.on_message(filters.command("ban") & is_admin)
    async def ban_user(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /ban <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            await user_repo.ban(target_id, True)
            await message.reply(f"✅ User `{target_id}` banned.")
            log.warning(f"Admin banned user {target_id}")
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    @app.on_message(filters.command("unban") & is_admin)
    async def unban_user(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /unban <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            await user_repo.ban(target_id, False)
            await message.reply(f"✅ User `{target_id}` unbanned.")
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    @app.on_message(filters.command("broadcast") & is_admin)
    async def broadcast_start(client: Client, message: Message):
        if not message.reply_to_message:
            await message.reply("Reply to a message to broadcast it.\nUsage: Reply + /broadcast")
            return
        # Store the source message to forward later
        _broadcast_msg[message.from_user.id] = message.reply_to_message
        count = await user_repo.count()
        await message.reply(
            Messages.broadcast_confirm(count),
            reply_markup=Keyboards.broadcast_confirm(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^broadcast_confirm$") & is_admin)
    async def broadcast_do(client: Client, cq: CallbackQuery):
        source_msg = _broadcast_msg.pop(cq.from_user.id, None)
        if not source_msg:
            await cq.message.edit_text("❌ No broadcast message found. Use /broadcast again.")
            return

        await cq.message.edit_text("📢 Broadcasting... please wait.")
        user_ids = await user_repo.get_all_ids()
        success, failed = 0, 0
        for uid in user_ids:
            try:
                await source_msg.forward(uid)
                success += 1
            except Exception:
                failed += 1

        await cq.message.edit_text(
            f"📢 <b>Broadcast Done</b>\n\n✅ Sent: {success}\n❌ Failed: {failed}",
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^broadcast_cancel$") & is_admin)
    async def broadcast_cancel(client: Client, cq: CallbackQuery):
        _broadcast_msg.pop(cq.from_user.id, None)
        await cq.message.edit_text("❌ Broadcast cancelled.")

    @app.on_callback_query(filters.regex("^admin_stats$") & is_admin)
    async def cb_admin_stats(client: Client, cq: CallbackQuery):
        total_users = await user_repo.count()
        connected = await user_repo.count_connected()
        total_uploads = await upload_repo.count()
        uploads_today = await upload_repo.count_today()
        done = await upload_repo.count_by_status(UploadStatus.DONE)
        success_rate = (done / total_uploads * 100) if total_uploads > 0 else 0
        keys = await apikey_repo.list_all()
        active_keys = sum(1 for k in keys if k.get("active") and k.get("units_used", 0) < 8000)
        await cq.message.edit_text(
            Messages.admin_stats(total_users, connected, total_uploads, uploads_today, success_rate, active_keys),
            reply_markup=Keyboards.admin_panel(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_broadcast$") & is_admin)
    async def cb_admin_broadcast(client: Client, cq: CallbackQuery):
        await cq.message.edit_text(
            "📢 <b>Broadcast</b>\n\n"
            "Reply to any message with /broadcast to send it to all users.\n\n"
            "<i>Go back and use the /broadcast command while replying to a message.</i>",
            reply_markup=Keyboards.back_to_start(),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex("^admin_keys$") & is_admin)
    async def cb_admin_keys(client: Client, cq: CallbackQuery):
        keys = await apikey_repo.list_all()
        if not keys:
            text = "🔑 <b>API Keys</b>\n\nNo keys added yet.\nUse /addkey <key> to add one."
        else:
            lines = []
            for k in keys:
                status = "✅" if k.get("active") else "❌"
                used = k.get("units_used", 0)
                short = k.get("key", "")[:12] + "..."
                lines.append(f"{status} <code>{short}</code> — {used}/8000 units")
            text = "🔑 <b>API Keys</b>\n\n" + "\n".join(lines)
        await cq.message.edit_text(text, reply_markup=Keyboards.back_to_start(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex("^admin_maintenance_on$") & is_admin)
    async def cb_maintenance_on(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = True
        await cq.answer("🔧 Maintenance mode ON")

    @app.on_callback_query(filters.regex("^admin_maintenance_off$") & is_admin)
    async def cb_maintenance_off(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = False
        await cq.answer("✅ Maintenance mode OFF")