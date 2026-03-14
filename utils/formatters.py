def make_progress_bar(percent: int, length: int = 10) -> str:
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_status_emoji(status: str) -> str:
    return {
        "done": "✅",
        "failed": "❌",
        "uploading": "📤",
        "downloading": "📥",
        "pending": "⏳"
    }.get(status, "❓")


def format_upload_history(uploads: list) -> str:
    if not uploads:
        return "📭 No uploads yet."

    text = "📋 **Recent Uploads:**\n\n"
    for u in uploads:
        emoji = format_status_emoji(u.status)
        yt_link = (
            f"[Watch](https://youtube.com/watch?v={u.youtube_id})"
            if u.youtube_id else "-"
        )
        title = (u.title or "Untitled")[:30]
        text += f"{emoji} **{title}**\n└ {yt_link}\n\n"
    return text.strip()
