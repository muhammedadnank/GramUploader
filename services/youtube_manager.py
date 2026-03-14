"""
YouTube Manager Service
Fetch, edit, delete, manage videos on YouTube via Data API v3
"""

import asyncio
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from database.db import user_repo
from services.youtube_uploader import get_credentials
from utils.logger import log


async def _build_youtube(telegram_id: int):
    creds = await get_credentials(telegram_id)
    if not creds:
        raise Exception("YouTube not connected. Use /connect first.")
    return build("youtube", "v3", credentials=creds)


# ─── VIDEO LIST ─────────────────────────────────────────────────

async def get_my_videos(telegram_id: int, page_token: str = None, max_results: int = 8) -> dict:
    """Fetch user's uploaded videos — returns items + nextPageToken"""
    try:
        yt = await _build_youtube(telegram_id)

        # Get uploads playlist ID from channel
        channel_resp = await asyncio.to_thread(
            lambda: yt.channels().list(part="contentDetails", mine=True).execute()
        )
        uploads_playlist = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Fetch videos from uploads playlist
        kwargs = dict(
            part="snippet,contentDetails",
            playlistId=uploads_playlist,
            maxResults=max_results
        )
        if page_token:
            kwargs["pageToken"] = page_token

        resp = await asyncio.to_thread(
            lambda: yt.playlistItems().list(**kwargs).execute()
        )

        video_ids = [i["contentDetails"]["videoId"] for i in resp.get("items", [])]

        if not video_ids:
            return {"items": [], "nextPageToken": None, "prevPageToken": None}

        # Fetch full video details
        videos_resp = await asyncio.to_thread(
            lambda: yt.videos().list(
                part="snippet,status,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()
        )

        return {
            "items": videos_resp.get("items", []),
            "nextPageToken": resp.get("nextPageToken"),
            "prevPageToken": resp.get("prevPageToken"),
        }

    except HttpError as e:
        log.error(f"YouTube get_my_videos error: {e}")
        raise Exception(f"Failed to fetch videos: {e.reason}")


async def get_video_details(telegram_id: int, video_id: str) -> dict:
    """Get full details for a single video"""
    try:
        yt = await _build_youtube(telegram_id)
        resp = await asyncio.to_thread(
            lambda: yt.videos().list(
                part="snippet,status,statistics,contentDetails,processingDetails",
                id=video_id
            ).execute()
        )
        items = resp.get("items", [])
        if not items:
            raise Exception("Video not found.")
        return items[0]
    except HttpError as e:
        raise Exception(f"Failed to fetch video: {e.reason}")


# ─── VIDEO EDIT ─────────────────────────────────────────────────

async def update_video(telegram_id: int, video_id: str, updates: dict) -> dict:
    """
    Update video metadata.
    updates can contain: title, description, tags, categoryId,
    privacyStatus, madeForKids, embeddable, license, publishAt
    """
    try:
        yt = await _build_youtube(telegram_id)

        # Fetch current snippet & status
        current = await get_video_details(telegram_id, video_id)
        snippet = current["snippet"]
        status = current["status"]

        # Apply snippet updates
        if "title" in updates:
            snippet["title"] = updates["title"][:100]
        if "description" in updates:
            snippet["description"] = updates["description"][:5000]
        if "tags" in updates:
            snippet["tags"] = updates["tags"][:500]
        if "categoryId" in updates:
            snippet["categoryId"] = updates["categoryId"]
        if "defaultLanguage" in updates:
            snippet["defaultLanguage"] = updates["defaultLanguage"]

        # Apply status updates
        if "privacyStatus" in updates:
            status["privacyStatus"] = updates["privacyStatus"]
        if "madeForKids" in updates:
            status["selfDeclaredMadeForKids"] = updates["madeForKids"]
        if "embeddable" in updates:
            status["embeddable"] = updates["embeddable"]
        if "license" in updates:
            status["license"] = updates["license"]
        if "publishAt" in updates:
            status["publishAt"] = updates["publishAt"]
            status["privacyStatus"] = "private"  # required for scheduled

        resp = await asyncio.to_thread(
            lambda: yt.videos().update(
                part="snippet,status",
                body={"id": video_id, "snippet": snippet, "status": status}
            ).execute()
        )
        log.info(f"Updated video {video_id} for user {telegram_id}")
        return resp

    except HttpError as e:
        raise Exception(f"Failed to update video: {e.reason}")


async def delete_video(telegram_id: int, video_id: str):
    """Delete a video from YouTube"""
    try:
        yt = await _build_youtube(telegram_id)
        await asyncio.to_thread(
            lambda: yt.videos().delete(id=video_id).execute()
        )
        log.info(f"Deleted video {video_id} for user {telegram_id}")
    except HttpError as e:
        raise Exception(f"Failed to delete video: {e.reason}")


# ─── THUMBNAIL ──────────────────────────────────────────────────

async def set_thumbnail(telegram_id: int, video_id: str, image_path: str):
    """Set custom thumbnail for a video"""
    try:
        yt = await _build_youtube(telegram_id)
        media = MediaFileUpload(image_path, mimetype="image/jpeg", resumable=True)
        await asyncio.to_thread(
            lambda: yt.thumbnails().set(videoId=video_id, media_body=media).execute()
        )
        log.info(f"Thumbnail set for video {video_id}")
    except HttpError as e:
        raise Exception(f"Failed to set thumbnail: {e.reason}")


# ─── PLAYLISTS ──────────────────────────────────────────────────

async def get_my_playlists(telegram_id: int) -> list:
    """Fetch all playlists for the user's channel"""
    try:
        yt = await _build_youtube(telegram_id)
        resp = await asyncio.to_thread(
            lambda: yt.playlists().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=50
            ).execute()
        )
        return resp.get("items", [])
    except HttpError as e:
        raise Exception(f"Failed to fetch playlists: {e.reason}")


