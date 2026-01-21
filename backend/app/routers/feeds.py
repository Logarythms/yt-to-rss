import os
import shutil
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Feed, Episode, EpisodeStatus
from sqlalchemy import func
from app.schemas import (
    FeedCreate, FeedUpdate, FeedResponse, FeedListResponse,
    FeedDetailResponse, EpisodeResponse, AddVideosRequest, AddVideosResponse,
    StorageResponse, FeedStorageInfo
)
from app.auth import get_current_user
from app.config import get_settings
from app.services.youtube import extract_video_ids_from_urls, get_video_info
from app.tasks.download import download_episode

router = APIRouter(prefix="/api/feeds", tags=["feeds"])
settings = get_settings()


def feed_to_response(feed: Feed, db: Session) -> FeedResponse:
    """Convert Feed model to response schema."""
    episode_count = db.query(Episode).filter(Episode.feed_id == feed.id).count()
    total_size = db.query(func.coalesce(func.sum(Episode.file_size), 0)).filter(
        Episode.feed_id == feed.id
    ).scalar() or 0
    base_url = settings.base_url.rstrip('/')
    return FeedResponse(
        id=feed.id,
        name=feed.name,
        author=feed.author,
        description=feed.description,
        artwork_path=feed.artwork_path,
        created_at=feed.created_at,
        updated_at=feed.updated_at,
        episode_count=episode_count,
        total_size=total_size,
        rss_url=f"{base_url}/rss/{feed.id}",
    )


