from datetime import datetime
from typing import Optional
from pydantic import BaseModel
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
    status: EpisodeStatus
    error_message: Optional[str]
    created_at: datetime
    source_type: EpisodeSource = EpisodeSource.youtube
    original_filename: Optional[str] = None
    thumbnail_path: Optional[str] = None

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class AddVideosRequest(BaseModel):
    urls: list[str]


class AddVideosResponse(BaseModel):
    added_count: int
    episodes: list[EpisodeResponse]


class EpisodeUpdate(BaseModel):
    published_at: Optional[datetime] = None  # None = revert to original


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
