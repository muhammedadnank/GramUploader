from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class Plan(str, Enum):
    FREE = "free"
    PREMIUM = "premium"


class UploadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"


class YouTubeToken(BaseModel):
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str


class User(BaseModel):
    model_config = {"use_enum_values": True}

    id: int  # telegram_id as _id
    username: Optional[str] = None
    first_name: Optional[str] = None
    plan: Plan = Plan.FREE
    youtube_connected: bool = False
    youtube_token: Optional[YouTubeToken] = None
    is_banned: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    connected_at: Optional[datetime] = None
    uploads: dict = Field(default_factory=dict)  # {"2024-01-01": 2}
    settings: dict = Field(default_factory=dict)  # privacy, lang, auto_title

    def get_settings(self) -> dict:
        return self.settings or {}


class Upload(BaseModel):
    model_config = {"use_enum_values": True}

    telegram_id: int
    file_id: str
    title: str
    size: int
    status: UploadStatus = UploadStatus.PENDING
    progress_download: int = 0
    progress_upload: int = 0
    youtube_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APIKey(BaseModel):
    key: str
    units_used: int = 0
    active: bool = True
    reset_at: datetime = Field(default_factory=datetime.utcnow)
    added_at: datetime = Field(default_factory=datetime.utcnow)