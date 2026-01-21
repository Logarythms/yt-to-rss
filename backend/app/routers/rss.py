import os
import httpx
import logging
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Feed, Episode, EpisodeStatus
from app.services.rss_generator import generate_rss_feed
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rss"])
settings = get_settings()
http_client = httpx.AsyncClient(timeout=30.0)

# Allowed domains for thumbnail proxy (SSRF prevention)
ALLOWED_THUMBNAIL_DOMAINS = {'i.ytimg.com', 'i9.ytimg.com', 'img.youtube.com'}


def validate_file_path(file_path: str, allowed_dir: str) -> bool:
    """
    Validate that a file path is within the allowed directory.
    Prevents path traversal attacks by resolving symlinks and checking containment.
    """
    try:
        # Resolve to absolute path (handles symlinks, .., etc.)
        real_path = os.path.realpath(file_path)
        real_allowed_dir = os.path.realpath(allowed_dir)

        # Check that the file is within the allowed directory
        return real_path.startswith(real_allowed_dir + os.sep) or real_path == real_allowed_dir
    except (TypeError, ValueError):
        return False


def validate_thumbnail_url(url: str) -> bool:
    """
    Validate that a thumbnail URL is from an allowed domain.
    Prevents SSRF by only allowing YouTube image domains.
    """
    try:
        parsed = urlparse(url)
        return parsed.hostname in ALLOWED_THUMBNAIL_DOMAINS and parsed.scheme == 'https'
    except Exception:
        return False


@router.get("/rss/{feed_id}")
async def get_rss_feed(
    feed_id: str,
    db: Session = Depends(get_db),
):
    """Get RSS feed XML (public, no auth required)."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    rss_xml = generate_rss_feed(feed, db)

    return Response(
        content=rss_xml,
        media_type="application/xml",
        headers={
            "Content-Type": "application/rss+xml; charset=utf-8",
        }
    )


@router.get("/audio/{episode_id}.mp3")
async def get_audio(
    episode_id: str,
    db: Session = Depends(get_db),
):
    """Get audio file (public, no auth required)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.status != EpisodeStatus.ready or not episode.audio_path:
        raise HTTPException(status_code=404, detail="Audio not ready")

    # Path traversal prevention
    if not validate_file_path(episode.audio_path, settings.audio_dir):
        logger.warning(f"Path traversal attempt blocked for audio: {episode.audio_path}")
        raise HTTPException(status_code=404, detail="Audio file not found")

    if not os.path.exists(episode.audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Use youtube_id for filename if available, otherwise use episode_id
    filename = f"{episode.youtube_id}.mp3" if episode.youtube_id else f"{episode.id}.mp3"

    return FileResponse(
        episode.audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )


@router.get("/artwork/{feed_id}")
async def get_artwork(
    feed_id: str,
    db: Session = Depends(get_db),
):
    """Get feed artwork (public, no auth required)."""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if not feed.artwork_path:
        raise HTTPException(status_code=404, detail="Artwork not found")

    # Path traversal prevention
    if not validate_file_path(feed.artwork_path, settings.artwork_dir):
        logger.warning(f"Path traversal attempt blocked for artwork: {feed.artwork_path}")
        raise HTTPException(status_code=404, detail="Artwork not found")

    if not os.path.exists(feed.artwork_path):
        raise HTTPException(status_code=404, detail="Artwork not found")

    # Determine media type from extension
    ext = os.path.splitext(feed.artwork_path)[1].lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    media_type = media_types.get(ext, 'image/jpeg')

    return FileResponse(
        feed.artwork_path,
        media_type=media_type,
    )


@router.get("/thumbnail/{episode_id}.jpg")
async def get_thumbnail(
    episode_id: str,
    db: Session = Depends(get_db),
):
    """Proxy YouTube thumbnail with proper .jpg extension (public, no auth required)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Prefer locally cached thumbnail if available
    if episode.thumbnail_path and os.path.exists(episode.thumbnail_path):
        if validate_file_path(episode.thumbnail_path, settings.thumbnail_dir):
            return FileResponse(
                episode.thumbnail_path,
                media_type="image/jpeg",
            )

    if not episode.thumbnail_url:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    # SSRF prevention: validate URL domain before fetching
    if not validate_thumbnail_url(episode.thumbnail_url):
        logger.warning(f"SSRF attempt blocked for thumbnail URL: {episode.thumbnail_url}")
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    # Fetch the thumbnail from YouTube
    try:
        response = await http_client.get(episode.thumbnail_url)
        response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to fetch thumbnail")

    return Response(
        content=response.content,
        media_type="image/jpeg",
    )


@router.get("/episode-thumbnail/{episode_id}.jpg")
async def get_episode_thumbnail(
    episode_id: str,
    db: Session = Depends(get_db),
):
    """Get locally stored episode thumbnail (public, no auth required)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if not episode.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # Path traversal prevention
    if not validate_file_path(episode.thumbnail_path, settings.thumbnail_dir):
        logger.warning(f"Path traversal attempt blocked for thumbnail: {episode.thumbnail_path}")
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    if not os.path.exists(episode.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(
        episode.thumbnail_path,
        media_type="image/jpeg",
    )
