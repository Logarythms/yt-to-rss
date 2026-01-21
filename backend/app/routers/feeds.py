import os
import shutil
import tempfile
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import Feed, Episode, EpisodeStatus, EpisodeSource
from sqlalchemy import func
from app.schemas import (
    FeedCreate, FeedUpdate, FeedResponse, FeedListResponse,
    FeedDetailResponse, EpisodeResponse, EpisodeUpdate, AddVideosRequest, AddVideosResponse,
    StorageResponse, FeedStorageInfo
)
from app.auth import get_current_user
from app.config import get_settings
from app.services.youtube import extract_video_ids_from_urls, get_video_info
from app.services.audio_converter import (
    validate_audio_file, extract_metadata, convert_to_mp3, is_mp3, verify_audio_file,
    MAX_FILE_SIZE, LARGE_FILE_THRESHOLD
)
from app.services.thumbnail import process_thumbnail, validate_thumbnail, delete_thumbnail
from app.services.artwork import validate_artwork_extension, validate_and_process_artwork
from app.tasks.download import download_episode
from app.tasks.convert import convert_uploaded_audio

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

    # Handle artwork upload with validation
    if artwork and artwork.filename:
        # Validate extension
        is_valid, error_msg = validate_artwork_extension(artwork.filename)
        if not is_valid:
            db.rollback()
            raise HTTPException(status_code=400, detail=error_msg)

        # Read artwork data
        artwork_data = await artwork.read()

        os.makedirs(settings.artwork_dir, exist_ok=True)
        artwork_path = os.path.join(settings.artwork_dir, f"{feed.id}.jpg")

        # Validate and process artwork (converts to JPEG)
        success, error_msg = validate_and_process_artwork(artwork_data, artwork_path)
        if not success:
            db.rollback()
            raise HTTPException(status_code=400, detail=error_msg)

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

    # Handle artwork upload with validation
    if artwork and artwork.filename:
        # Validate extension
        is_valid, error_msg = validate_artwork_extension(artwork.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Read artwork data
        artwork_data = await artwork.read()

        os.makedirs(settings.artwork_dir, exist_ok=True)
        artwork_path = os.path.join(settings.artwork_dir, f"{feed.id}.jpg")

        # Validate and process artwork (converts to JPEG)
        success, error_msg = validate_and_process_artwork(artwork_data, artwork_path)
        if not success:
            raise HTTPException(status_code=400, detail=error_msg)

        # Remove old artwork if exists and different path
        if feed.artwork_path and feed.artwork_path != artwork_path:
            if os.path.exists(feed.artwork_path):
                os.remove(feed.artwork_path)

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

    # Delete episode files (audio and thumbnails)
    episodes = db.query(Episode).filter(Episode.feed_id == feed_id).all()
    for episode in episodes:
        if episode.audio_path and os.path.exists(episode.audio_path):
            os.remove(episode.audio_path)
        if episode.thumbnail_path and os.path.exists(episode.thumbnail_path):
            os.remove(episode.thumbnail_path)

    # Delete feed artwork
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


@router.post("/{feed_id}/upload-audio", response_model=EpisodeResponse)
async def upload_audio(
    feed_id: str,
    audio: UploadFile = File(...),
    thumbnail: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Upload an audio file as a new episode."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Security: sanitize filename to prevent path traversal
    safe_filename = os.path.basename(audio.filename) if audio.filename else "upload.mp3"

    # Validate file extension and get file size via chunked read
    temp_dir = tempfile.mkdtemp()
    temp_input_path = os.path.join(temp_dir, safe_filename)

    try:
        # Chunked file write to avoid loading entire file in memory
        file_size = 0
        with open(temp_input_path, 'wb') as f:
            while chunk := await audio.read(8192):  # 8KB chunks
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                f.write(chunk)

        # Validate audio file extension
        is_valid, error_msg = validate_audio_file(safe_filename, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Security: verify file is actually audio using ffprobe (magic byte validation)
        is_audio, verify_error = verify_audio_file(temp_input_path)
        if not is_audio:
            raise HTTPException(status_code=400, detail=verify_error or "Invalid audio file")

        # Extract metadata
        metadata = extract_metadata(temp_input_path)

        # Generate episode ID
        episode_id = str(uuid4())

        # Determine title (priority: form input > metadata > filename)
        episode_title = title
        if not episode_title and metadata.title:
            episode_title = metadata.title
        if not episode_title:
            episode_title = os.path.splitext(safe_filename)[0]

        # Process thumbnail if provided (before potentially going async)
        thumbnail_path = None
        if thumbnail and thumbnail.filename:
            is_valid, error_msg = validate_thumbnail(thumbnail.filename)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

            os.makedirs(settings.thumbnail_dir, exist_ok=True)
            thumbnail_path = os.path.join(settings.thumbnail_dir, f"{episode_id}.jpg")
            thumbnail_content = await thumbnail.read()

            if not process_thumbnail(thumbnail_content, thumbnail_path):
                thumbnail_path = None  # Failed, but continue without thumbnail

        # For large files (>100MB), use Celery for background processing
        if file_size > LARGE_FILE_THRESHOLD:
            # Move temp file to persistent location for Celery task
            os.makedirs(settings.data_dir, exist_ok=True)
            persistent_temp_path = os.path.join(settings.data_dir, "temp", f"{episode_id}_upload")
            os.makedirs(os.path.dirname(persistent_temp_path), exist_ok=True)
            shutil.move(temp_input_path, persistent_temp_path)

            # Create episode with pending status
            now = datetime.utcnow()
            episode = Episode(
                id=episode_id,
                feed_id=feed_id,
                youtube_id=None,
                title=episode_title,
                description=description,
                thumbnail_url=None,
                audio_path=None,  # Will be set by Celery task
                file_size=None,  # Will be set by Celery task
                duration=metadata.duration,
                published_at=now,
                original_published_at=now,
                original_title=episode_title,
                original_description=description,
                status=EpisodeStatus.pending,
                source_type=EpisodeSource.upload,
                original_filename=safe_filename,
                thumbnail_path=thumbnail_path,
            )

            try:
                db.add(episode)
                db.commit()
                db.refresh(episode)
            except Exception as e:
                # Clean up files if DB commit fails
                if os.path.exists(persistent_temp_path):
                    os.remove(persistent_temp_path)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                raise

            # Queue Celery task after commit
            convert_uploaded_audio.delay(episode.id, persistent_temp_path)

            return EpisodeResponse.model_validate(episode)

        # For smaller files, process synchronously
        os.makedirs(settings.audio_dir, exist_ok=True)
        output_path = os.path.join(settings.audio_dir, f"{episode_id}.mp3")

        # Convert to MP3 (or copy if already MP3)
        if not convert_to_mp3(temp_input_path, output_path):
            # Clean up thumbnail if conversion failed
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            raise HTTPException(status_code=500, detail="Failed to process audio file")

        # Get actual output file size
        output_file_size = os.path.getsize(output_path)

        # Create episode
        now = datetime.utcnow()
        episode = Episode(
            id=episode_id,
            feed_id=feed_id,
            youtube_id=None,
            title=episode_title,
            description=description,
            thumbnail_url=None,
            audio_path=output_path,
            file_size=output_file_size,
            duration=metadata.duration,
            published_at=now,
            original_published_at=now,
            original_title=episode_title,
            original_description=description,
            status=EpisodeStatus.ready,
            source_type=EpisodeSource.upload,
            original_filename=safe_filename,
            thumbnail_path=thumbnail_path,
        )

        try:
            db.add(episode)
            db.commit()
            db.refresh(episode)
        except Exception as e:
            # Clean up orphaned files if DB commit fails
            if os.path.exists(output_path):
                os.remove(output_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            raise

        return EpisodeResponse.model_validate(episode)

    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


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

    # Delete thumbnail file (for uploaded episodes)
    if episode.thumbnail_path and os.path.exists(episode.thumbnail_path):
        os.remove(episode.thumbnail_path)

    db.delete(episode)
    db.commit()

    return {"deleted": True}


@router.patch("/{feed_id}/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    feed_id: str,
    episode_id: str,
    request: EpisodeUpdate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """Update episode metadata."""
    episode = db.query(Episode).filter(
        Episode.id == episode_id, Episode.feed_id == feed_id
    ).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if request.published_at is None:
        # Revert to original date
        episode.published_at = episode.original_published_at or episode.created_at
    else:
        # Validate date range: reject dates before 2005 (YouTube launch) or more than 1 year in future
        min_date = datetime(2005, 1, 1)
        max_date = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
        if request.published_at < min_date:
            raise HTTPException(status_code=400, detail="Date cannot be before 2005")
        if request.published_at > max_date:
            raise HTTPException(status_code=400, detail="Date cannot be more than 1 year in the future")
        episode.published_at = request.published_at

    # Handle title update (None = no change, empty string = revert to original)
    if request.title is not None:
        episode.title = request.title if request.title else (episode.original_title or episode.title)

    # Handle description update (None = no change, empty string = revert to original)
    if request.description is not None:
        episode.description = request.description if request.description else (episode.original_description or episode.description)

    db.commit()
    db.refresh(episode)
    return EpisodeResponse.model_validate(episode)


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
