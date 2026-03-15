"""
Manager panel message templates — YouTube Studio-like
"""
from services.youtube_manager import format_duration, format_count
from handlers.video import _pending, _pending_edit, _pending_thumb


class ManagerMessages:

    @staticmethod
    def video_list_header(total: int) -> str:
        return (
            f"🎬 <b>My Videos</b> ({total})\n\n"
            f"Tap any video to manage it."
        )

    @staticmethod
    def video_panel(video: dict) -> str:
        s = video["snippet"]
        st = video["status"]
        stats = video.get("statistics", {})
        cd = video.get("contentDetails", {})

        title = s.get("title", "Untitled")
        raw_desc = s.get("description") or ""
        description = raw_desc[:100]
        privacy = st.get("privacyStatus", "unknown")
        privacy_emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "❓")
        duration = format_duration(cd.get("duration", "PT0S"))
        views = format_count(stats.get("viewCount", 0))
        likes = format_count(stats.get("likeCount", 0))
        comments = format_count(stats.get("commentCount", 0))
        published = s.get("publishedAt", "")[:10]
        category_id = s.get("categoryId", "22")

        kids = "✅" if st.get("selfDeclaredMadeForKids") else "❌"
        embed = "✅" if st.get("embeddable", True) else "❌"
        lic = "CC" if st.get("license") == "creativeCommon" else "Standard"

        tags = s.get("tags", [])
        tags_str = ", ".join(tags[:5]) + ("..." if len(tags) > 5 else "") if tags else "None"

        return (
            f"🎬 <b>{title}</b>\n\n"
            f"{privacy_emoji} <b>Privacy:</b> {privacy.capitalize()}\n"
            f"⏱ <b>Duration:</b> {duration}\n"
            f"📅 <b>Published:</b> {published}\n\n"
            f"📊 <b>Stats:</b>\n"
            f"  👁 Views: <b>{views}</b>\n"
            f"  👍 Likes: <b>{likes}</b>\n"
            f"  💬 Comments: <b>{comments}</b>\n\n"
            f"🏷 <b>Tags:</b> <i>{tags_str}</i>\n"
            f"📝 <b>Desc:</b> <i>{description or 'Empty'}{'…' if len(raw_desc) > 100 else ''}</i>\n\n"
            f"⚙️ Kids: {kids}  |  Embed: {embed}  |  License: {lic}"
        )

    @staticmethod
    def channel_stats(channel: dict) -> str:
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        name = snippet.get("title", "Unknown")
        subs = format_count(stats.get("subscriberCount", 0))
        views = format_count(stats.get("viewCount", 0))
        videos = stats.get("videoCount", 0)
        hidden = stats.get("hiddenSubscriberCount", False)

        return (
            f"📺 <b>{name}</b>\n\n"
            f"👥 Subscribers: <b>{'Hidden' if hidden else subs}</b>\n"
            f"👁 Total Views: <b>{views}</b>\n"
            f"🎬 Videos: <b>{videos}</b>"
        )

    @staticmethod
    def edit_prompt(field: str, current: str) -> str:
        return (
            f"✏️ <b>Edit {field}</b>\n\n"
            f"Current:\n<i>{current[:200] or 'Empty'}</i>\n\n"
            f"Send the new {field.lower()} as a message.\n"
            f"Send /cancel to abort."
        )

    @staticmethod
    def thumbnail_prompt(video_id: str) -> str:
        return (
            f"🖼 <b>Set Thumbnail</b>\n\n"
            f"Send a photo to set as thumbnail.\n"
            f"Recommended size: 1280×720px (16:9)\n\n"
            f"Send /cancel to abort."
        )

    @staticmethod
    def caption_prompt() -> str:
        return (
            f"📝 <b>Upload Caption</b>\n\n"
            f"Send your <b>.srt</b> file.\n"
            f"After that, select the language.\n\n"
            f"Send /cancel to abort."
        )

    @staticmethod
    def caption_lang_prompt() -> str:
        return (
            f"🌐 <b>Select Caption Language</b>\n\n"
            f"Send language code (e.g. <code>en</code>, <code>ml</code>, <code>hi</code>)"
        )

    @staticmethod
    def update_success(field: str) -> str:
        return f"✅ <b>{field}</b> updated successfully!"

    @staticmethod
    def delete_confirm(title: str) -> str:
        return (
            f"⚠️ <b>Delete Video?</b>\n\n"
            f"<i>{title}</i>\n\n"
            f"This <b>cannot be undone</b>. The video will be permanently deleted from YouTube."
        )

    @staticmethod
    def delete_done(title: str) -> str:
        return f"🗑 <b>Deleted</b>\n\n<i>{title}</i> has been removed from YouTube."

    @staticmethod
    def schedule_prompt() -> str:
        return (
            f"🕐 <b>Schedule Publish</b>\n\n"
            f"Send date and time in this format:\n"
            f"<code>YYYY-MM-DD HH:MM</code>\n\n"
            f"Example: <code>2026-04-01 18:00</code>\n"
            f"(UTC timezone)\n\n"
            f"Send /cancel to abort."
        )
