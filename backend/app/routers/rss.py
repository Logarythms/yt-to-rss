import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Feed, Episode, EpisodeStatus
from app.services.rss_generator import generate_rss_feed
from app.config import get_settings

router = APIRouter(tags=["rss"])
settings = get_settings()
http_client = httpx.AsyncClient(timeout=30.0)


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

    if not feed.artwork_path or not os.path.exists(feed.artwork_path):
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

    if not episode.thumbnail_url:
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

    if not episode.thumbnail_path or not os.path.exists(episode.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(
        episode.thumbnail_path,
        media_type="image/jpeg",
    )
