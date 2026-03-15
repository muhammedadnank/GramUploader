"""
All InlineKeyboard layouts — centralized.
Use Keyboards.xxx() everywhere.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config


class Keyboards:

    # ─── START ──────────────────────────────────────────────────

    @staticmethod
    def start(telegram_id: int, connected: bool) -> InlineKeyboardMarkup:
        buttons = []
        if not connected:
            buttons.append([
                InlineKeyboardButton(
                    "🔗 Connect YouTube",
                    url=f"{Config.OAUTH_BASE_URL}/auth/{telegram_id}"
                )
            ])
        buttons += [
            [
                InlineKeyboardButton("❓ Help", callback_data="help"),
                InlineKeyboardButton("ℹ️ About", callback_data="about"),
            ],
            [
                InlineKeyboardButton("📋 History", callback_data="history:1"),
                InlineKeyboardButton("📊 Quota", callback_data="quota"),
            ],
            [
                InlineKeyboardButton("🎬 Manage Videos", callback_data="mgr_open"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("💎 Premium", callback_data="premium"),
            ],
            [
                InlineKeyboardButton("👤 Owner ↗", url=Config.OWNER_URL),
                InlineKeyboardButton("💬 Support ↗", url=Config.SUPPORT_URL),
            ],
            [
                InlineKeyboardButton("✖️ Close", callback_data="close"),
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def back_to_start() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back", callback_data="back_start")
        ]])

    # ─── CONNECT ────────────────────────────────────────────────

    @staticmethod
    def connect(telegram_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔗 Connect YouTube ▶️",
                url=f"{Config.OAUTH_BASE_URL}/auth/{telegram_id}"
            )],
            [InlineKeyboardButton("« Back", callback_data="back_start")]
        ])

    @staticmethod
    def reconnect(telegram_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔄 Reconnect YouTube",
                url=f"{Config.OAUTH_BASE_URL}/auth/{telegram_id}"
            )],
            [InlineKeyboardButton("« Back", callback_data="back_start")]
        ])

    # ─── UPLOAD CONFIRM ─────────────────────────────────────────

    @staticmethod
    def upload_confirm(upload_id: str, is_short: bool = False) -> InlineKeyboardMarkup:
        shorts_label = "📱 Short: ✅ ON" if is_short else "📱 Short: OFF"
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Upload Now", callback_data=f"upload_confirm:{upload_id}"),
                InlineKeyboardButton("🗑 Discard", callback_data=f"upload_cancel:{upload_id}"),
            ],
            [
                InlineKeyboardButton("✏️ Edit Title", callback_data=f"upload_edit_title:{upload_id}"),
                InlineKeyboardButton("🔒 Privacy", callback_data=f"upload_privacy:{upload_id}"),
            ],
            [
                InlineKeyboardButton(shorts_label, callback_data=f"upload_toggle_shorts:{upload_id}"),
            ],
        ])

    @staticmethod
    def privacy_select(upload_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌍 Public", callback_data=f"set_privacy:public:{upload_id}"),
                InlineKeyboardButton("🔒 Private", callback_data=f"set_privacy:private:{upload_id}"),
                InlineKeyboardButton("🔗 Unlisted", callback_data=f"set_privacy:unlisted:{upload_id}"),
            ],
            [InlineKeyboardButton("« Back", callback_data=f"upload_back:{upload_id}")]
        ])

    # ─── HISTORY ────────────────────────────────────────────────

    @staticmethod
    def history(page: int, total_pages: int) -> InlineKeyboardMarkup:
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"history:{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"history:{page+1}"))

        buttons = []
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"history:{page}")])
        buttons.append([InlineKeyboardButton("« Back", callback_data="back_start")])
        return InlineKeyboardMarkup(buttons)

    # ─── SETTINGS ───────────────────────────────────────────────

    @staticmethod
    def settings(privacy: str, lang: str, auto_title: bool) -> InlineKeyboardMarkup:
        def check(val, target): return f"{'✅' if val == target else ''} {target.capitalize()}"
        def toggle(val): return "✅ ON" if val else "OFF"

        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Default Privacy", callback_data="noop")],
            [
                InlineKeyboardButton(check(privacy, "public"), callback_data="set_default_privacy:public"),
                InlineKeyboardButton(check(privacy, "private"), callback_data="set_default_privacy:private"),
                InlineKeyboardButton(check(privacy, "unlisted"), callback_data="set_default_privacy:unlisted"),
            ],
            [InlineKeyboardButton("🌐 Language", callback_data="noop")],
            [
                InlineKeyboardButton(f"{'✅ ' if lang == 'en' else ''}English", callback_data="set_lang:en"),
                InlineKeyboardButton(f"{'✅ ' if lang == 'ml' else ''}Malayalam", callback_data="set_lang:ml"),
            ],
            [InlineKeyboardButton(
                f"✏️ Auto-title: {toggle(auto_title)}",
                callback_data="toggle_autotitle"
            )],
            [InlineKeyboardButton("« Back", callback_data="back_start")]
        ])

    # ─── ADMIN ──────────────────────────────────────────────────

    @staticmethod
    def admin_panel(maintenance: bool = False) -> InlineKeyboardMarkup:
        if maintenance:
            maint_btn = InlineKeyboardButton("✅ Maintenance OFF", callback_data="admin_maintenance_off")
        else:
            maint_btn = InlineKeyboardButton("🔧 Maintenance ON", callback_data="admin_maintenance_on")
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔑 API Keys", callback_data="admin_keys"),
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            ],
            [maint_btn],
            [
                InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats"),
            ],
            [
                InlineKeyboardButton("« Back", callback_data="back_start"),
            ],
        ])

    @staticmethod
    def broadcast_confirm() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Send", callback_data="broadcast_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel"),
            ]
        ])

    @staticmethod
    def admin_back() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back to Admin", callback_data="admin_stats")
        ]])

    @staticmethod
    def admin_user(user_id: int, is_banned: bool, plan: str) -> InlineKeyboardMarkup:
        ban_btn = (
            InlineKeyboardButton("✅ Unban", callback_data=f"admin_unban_user:{user_id}")
            if is_banned else
            InlineKeyboardButton("🚫 Ban", callback_data=f"admin_ban_user:{user_id}")
        )
        plan_btn = (
            InlineKeyboardButton("🆓 Set Free", callback_data=f"admin_set_free:{user_id}")
            if plan == "premium" else
            InlineKeyboardButton("💎 Set Premium", callback_data=f"admin_set_premium:{user_id}")
        )
        return InlineKeyboardMarkup([
            [ban_btn, plan_btn],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_stats")],
        ])

    # ─── PREMIUM ────────────────────────────────────────────────

    @staticmethod
    def premium() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Buy Premium ↗", url=Config.PREMIUM_URL)],
            [InlineKeyboardButton("« Back", callback_data="back_start")]
        ])
