"""
All bot message templates — centralized.
Use Messages.xxx() everywhere instead of hardcoding strings.
"""

from datetime import datetime, timezone, timedelta
from utils.formatters import make_progress_bar, format_size
from config import Config


# UPGRADE #10: file type → emoji map
_FILE_TYPE_EMOJI = {
    "mp4": "🎬", "mov": "🎬", "mkv": "📦", "webm": "🌐",
    "avi": "📼", "wmv": "📼", "flv": "📼", "mpeg": "📼", "3gp": "📱",
}


def _dual_progress(dl_pct: int, ul_pct: int) -> str:
    """UPGRADE #3: side-by-side download + upload progress bars."""
    dl_bar = make_progress_bar(dl_pct)
    ul_bar = make_progress_bar(ul_pct)
    dl_label = "✅" if dl_pct >= 100 else f"<b>{dl_pct}%</b>"
    ul_label = "✅" if ul_pct >= 100 else f"<b>{ul_pct}%</b>"
    return (
        f"📥 Download: {dl_bar} {dl_label}\n"
        f"📤 Upload:   {ul_bar} {ul_label}"
    )


class Messages:

    # ─── START / WELCOME ────────────────────────────────────────

    @staticmethod
    def start_caption(mention: str, connected: bool) -> str:
        # UPGRADE #1: different content for connected vs not
        if connected:
            status = (
                "✅ <b>YouTube Connected</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "Just send me a video to upload!"
            )
        else:
            status = (
                "⚠️ <b>YouTube not linked yet</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "Tap <b>Connect YouTube</b> below to get started."
            )
        return (
            f"Hey, {mention}\n"
            f"Welcome to GramUploader!\n\n"
            f"Upload your Telegram videos directly\n"
            f"to YouTube — fast, simple, private.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 <b>What I can do:</b>\n"
            f"  ▸ Upload videos with live progress\n"
            f"  ▸ Manage title, tags &amp; privacy\n"
            f"  ▸ Add captions &amp; thumbnails\n"
            f"  ▸ Organize into playlists\n"
            f"  ▸ Edit videos after upload\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

    @staticmethod
    def help_text() -> str:
        # UPGRADE #8: added /disconnect and /queue
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
            "   /disconnect — Unlink YouTube\n"
            "   /manage — YouTube Studio panel\n"
            "   /history — Upload history\n"
            "   /quota — Today's usage\n"
            "   /queue — Upload queue status\n"
            "   /settings — Preferences\n"
            "   /cancel — Cancel current input"
        )

    @staticmethod
    def about_text() -> str:
        return (
            "ℹ️ <b>About This Bot</b>\n\n"
            "🤖 <b>GramUploader</b>\n"
            f"📦 Version: {Config.VERSION}\n\n"
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
    def upload_confirm(title: str, size: int, privacy: str = "public",
                       file_type: str = "", quota_warning: bool = False,
                       duration: int = None, is_short: bool = False,
                       has_thumb: bool = False) -> str:
        # UPGRADE #5: duration line
        # UPGRADE #10: file type emoji
        privacy_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "🌍")
        UNSUPPORTED = {"avi", "wmv", "flv", "3gp", "mpeg"}

        type_line = ""
        if file_type and file_type != "unknown":
            ft_emoji = _FILE_TYPE_EMOJI.get(file_type, "🎞")
            warn = " ⚠️ <i>format may need re-encoding</i>" if file_type in UNSUPPORTED else ""
            type_line = f"{ft_emoji} Type: <code>.{file_type}</code>{warn}\n"

        dur_line = ""
        if duration and duration > 0:
            m, s = divmod(int(duration), 60)
            h, m = divmod(m, 60)
            dur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            shorts_hint = " 📱 <i>Shorts eligible</i>" if int(duration) <= 180 else ""
            dur_line = f"⏱ Duration: <code>{dur_str}</code>{shorts_hint}\n"

        # Shorts status line
        shorts_line = ""
        if is_short:
            thumb_status = "🖼 <b>Thumbnail set</b> — will be prepended as first 2s\n" if has_thumb else ""
            shorts_line = f"📱 <b>YouTube Short</b> — will upload as Short (<code>#Shorts</code> added, privacy forced Public)\n{thumb_status}"

        quota_line = "\n⚠️ <b>Last free upload today!</b> Upgrade for unlimited." if quota_warning else ""
        return (
            f"📹 <b>Video Detected!</b>\n\n"
            f"✏️ Title: <code>{title[:50]}</code>\n"
            f"📁 Size: <code>{format_size(size)}</code>\n"
            f"{dur_line}"
            f"{type_line}"
            f"{privacy_emoji} Privacy: <b>{privacy.capitalize()}</b>\n"
            f"{shorts_line}"
            f"{quota_line}\n\n"
            f"Tap <b>Upload Now</b> to proceed."
        )

    # ─── PROGRESS ───────────────────────────────────────────────

    @staticmethod
    def progress_downloading(percent: int, current: int, total: int,
                             speed: int = 0, eta: int = 0) -> str:
        # UPGRADE #3: dual stage progress
        from utils.formatters import format_eta
        speed_line = f"⚡ {format_size(speed)}/s · {format_eta(eta)}\n" if speed > 0 else ""
        return (
            f"📥 <b>Downloading from Telegram...</b>\n\n"
            f"{_dual_progress(percent, 0)}\n"
            f"📁 {format_size(current)} / {format_size(total)}\n"
            f"{speed_line}"
        )

    @staticmethod
    def progress_uploading(dl_pct: int, ul_pct: int, eta: int = 0) -> str:
        # UPGRADE #3: dual stage progress
        from utils.formatters import format_eta
        eta_line = f"⏱ {format_eta(eta)}\n" if eta > 0 else ""
        return (
            f"📤 <b>Uploading to YouTube...</b>\n\n"
            f"{_dual_progress(dl_pct, ul_pct)}\n"
            f"{eta_line}"
        )

    @staticmethod
    def upload_done(title: str, video_id: str, privacy: str = "public") -> str:
        url = f"https://youtube.com/watch?v={video_id}"
        privacy_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "🌍")
        return (
            f"✅ <b>Upload Complete!</b>\n\n"
            f"🎬 <b>{title}</b>\n"
            f"{privacy_emoji} {privacy.capitalize()}\n"
            f"🔗 {url}"
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
        # UPGRADE #4: show date per upload
        text = f"📋 <b>Upload History</b> (Page {page}/{total_pages})\n\n"
        for u in uploads:
            emoji = {
                "done": "✅", "failed": "❌",
                "uploading": "📤", "downloading": "📥", "pending": "⏳"
            }.get(u.status, "❓")
            title = (u.title or "Untitled")[:26]
            date_str = ""
            if hasattr(u, "created_at") and u.created_at:
                try:
                    date_str = f" <i>· {u.created_at.strftime('%d %b')}</i>"
                except Exception:
                    pass
            if u.youtube_id:
                text += f"{emoji} <a href='https://youtube.com/watch?v={u.youtube_id}'>{title}</a>{date_str}\n"
            else:
                text += f"{emoji} {title} — <i>{u.status}</i>{date_str}\n"
        return text.strip()

    # ─── QUOTA ──────────────────────────────────────────────────

    @staticmethod
    def quota_text(used: int, limit, plan: str) -> str:
        # UPGRADE #6: countdown to midnight UTC reset
        limit_str = str(limit) if limit != -1 else "∞"
        if isinstance(limit, int) and limit > 0:
            bar_pct = int((used / limit) * 100)
        else:
            bar_pct = 100 if plan != "free" else 0
        bar = make_progress_bar(bar_pct)

        now_utc = datetime.now(timezone.utc)
        midnight = (now_utc + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        diff = midnight - now_utc
        total_mins = int(diff.total_seconds() // 60)
        h, m = divmod(total_mins, 60)
        reset_str = f"{h}h {m:02d}m" if h else f"{m}m"

        return (
            f"📊 <b>Today's Usage</b>\n\n"
            f"Plan: <b>{plan.capitalize()}</b>\n"
            f"Uploads: <b>{used}</b> / <b>{limit_str}</b>\n"
            f"{bar}\n"
            f"🕐 Resets in <b>{reset_str}</b>\n\n"
            f"{'💎 Upgrade for unlimited uploads!' if plan == 'free' else '🌟 Premium active!'}"
        )

    # ─── SETTINGS ───────────────────────────────────────────────

    @staticmethod
    def settings_text(privacy: str, lang: str, auto_title: bool,
                      channel_name: str = None) -> str:
        # UPGRADE #7: optional channel name
        p_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "🌍")
        channel_line = f"📺 Channel: <b>{channel_name}</b>\n" if channel_name else ""
        return (
            f"⚙️ <b>Settings</b>\n\n"
            f"{channel_line}"
            f"{p_emoji} Default Privacy: <b>{privacy.capitalize()}</b>\n"
            f"🌐 Language: <b>{'English' if lang == 'en' else 'Malayalam'}</b>\n"
            f"✏️ Auto-title from caption: <b>{'ON' if auto_title else 'OFF'}</b>"
        )

    # ─── ADMIN ──────────────────────────────────────────────────

    @staticmethod
    def admin_stats(
        total_users: int, connected: int,
        total_uploads: int, uploads_today: int,
        success_rate: float, active_keys: int,
        queue_size: int = 0,
    ) -> str:
        # UPGRADE #9: show queue size
        queue_line = f"⏳ Queue: <b>{queue_size}</b> pending\n" if queue_size > 0 else ""
        return (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"🔗 Connected: <b>{connected}</b>\n"
            f"📤 Total Uploads: <b>{total_uploads}</b>\n"
            f"📅 Today: <b>{uploads_today}</b>\n"
            f"✅ Success Rate: <b>{success_rate:.1f}%</b>\n"
            f"🔑 API Keys: <b>{active_keys} active</b>\n"
            f"{queue_line}"
        )

    @staticmethod
    def admin_user_info(user, uploads_today: int, total_uploads: int) -> str:
        # UPGRADE #11: safe plan access whether string or enum
        plan = (user.plan if isinstance(user.plan, str) else user.plan.value).capitalize()
        status = "🚫 Banned" if user.is_banned else "✅ Active"
        connected = "✅ Yes" if user.youtube_connected else "❌ No"
        name = user.first_name or "—"
        username = f"@{user.username}" if user.username else "—"
        return (
            f"👤 <b>User Info</b>\n\n"
            f"ID: <code>{user.id}</code>\n"
            f"Name: <b>{name}</b>\n"
            f"Username: {username}\n"
            f"Plan: <b>{plan}</b>\n"
            f"Status: {status}\n"
            f"YouTube: {connected}\n"
            f"Uploads Today: <b>{uploads_today}</b>\n"
            f"Total Uploads: <b>{total_uploads}</b>"
        )

    @staticmethod
    def broadcast_confirm(count: int) -> str:
        return (
            f"📢 <b>Broadcast Confirmation</b>\n\n"
            f"This will send to <b>{count}</b> users.\n"
            f"Are you sure?"
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
