from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from database.db import user_repo, upload_repo, apikey_repo
from database.models import UploadStatus
from utils.messages import Messages
from utils.keyboards import Keyboards
from core.filters import is_admin
from utils.logger import log
from config import Config


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
            parse_mode="html"
        )

    @app.on_message(filters.command("addkey") & is_admin)
    async def add_key(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /addkey <api_key>")
            return
        key = parts[1].strip()
        await apikey_repo.add(key)
        await message.reply(f"✅ API key added successfully.")
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
        count = await user_repo.count()
        await message.reply(
            Messages.broadcast_confirm(count),
            reply_markup=Keyboards.broadcast_confirm(),
            parse_mode="html"
        )

    @app.on_callback_query(filters.regex("^broadcast_confirm$") & is_admin)
    async def broadcast_do(client: Client, cq: CallbackQuery):
        await cq.message.edit_text("📢 Broadcasting... please wait.")
        user_ids = await user_repo.get_all_ids()
        success, failed = 0, 0
        for uid in user_ids:
            try:
                await client.send_message(uid, "📢 Announcement from bot admin.")
                success += 1
            except Exception:
                failed += 1
        await cq.message.edit_text(
            f"📢 <b>Broadcast Done</b>\n\n✅ Sent: {success}\n❌ Failed: {failed}",
            parse_mode="html"
        )

    @app.on_callback_query(filters.regex("^broadcast_cancel$") & is_admin)
    async def broadcast_cancel(client: Client, cq: CallbackQuery):
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
            parse_mode="html"
        )

    @app.on_callback_query(filters.regex("^admin_maintenance_on$") & is_admin)
    async def cb_maintenance_on(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = True
        await cq.answer("🔧 Maintenance mode ON")

    @app.on_callback_query(filters.regex("^admin_maintenance_off$") & is_admin)
    async def cb_maintenance_off(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = False
        await cq.answer("✅ Maintenance mode OFF")
