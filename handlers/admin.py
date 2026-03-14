from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram import enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import user_repo, upload_repo, apikey_repo
from database.models import UploadStatus, Plan
from utils.messages import Messages
from utils.keyboards import Keyboards
from core.filters import is_admin
from utils.logger import log
from config import Config
import asyncio

# Store the broadcast source message per admin {admin_id: Message}
_broadcast_msg: dict = {}


# ── Shared helper ────────────────────────────────────────────────────────────

async def _fetch_stats() -> dict:
    total_users = await user_repo.count()
    connected = await user_repo.count_connected()
    total_uploads = await upload_repo.count()
    uploads_today = await upload_repo.count_today()
    done = await upload_repo.count_by_status(UploadStatus.DONE)
    success_rate = (done / total_uploads * 100) if total_uploads > 0 else 0
    keys = await apikey_repo.list_all()
    active_keys = sum(1 for k in keys if k.get("active") and k.get("units_used", 0) < 8000)
    return dict(
        total_users=total_users, connected=connected,
        total_uploads=total_uploads, uploads_today=uploads_today,
        success_rate=success_rate, active_keys=active_keys
    )


def register(app: Client):

    # ─── /stats ─────────────────────────────────────────────────

    @app.on_message(filters.command("stats") & is_admin)
    async def stats(client: Client, message: Message):
        s = await _fetch_stats()
        await message.reply(
            Messages.admin_stats(**s),
            reply_markup=Keyboards.admin_panel(),
            parse_mode=enums.ParseMode.HTML
        )

    # ─── /addkey ────────────────────────────────────────────────

    @app.on_message(filters.command("addkey") & is_admin)
    async def add_key(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /addkey <api_key>")
            return
        key = parts[1].strip()
        existing = await apikey_repo.find_by_key(key)
        if existing:
            await message.reply("⚠️ This API key already exists.")
            return
        await apikey_repo.add(key)
        await message.reply("✅ API key added successfully.")
        log.info(f"Admin {message.from_user.id} added new API key")

    # ─── /deletekey ─────────────────────────────────────────────

    @app.on_message(filters.command("deletekey") & is_admin)
    async def delete_key(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /deletekey <api_key>")
            return
        key = parts[1].strip()
        existing = await apikey_repo.find_by_key(key)
        if not existing:
            await message.reply("❌ Key not found.")
            return
        await apikey_repo.deactivate(existing["_id"])
        await message.reply("✅ API key deactivated.")
        log.info(f"Admin {message.from_user.id} deactivated API key")

    # ─── /ban ───────────────────────────────────────────────────

    @app.on_message(filters.command("ban") & is_admin)
    async def ban_user(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /ban <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            # upsert=True so ban works even if user never started the bot
            await user_repo.ban(target_id, True)
            await message.reply(f"✅ User <code>{target_id}</code> banned.", parse_mode=enums.ParseMode.HTML)
            log.warning(f"Admin {message.from_user.id} banned user {target_id}")
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    # ─── /unban ─────────────────────────────────────────────────

    @app.on_message(filters.command("unban") & is_admin)
    async def unban_user(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /unban <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            await user_repo.ban(target_id, False)
            await message.reply(f"✅ User <code>{target_id}</code> unbanned.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    # ─── /user ──────────────────────────────────────────────────

    @app.on_message(filters.command("user") & is_admin)
    async def user_info(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /user <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            user = await user_repo.find(target_id)
            if not user:
                await message.reply("❌ User not found.")
                return
            uploads_today = await user_repo.get_uploads_today(target_id)
            total_uploads = await upload_repo.count_by_user(target_id)
            await message.reply(
                Messages.admin_user_info(user, uploads_today, total_uploads),
                reply_markup=Keyboards.admin_user(target_id, user.is_banned, user.plan.value),
                parse_mode=enums.ParseMode.HTML
            )
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    # ─── /setpremium / /setfree ─────────────────────────────────

    @app.on_message(filters.command("setpremium") & is_admin)
    async def set_premium(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /setpremium <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            await user_repo.set_plan(target_id, Plan.PREMIUM)
            await message.reply(f"✅ User <code>{target_id}</code> → Premium.", parse_mode=enums.ParseMode.HTML)
            log.info(f"Admin {message.from_user.id} set user {target_id} to premium")
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    @app.on_message(filters.command("setfree") & is_admin)
    async def set_free(client: Client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply("Usage: /setfree <user_id>")
            return
        try:
            target_id = int(parts[1].strip())
            await user_repo.set_plan(target_id, Plan.FREE)
            await message.reply(f"✅ User <code>{target_id}</code> → Free.", parse_mode=enums.ParseMode.HTML)
        except ValueError:
            await message.reply("❌ Invalid user ID.")

    # ─── /broadcast ─────────────────────────────────────────────

    @app.on_message(filters.command("broadcast") & is_admin)
    async def broadcast_start(client: Client, message: Message):
        if not message.reply_to_message:
            await message.reply("Reply to a message to broadcast it.\nUsage: Reply + /broadcast")
            return
        _broadcast_msg[message.from_user.id] = message.reply_to_message
        count = await user_repo.count()
        await message.reply(
            Messages.broadcast_confirm(count),
            reply_markup=Keyboards.broadcast_confirm(),
            parse_mode=enums.ParseMode.HTML
        )

    # ─── CALLBACKS ──────────────────────────────────────────────

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
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await source_msg.forward(uid)
                    success += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)  # ~20 msgs/sec — stay under Telegram limit

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
        s = await _fetch_stats()
        try:
            await cq.message.edit_text(
                Messages.admin_stats(**s),
                reply_markup=Keyboards.admin_panel(),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex("^admin_broadcast$") & is_admin)
    async def cb_admin_broadcast(client: Client, cq: CallbackQuery):
        await cq.message.edit_text(
            "📢 <b>Broadcast</b>\n\n"
            "Reply to any message with /broadcast to send it to all users.\n\n"
            "<i>Go back and use the /broadcast command while replying to a message.</i>",
            reply_markup=Keyboards.admin_back(),
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
        await cq.message.edit_text(text, reply_markup=Keyboards.admin_back(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex("^admin_maintenance_on$") & is_admin)
    async def cb_maintenance_on(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = True
        await cq.answer("🔧 Maintenance mode ON")
        s = await _fetch_stats()
        try:
            await cq.message.edit_text(
                Messages.admin_stats(**s),
                reply_markup=Keyboards.admin_panel(),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex("^admin_maintenance_off$") & is_admin)
    async def cb_maintenance_off(client: Client, cq: CallbackQuery):
        Config.MAINTENANCE_MODE = False
        await cq.answer("✅ Maintenance mode OFF")
        s = await _fetch_stats()
        try:
            await cq.message.edit_text(
                Messages.admin_stats(**s),
                reply_markup=Keyboards.admin_panel(),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass

    # ─── USER ACTION CALLBACKS ───────────────────────────────────

    @app.on_callback_query(filters.regex(r"^admin_ban_user:(\d+)$") & is_admin)
    async def cb_ban_user(client: Client, cq: CallbackQuery):
        target_id = int(cq.matches[0].group(1))
        await user_repo.ban(target_id, True)
        await cq.answer(f"✅ User {target_id} banned.")
        user = await user_repo.find(target_id)
        uploads_today = await user_repo.get_uploads_today(target_id)
        total_uploads = await upload_repo.count_by_user(target_id)
        await cq.message.edit_reply_markup(
            Keyboards.admin_user(target_id, True, user.plan.value if user else "free")
        )

    @app.on_callback_query(filters.regex(r"^admin_unban_user:(\d+)$") & is_admin)
    async def cb_unban_user(client: Client, cq: CallbackQuery):
        target_id = int(cq.matches[0].group(1))
        await user_repo.ban(target_id, False)
        await cq.answer(f"✅ User {target_id} unbanned.")
        user = await user_repo.find(target_id)
        await cq.message.edit_reply_markup(
            Keyboards.admin_user(target_id, False, user.plan.value if user else "free")
        )

    @app.on_callback_query(filters.regex(r"^admin_set_premium:(\d+)$") & is_admin)
    async def cb_set_premium(client: Client, cq: CallbackQuery):
        target_id = int(cq.matches[0].group(1))
        await user_repo.set_plan(target_id, Plan.PREMIUM)
        await cq.answer("✅ Set to Premium.")
        await cq.message.edit_reply_markup(
            Keyboards.admin_user(target_id, False, "premium")
        )

    @app.on_callback_query(filters.regex(r"^admin_set_free:(\d+)$") & is_admin)
    async def cb_set_free(client: Client, cq: CallbackQuery):
        target_id = int(cq.matches[0].group(1))
        await user_repo.set_plan(target_id, Plan.FREE)
        await cq.answer("✅ Set to Free.")
        await cq.message.edit_reply_markup(
            Keyboards.admin_user(target_id, False, "free")
        )