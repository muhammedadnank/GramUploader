import os
import asyncio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from database.db import user_repo, apikey_repo
from database.models import YouTubeToken
from utils.logger import log

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
UPLOAD_UNITS = 1600  # approximate quota units per upload


async def get_credentials(telegram_id: int) -> Credentials | None:
    """Get valid Google OAuth2 credentials for a user, auto-refreshing if expired."""
    token: YouTubeToken = await user_repo.get_youtube_token(telegram_id)
    if not token:
        return None

    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token.client_id,
        client_secret=token.client_secret,
        scopes=SCOPES
    )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, Request())
        # Save refreshed token back to DB
        await user_repo.set_youtube_token(telegram_id, YouTubeToken(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            client_id=token.client_id,
            client_secret=token.client_secret,
        ))
        log.info(f"Token refreshed for user {telegram_id}")

    return creds


async def upload_to_youtube(
    telegram_id: int,
    file_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    privacy: str = "public",
    category_id: str = "22",
    progress_callback=None
) -> str:
    """
    Upload a video file to YouTube.
    Returns YouTube video ID on success.
    Raises Exception on failure.
    """
    creds = await get_credentials(telegram_id)
    if not creds:
        raise Exception("YouTube not connected. Use /connect first.")

    # Get active API key
    api_key_doc = await apikey_repo.get_active()
    if not api_key_doc:
        raise Exception("No active YouTube API key. Ask admin to add one via /addkey.")

    try:
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description or "Uploaded via GramUploader",
                "tags": tags if tags is not None else ["telegram", "gramuploader"],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            }
        }

        media = MediaFileUpload(
            file_path,
            chunksize=5 * 1024 * 1024,  # 5MB chunks
            resumable=True
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        # Resumable upload with progress
        response = None
        while response is None:
            status, response = await asyncio.to_thread(request.next_chunk)
            if status and progress_callback:
                progress = int(status.progress() * 100)
                await progress_callback(progress)

        video_id = response.get("id")
        if not video_id:
            raise Exception("Upload succeeded but no video ID returned.")

        # Track quota usage
        await apikey_repo.increment_usage(api_key_doc["_id"], UPLOAD_UNITS)
        log.info(f"Upload complete: {video_id} for user {telegram_id}")

        return video_id

    except HttpError as e:
        if e.resp.status == 403:
            raise Exception("YouTube quota exceeded. Try again tomorrow or ask admin to add a new API key.")
        raise Exception(f"YouTube upload failed: {e.reason}")
    finally:
        # Always cleanup temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_err:
            log.warning(f"Could not delete temp file {file_path}: {cleanup_err}")