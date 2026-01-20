import os
import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Episode, EpisodeStatus
from app.services.youtube import get_video_info
from app.services.audio import download_audio

logger = logging.getLogger(__name__)


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
            episode.title = info.title
            episode.description = info.description
            episode.thumbnail_url = info.thumbnail_url
            episode.duration = info.duration
            episode.published_at = info.published_at
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
            logger.error(f"Failed to download episode {episode_id}: {e}")
            episode.status = EpisodeStatus.failed
            episode.error_message = str(e)
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
