import os
import logging
import httpx
from urllib.parse import urlparse
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Episode, EpisodeStatus
from app.services.youtube import get_video_info
from app.services.audio import download_audio
from app.services.thumbnail import process_thumbnail
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Allowed domains for thumbnail downloads (SSRF prevention)
ALLOWED_THUMBNAIL_DOMAINS = {'i.ytimg.com', 'i9.ytimg.com', 'img.youtube.com'}


def download_and_cache_thumbnail(episode_id: str, thumbnail_url: str) -> str | None:
    """
    Download thumbnail from YouTube and cache locally.
    Returns the local path on success, None on failure.
    """
    if not thumbnail_url:
        return None

    # Validate URL domain (SSRF prevention)
    try:
        parsed = urlparse(thumbnail_url)
        if parsed.hostname not in ALLOWED_THUMBNAIL_DOMAINS or parsed.scheme != 'https':
            logger.warning(f"Blocked thumbnail download from untrusted domain: {thumbnail_url}")
            return None
    except Exception:
        return None

    try:
        os.makedirs(settings.thumbnail_dir, exist_ok=True)
        output_path = os.path.join(settings.thumbnail_dir, f"{episode_id}.jpg")

        # Download thumbnail
        with httpx.Client(timeout=30.0) as client:
            response = client.get(thumbnail_url)
            response.raise_for_status()

        # Process and save thumbnail
        if process_thumbnail(response.content, output_path):
            logger.info(f"Cached thumbnail for episode {episode_id}")
            return output_path
        else:
            logger.warning(f"Failed to process thumbnail for episode {episode_id}")
            return None

    except Exception as e:
        logger.error(f"Failed to download thumbnail for episode {episode_id}: {e}")
        return None


@celery_app.task(bind=True, max_retries=3)
def download_episode(self, episode_id: str):
    """
    Download audio for an episode.
    Updates episode metadata and status.
    """
    db = SessionLocal()
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            logger.error(f"Episode {episode_id} not found")
            return

        # Update status to downloading
        episode.status = EpisodeStatus.downloading
        db.commit()

        try:
            # Get video info (in case we need to update metadata)
            info = get_video_info(episode.youtube_id)

            # Only update title if user hasn't customized it
            user_customized_title = (
                episode.original_title is not None and
                episode.title != episode.original_title
            )
            if not user_customized_title:
                episode.title = info.title
            episode.original_title = info.title

            # Only update description if user hasn't customized it
            user_customized_description = (
                episode.original_description is not None and
                episode.description != episode.original_description
            )
            if not user_customized_description:
                episode.description = info.description
            episode.original_description = info.description

            episode.thumbnail_url = info.thumbnail_url
            episode.duration = info.duration
            # Only update published_at if user hasn't customized it
            # (i.e., if it matches original_published_at or original is NULL)
            user_customized_date = (
                episode.original_published_at is not None and
                episode.published_at != episode.original_published_at
            )
            if not user_customized_date:
                episode.published_at = info.published_at
            episode.original_published_at = info.published_at
            db.commit()

            # Cache thumbnail locally (SSRF protection - validates domain)
            if info.thumbnail_url:
                thumbnail_path = download_and_cache_thumbnail(episode_id, info.thumbnail_url)
                if thumbnail_path:
                    episode.thumbnail_path = thumbnail_path
                    db.commit()

            # Download audio
            audio_path = download_audio(episode.youtube_id)
            episode.audio_path = audio_path
            episode.file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else None
            episode.status = EpisodeStatus.ready
            episode.error_message = None
            db.commit()

            logger.info(f"Successfully downloaded episode {episode_id}")

        except Exception as e:
            # Log full error for debugging, store sanitized message for users
            logger.error(f"Failed to download episode {episode_id}. Full error: {e}")
            episode.status = EpisodeStatus.failed
            episode.error_message = "Download failed. Check server logs for details."
            db.commit()

            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task
def retry_failed_episode(episode_id: str):
    """Retry downloading a failed episode."""
    db = SessionLocal()
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if episode and episode.status == EpisodeStatus.failed:
            episode.status = EpisodeStatus.pending
            episode.error_message = None
            db.commit()
            download_episode.delay(episode_id)
    finally:
        db.close()
