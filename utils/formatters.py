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


def format_eta(seconds: int) -> str:
    """Format seconds into human-readable ETA string."""
    if seconds <= 0:
        return "almost done"
    if seconds < 60:
        return f"{seconds}s left"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:02d}s left"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins:02d}m left"


def format_status_emoji(status: str) -> str:
    return {
        "done": "✅",
        "failed": "❌",
        "uploading": "📤",
        "downloading": "📥",
        "pending": "⏳"
    }.get(status, "❓")


# format_upload_history() removed — was dead code using Markdown, not HTML