@router.get("", response_model=FeedListResponse)
async def list_feeds(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """List all feeds."""
    feeds = db.query(Feed).order_by(Feed.created_at.desc()).all()
    return FeedListResponse(
        feeds=[feed_to_response(f, db) for f in feeds]
    )


@router.post("", response_model=FeedResponse)
async def create_feed(
    name: str = Form(...),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    artwork: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Create a new feed."""
    feed = Feed(name=name, author=author, description=description)
    db.add(feed)
    db.flush()  # Get the ID

    # Handle artwork upload
    if artwork and artwork.filename:
        os.makedirs(settings.artwork_dir, exist_ok=True)
        ext = os.path.splitext(artwork.filename)[1] or '.jpg'
        artwork_path = os.path.join(settings.artwork_dir, f"{feed.id}{ext}")

        with open(artwork_path, "wb") as f:
            shutil.copyfileobj(artwork.file, f)

        feed.artwork_path = artwork_path

    db.commit()
    db.refresh(feed)

    return feed_to_response(feed, db)


@router.get("/{feed_id}", response_model=FeedDetailResponse)
async def get_feed(
    feed_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Get feed details with episodes."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    episodes = (
        db.query(Episode)
        .filter(Episode.feed_id == feed_id)
        .order_by(Episode.created_at.desc())
        .all()
    )

    base_url = settings.base_url.rstrip('/')
    total_size = db.query(func.coalesce(func.sum(Episode.file_size), 0)).filter(
        Episode.feed_id == feed_id
    ).scalar() or 0
    return FeedDetailResponse(
        id=feed.id,
        name=feed.name,
        author=feed.author,
        description=feed.description,
        artwork_path=feed.artwork_path,
        created_at=feed.created_at,
        updated_at=feed.updated_at,
        rss_url=f"{base_url}/rss/{feed.id}",
        total_size=total_size,
        episodes=[EpisodeResponse.model_validate(e) for e in episodes],
    )


@router.put("/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: str,
    name: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    artwork: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Update feed metadata."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if name is not None:
        feed.name = name
    if author is not None:
        feed.author = author
    if description is not None:
        feed.description = description

    # Handle artwork upload
    if artwork and artwork.filename:
        os.makedirs(settings.artwork_dir, exist_ok=True)
        ext = os.path.splitext(artwork.filename)[1] or '.jpg'
        artwork_path = os.path.join(settings.artwork_dir, f"{feed.id}{ext}")

        # Remove old artwork if different extension
        if feed.artwork_path and feed.artwork_path != artwork_path:
            if os.path.exists(feed.artwork_path):
                os.remove(feed.artwork_path)

        with open(artwork_path, "wb") as f:
            shutil.copyfileobj(artwork.file, f)

        feed.artwork_path = artwork_path

    db.commit()
    db.refresh(feed)

    return feed_to_response(feed, db)


@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Delete feed and all episodes."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Delete audio files
    episodes = db.query(Episode).filter(Episode.feed_id == feed_id).all()
    for episode in episodes:
        if episode.audio_path and os.path.exists(episode.audio_path):
            os.remove(episode.audio_path)

    # Delete artwork
    if feed.artwork_path and os.path.exists(feed.artwork_path):
        os.remove(feed.artwork_path)

    db.delete(feed)
    db.commit()

    return {"deleted": True}


@router.post("/{feed_id}/add-videos", response_model=AddVideosResponse)
async def add_videos(
    feed_id: str,
    request: AddVideosRequest,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Add videos to feed by URL (supports individual videos and playlists)."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Extract video IDs from URLs
    video_ids = extract_video_ids_from_urls(request.urls)

    if not video_ids:
        raise HTTPException(status_code=400, detail="No valid video URLs found")

    # Check for existing episodes
    existing_ids = {
        e.youtube_id for e in
        db.query(Episode.youtube_id)
        .filter(Episode.feed_id == feed_id, Episode.youtube_id.in_(video_ids))
        .all()
    }

    # Create new episodes
    new_episodes = []
    for vid in video_ids:
        if vid in existing_ids:
            continue

        episode = Episode(
            feed_id=feed_id,
            youtube_id=vid,
            title=f"Loading... ({vid})",  # Will be updated by worker
            status=EpisodeStatus.pending,
        )
        db.add(episode)
        db.flush()
        new_episodes.append(episode)

    # Commit transaction BEFORE queuing tasks to avoid race condition
    # where worker queries for episode before it's visible
    db.commit()

    # Queue download tasks after commit
    for episode in new_episodes:
        download_episode.delay(episode.id)

    return AddVideosResponse(
        added_count=len(new_episodes),
        episodes=[EpisodeResponse.model_validate(e) for e in new_episodes],
    )


@router.delete("/{feed_id}/episodes/{episode_id}")
async def delete_episode(
    feed_id: str,
    episode_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Remove an episode from a feed."""
    episode = db.query(Episode).filter(
        Episode.id == episode_id,
        Episode.feed_id == feed_id,
    ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Delete audio file
    if episode.audio_path and os.path.exists(episode.audio_path):
        os.remove(episode.audio_path)

    db.delete(episode)
    db.commit()

    return {"deleted": True}


@router.post("/{feed_id}/episodes/{episode_id}/retry")
async def retry_episode(
    feed_id: str,
    episode_id: str,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Retry downloading a failed episode."""
    episode = db.query(Episode).filter(
        Episode.id == episode_id,
        Episode.feed_id == feed_id,
    ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.status != EpisodeStatus.failed:
        raise HTTPException(status_code=400, detail="Episode is not in failed state")

    episode.status = EpisodeStatus.pending
    episode.error_message = None
    db.commit()

    download_episode.delay(episode.id)

    return {"queued": True}


@router.get("/storage/info", response_model=StorageResponse)
async def get_storage_info(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Get storage usage information."""
    import shutil

    # Get per-feed storage info
    feeds = db.query(Feed).order_by(Feed.name).all()
    feed_storage = []
    for feed in feeds:
        episode_count = db.query(Episode).filter(Episode.feed_id == feed.id).count()
        total_size = db.query(func.coalesce(func.sum(Episode.file_size), 0)).filter(
            Episode.feed_id == feed.id
        ).scalar() or 0
        feed_storage.append(FeedStorageInfo(
            id=feed.id,
            name=feed.name,
            episode_count=episode_count,
            total_size=total_size,
        ))

    # Get total used space
    total_used = db.query(func.coalesce(func.sum(Episode.file_size), 0)).scalar() or 0

    # Get disk space info
    try:
        disk_usage = shutil.disk_usage(settings.data_dir)
        total_free = disk_usage.free
        total_capacity = disk_usage.total
    except OSError:
        total_free = 0
        total_capacity = 0

    return StorageResponse(
        feeds=feed_storage,
        total_used=total_used,
        total_free=total_free,
        total_capacity=total_capacity,
    )
