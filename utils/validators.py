from config import Config

ALLOWED_MIME_TYPES = [
    "video/mp4", "video/x-matroska", "video/webm",
    "video/quicktime", "video/x-msvideo", "video/mpeg"
]


def is_valid_video(mime_type: str | None) -> bool:
    if not mime_type:
        return True  # Allow if unknown (let YouTube decide)
    return mime_type in ALLOWED_MIME_TYPES


def is_within_size_limit(size_bytes: int) -> bool:
    max_bytes = Config.MAX_FILE_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes


def sanitize_title(title: str) -> str:
    """Remove characters not allowed in YouTube titles"""
    import re
    # Strip ASCII control characters (newlines, tabs, carriage returns, etc.)
    # YouTube rejects titles with any \x00-\x1f characters
    title = re.sub(r'[\x00-\x1f]', ' ', title)
    # Strip characters explicitly forbidden by YouTube
    for char in ['<', '>', '"']:
        title = title.replace(char, '')
    # Collapse multiple spaces and trim
    title = re.sub(r' +', ' ', title).strip()
    return title[:100]  # YouTube title max 100 chars