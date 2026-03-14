"""
All bot message templates — centralized.
Use Messages.xxx() everywhere instead of hardcoding strings.
"""

from utils.formatters import make_progress_bar, format_size
from utils.fonts import sc


class Messages:

    # ─── START / WELCOME ────────────────────────────────────────

    @staticmethod
    def start_caption(mention: str, connected: bool) -> str:
        status = (
            "✅ YouTube Connected\nReady — just send me a video!"
            if connected else
            "⚠️ YouTube not linked yet.\nTap <b>Connect</b> below to get started."
        )
        return (
            f"{sc('hey')}, {mention}\n"
            f"{sc('welcome to gramuploader!')}\n\n"
            f"Upload your Telegram videos directly\n"
            f"to YouTube — fast, simple, private.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 <b>What I can do:</b>\n"
            f"  ▸ Upload videos with live progress\n"
            f"  ▸ Manage title, tags &amp; privacy\n"
            f"  ▸ Add captions &amp; thumbnails\n"
            f"  ▸ Organize into playlists\n"
            f"  ▸ Edit videos after upload\n\n"
            f"๏ {sc('click on the how to use button to get information about my commands.')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

    @staticmethod
    def help_text() -> str:
        return (
            "📖 <b>How to use this bot:</b>\n\n"
            "<b>1. Connect YouTube</b>\n"
            "   Tap /connect → Authorize Google account\n\n"
            "<b>2. Send a Video</b>\n"
            "   Send any video/document file\n"
            "   Add caption → becomes YouTube title\n\n"
            "<b>3. Track Progress</b>\n"
            "   Live download + upload progress\n"
            "   Get YouTube link when done\n\n"
            "📋 <b>Commands:</b>\n"
            "   /start — Main menu\n"
            "   /connect — Link YouTube\n"
            "   /history — Upload history\n"
            "   /quota — Today's usage\n"
            "   /settings — Preferences\n"
            "   /cancel — Cancel current upload"
        )

    @staticmethod
    def about_text() -> str:
        return (
            "ℹ️ <b>About This Bot</b>\n\n"
            "🤖 <b>GramUploader</b>\n"
            "📦 Version: 2.4.0\n\n"
            "Upload your Telegram videos directly to\n"
            "YouTube with one click — no PC needed.\n\n"
            "⚙️ <b>Tech Stack:</b>\n"
            "  • Kurigram (MTProto)\n"
            "  • YouTube Data API v3\n"
            "  • MongoDB Atlas\n"
            "  • FastAPI (OAuth2)\n\n"
            "🔒 Your data is safe & never shared."
        )

    # ─── CONNECT / AUTH ─────────────────────────────────────────

    @staticmethod
    def connect_text() -> str:
        return (
            "🔗 <b>Connect Your YouTube Channel</b>\n\n"
            "Tap the button below to authorize.\n"
            "You'll be redirected to Google.\n\n"
            "✅ One-time setup — stays connected\n"
            "🔒 We only request upload permissions"
        )

    @staticmethod
    def already_connected() -> str:
        return (
            "✅ <b>YouTube Already Connected!</b>\n\n"
            "Just send me a video to upload.\n\n"
            "Want to reconnect a different account?\n"
            "Tap <b>Reconnect</b> below."
        )

    # ─── UPLOAD CONFIRMATION ────────────────────────────────────

    @staticmethod
    def upload_confirm(title: str, size: int, privacy: str = "public") -> str:
        privacy_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "🌍")
        return (
            f"📹 <b>Video Detected!</b>\n\n"
            f"📁 Size: <code>{format_size(size)}</code>\n"
            f"{privacy_emoji} Privacy: <b>{privacy.capitalize()}</b>\n"
            f"✏️ Title: <code>{title[:50]}</code>\n\n"
            f"Tap <b>Upload Now</b> to proceed."
        )

    # ─── PROGRESS ───────────────────────────────────────────────

    @staticmethod
    def progress_downloading(percent: int, current: int, total: int) -> str:
        bar = make_progress_bar(percent)
        return (
            f"📥 <b>Downloading from Telegram...</b>\n\n"
            f"{bar} <b>{percent}%</b>\n"
            f"📁 {format_size(current)} / {format_size(total)}"
        )

    @staticmethod
    def progress_uploading(dl_done: bool, ul_percent: int) -> str:
        dl_bar = make_progress_bar(100)
        ul_bar = make_progress_bar(ul_percent)
        return (
            f"📥 Download: {dl_bar} ✅\n"
            f"📤 <b>Uploading to YouTube...</b>\n\n"
            f"{ul_bar} <b>{ul_percent}%</b>"
        )

    @staticmethod
    def upload_done(title: str, video_id: str) -> str:
        url = f"https://youtube.com/watch?v={video_id}"
        return (
            f"✅ <b>Upload Complete!</b>\n\n"
            f"🎬 {title}\n"
            f"🔗 {url}\n\n"
            f"Tap the link to view your video."
        )

    @staticmethod
    def upload_failed(error: str) -> str:
        return (
            f"❌ <b>Upload Failed</b>\n\n"
            f"<code>{error[:200]}</code>\n\n"
            f"Please try again or contact support."
        )

    @staticmethod
    def upload_queued(title: str, size: int, position: int) -> str:
        return (
            f"✅ <b>Added to Queue!</b>\n\n"
            f"🎬 <code>{title[:50]}</code>\n"
            f"📁 {format_size(size)}\n"
            f"📊 Queue position: #{position}\n\n"
            f"I'll notify you when done."
        )

    # ─── HISTORY ────────────────────────────────────────────────

    @staticmethod
    def history_empty() -> str:
        return (
            "📭 <b>No Uploads Yet</b>\n\n"
            "Send me a video to get started!"
        )

    @staticmethod
    def history_page(uploads: list, page: int, total_pages: int) -> str:
        text = f"📋 <b>Upload History</b> (Page {page}/{total_pages})\n\n"
        for u in uploads:
            emoji = {
                "done": "✅", "failed": "❌",
                "uploading": "📤", "downloading": "📥", "pending": "⏳"
            }.get(u.status, "❓")
            title = (u.title or "Untitled")[:28]
            if u.youtube_id:
                text += f"{emoji} <a href='https://youtube.com/watch?v={u.youtube_id}'>{title}</a>\n"
            else:
                text += f"{emoji} {title} — <i>{u.status}</i>\n"
        return text.strip()

    # ─── QUOTA ──────────────────────────────────────────────────

    @staticmethod
    def quota_text(used: int, limit, plan: str) -> str:
        limit_str = str(limit) if limit != -1 else "∞"
        bar = make_progress_bar(
            int((used / limit) * 100) if isinstance(limit, int) and limit > 0 else 0
        )
        return (
            f"📊 <b>Today's Usage</b>\n\n"
            f"Plan: <b>{plan.capitalize()}</b>\n"
            f"Uploads: <b>{used}</b> / <b>{limit_str}</b>\n"
            f"{bar}\n\n"
            f"{'💎 Upgrade for unlimited uploads!' if plan == 'free' else '🌟 Premium active!'}"
        )

    # ─── SETTINGS ───────────────────────────────────────────────

    @staticmethod
    def settings_text(privacy: str, lang: str, auto_title: bool) -> str:
        p_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "🌍")
        return (
            f"⚙️ <b>Settings</b>\n\n"
            f"{p_emoji} Default Privacy: <b>{privacy.capitalize()}</b>\n"
            f"🌐 Language: <b>{'English' if lang == 'en' else 'Malayalam'}</b>\n"
            f"✏️ Auto-title from caption: <b>{'ON' if auto_title else 'OFF'}</b>"
        )

    @staticmethod
    def admin_user_info(user, uploads_today: int, total_uploads: int) -> str:
        plan = user.plan.value.capitalize()
        status = "🚫 Banned" if user.is_banned else "✅ Active"
        connected = "✅ Yes" if user.youtube_connected else "❌ No"
        name = user.first_name or "—"
        username = f"@{user.username}" if user.username else "—"
        return (
            f"👤 <b>User Info</b>

"
            f"ID: <code>{user.id}</code>
"
            f"Name: <b>{name}</b>
"
            f"Username: {username}
"
            f"Plan: <b>{plan}</b>
"
            f"Status: {status}
"
            f"YouTube: {connected}
"
            f"Uploads Today: <b>{uploads_today}</b>
"
            f"Total Uploads: <b>{total_uploads}</b>"
        )

    # ─── ERRORS ─────────────────────────────────────────────────

    @staticmethod
    def not_connected() -> str:
        return (
            "❌ <b>YouTube Not Connected</b>\n\n"
            "Use /connect to link your channel first."
        )

    @staticmethod
    def daily_limit(limit: int) -> str:
        return (
            f"⚠️ <b>Daily Limit Reached</b>\n\n"
            f"Free plan: {limit} uploads/day\n\n"
            f"💎 Upgrade to Premium for unlimited uploads!"
        )

    @staticmethod
    def file_too_large(size: int, max_mb: int) -> str:
        return (
            f"📦 <b>File Too Large</b>\n\n"
            f"Your file: <b>{format_size(size)}</b>\n"
            f"Maximum: <b>{max_mb} MB</b>\n\n"
            f"Please send a smaller file."
        )

    @staticmethod
    def quota_exceeded() -> str:
        return (
            "😔 <b>YouTube Quota Exceeded</b>\n\n"
            "⏰ Resets at midnight UTC.\n"
            "Please try again tomorrow."
        )

    @staticmethod
    def banned() -> str:
        return "🚫 You have been banned from using this bot."

    @staticmethod
    def maintenance() -> str:
        return "🔧 Bot is under maintenance. Please try later."

    # ─── ADMIN ──────────────────────────────────────────────────

    @staticmethod
    def admin_stats(
        total_users: int, connected: int,
        total_uploads: int, uploads_today: int,
        success_rate: float, active_keys: int
    ) -> str:
        return (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"🔗 Connected: <b>{connected}</b>\n"
            f"📤 Total Uploads: <b>{total_uploads}</b>\n"
            f"📅 Today: <b>{uploads_today}</b>\n"
            f"✅ Success Rate: <b>{success_rate:.1f}%</b>\n"
            f"🔑 API Keys: <b>{active_keys} active</b>"
        )

    @staticmethod
    def broadcast_confirm(count: int) -> str:
        return (
            f"📢 <b>Broadcast Confirmation</b>\n\n"
            f"This will send to <b>{count}</b> users.\n"
            f"Are you sure?"
        )