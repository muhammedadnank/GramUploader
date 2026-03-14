import os
import asyncio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from database.db import (
    get_youtube_token, save_youtube_token,
    get_active_api_key, increment_key_usage
)
import io

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
UPLOAD_UNITS = 1600  # approximate units per upload


async def get_credentials(telegram_id: int) -> Credentials | None:
    token_data = await get_youtube_token(telegram_id)
    if not token_data:
        return None

    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=SCOPES
    )

    # Auto refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        await save_youtube_token(telegram_id, {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "client_id": token_data.get("client_id"),
            "client_secret": token_data.get("client_secret"),
        })

    return creds


async def upload_to_youtube(
    telegram_id: int,
    file_path: str,
    title: str,
    description: str = "",
    privacy: str = "public",
    progress_callback=None
) -> str | None:
    """
    Upload video to YouTube.
    Returns YouTube video ID on success, None on failure.
    """
    creds = await get_credentials(telegram_id)
    if not creds:
        raise Exception("YouTube not connected. Use /connect first.")

    # Get active API key
    api_key_doc = await get_active_api_key()
    if not api_key_doc:
        raise Exception("YouTube quota exceeded for today. Try again tomorrow.")

    try:
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title,
                "description": description or "Uploaded via Telegram Bot",
                "tags": ["telegram", "upload"],
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": privacy  # public / private / unlisted
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

        # Track quota usage
        await increment_key_usage(api_key_doc["_id"], UPLOAD_UNITS)

        return video_id

    except HttpError as e:
        if e.resp.status == 403:
            raise Exception("YouTube quota exceeded.")
        raise Exception(f"YouTube upload failed: {e}")
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