async def add_to_playlist(telegram_id: int, video_id: str, playlist_id: str):
    """Add video to playlist"""
    try:
        yt = await _build_youtube(telegram_id)
        await asyncio.to_thread(
            lambda: yt.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
        )
        log.info(f"Added video {video_id} to playlist {playlist_id}")
    except HttpError as e:
        raise Exception(f"Failed to add to playlist: {e.reason}")


async def create_playlist(telegram_id: int, title: str, description: str = "", privacy: str = "public") -> dict:
    """Create a new playlist"""
    try:
        yt = await _build_youtube(telegram_id)
        resp = await asyncio.to_thread(
            lambda: yt.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": title, "description": description},
                    "status": {"privacyStatus": privacy}
                }
            ).execute()
        )
        return resp
    except HttpError as e:
        raise Exception(f"Failed to create playlist: {e.reason}")


# ─── CAPTIONS ───────────────────────────────────────────────────

async def upload_caption(telegram_id: int, video_id: str, srt_path: str, language: str = "en", name: str = "") -> dict:
    """Upload SRT caption file to video"""
    try:
        yt = await _build_youtube(telegram_id)
        media = MediaFileUpload(srt_path, mimetype="application/octet-stream", resumable=False)
        resp = await asyncio.to_thread(
            lambda: yt.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": language,
                        "name": name or language,
                        "isDraft": False
                    }
                },
                media_body=media
            ).execute()
        )
        return resp
    except HttpError as e:
        raise Exception(f"Failed to upload caption: {e.reason}")


async def get_captions(telegram_id: int, video_id: str) -> list:
    """Get all caption tracks for a video"""
    try:
        yt = await _build_youtube(telegram_id)
        resp = await asyncio.to_thread(
            lambda: yt.captions().list(part="snippet", videoId=video_id).execute()
        )
        return resp.get("items", [])
    except HttpError as e:
        raise Exception(f"Failed to fetch captions: {e.reason}")


async def delete_caption(telegram_id: int, caption_id: str):
    """Delete a caption track"""
    try:
        yt = await _build_youtube(telegram_id)
        await asyncio.to_thread(
            lambda: yt.captions().delete(id=caption_id).execute()
        )
    except HttpError as e:
        raise Exception(f"Failed to delete caption: {e.reason}")


# ─── STATS ──────────────────────────────────────────────────────

async def get_channel_stats(telegram_id: int) -> dict:
    """Get channel statistics"""
    try:
        yt = await _build_youtube(telegram_id)
        resp = await asyncio.to_thread(
            lambda: yt.channels().list(
                part="snippet,statistics,brandingSettings",
                mine=True
            ).execute()
        )
        items = resp.get("items", [])
        return items[0] if items else {}
    except HttpError as e:
        raise Exception(f"Failed to fetch channel stats: {e.reason}")


# ─── HELPERS ────────────────────────────────────────────────────

def format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration to readable format"""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return "0:00"
    h, m, s = [int(x or 0) for x in match.groups()]
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_count(n) -> str:
    """Format large numbers: 1234567 → 1.2M"""
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)
    except Exception:
        return "0"


CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles",
    "10": "Music", "15": "Pets & Animals",
    "17": "Sports", "19": "Travel & Events",
    "20": "Gaming", "22": "People & Blogs",
    "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style",
    "27": "Education", "28": "Science & Technology",
    "29": "Nonprofits & Activism"
}