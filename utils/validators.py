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
    # Single quote (') is valid in YouTube titles — don't strip it
    forbidden = ['<', '>', '"']
    for char in forbidden:
        title = title.replace(char, '')
    return title.strip()[:100]  # YouTube title max 100 chars