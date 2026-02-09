from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models import EpisodeStatus, EpisodeSource


# Auth schemas
class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Feed schemas
class FeedCreate(BaseModel):
    name: str
    description: Optional[str] = None


class FeedUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class FeedResponse(BaseModel):
    id: str
    name: str
    author: Optional[str]
    description: Optional[str]
    artwork_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    episode_count: int = 0
    total_size: int = 0  # bytes
    rss_url: str = ""

    model_config = {"from_attributes": True}


class FeedListResponse(BaseModel):
    feeds: list[FeedResponse]


# Episode schemas
class EpisodeResponse(BaseModel):
    id: str
    feed_id: str
    youtube_id: Optional[str]  # Nullable for uploaded episodes
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    audio_path: Optional[str]
    file_size: Optional[int]  # bytes
    duration: Optional[int]
    published_at: Optional[datetime]
    original_published_at: Optional[datetime]
    original_title: Optional[str] = None
    original_description: Optional[str] = None
    status: EpisodeStatus
    error_message: Optional[str]
    created_at: datetime
    source_type: EpisodeSource = EpisodeSource.youtube
    original_filename: Optional[str] = None
    thumbnail_path: Optional[str] = None

    model_config = {"from_attributes": True}


class PlaylistSourceResponse(BaseModel):
    id: str
    feed_id: str
    playlist_url: str
    playlist_id: str
    name: Optional[str]
    last_refreshed_at: Optional[datetime]
    refresh_interval_override: Optional[int]
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v):
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)


class PlaylistSourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    refresh_interval_override: Optional[int] = None


class RefreshResponse(BaseModel):
    refreshed_playlists: int
    new_episodes_added: int


class FeedDetailResponse(BaseModel):
    id: str
    name: str
    author: Optional[str]
    description: Optional[str]
    artwork_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    rss_url: str
    total_size: int = 0  # bytes
    episodes: list[EpisodeResponse]
    playlist_sources: list[PlaylistSourceResponse] = []

    model_config = {"from_attributes": True}


class AddVideosRequest(BaseModel):
    urls: list[str]


class AddVideosResponse(BaseModel):
    added_count: int
    episodes: list[EpisodeResponse]
    playlist_sources_created: int = 0


class EpisodeUpdate(BaseModel):
    # All fields use None = no change when not provided in request
    # published_at: explicit null in JSON = revert to original
    # title/description: empty string = revert to original
    published_at: Optional[datetime] = None  # omit = no change, null = revert
    title: Optional[str] = Field(None, max_length=500)  # None = no change, "" = revert
    description: Optional[str] = None  # None = no change, "" = revert


# Storage schemas
class FeedStorageInfo(BaseModel):
    id: str
    name: str
    episode_count: int
    total_size: int  # bytes


class StorageResponse(BaseModel):
    feeds: list[FeedStorageInfo]
    total_used: int  # bytes
    total_free: int  # bytes
    total_capacity: int  # bytes
