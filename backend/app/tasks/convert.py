import os
import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Episode, EpisodeStatus
from app.services.audio_converter import convert_to_mp3
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=2)
def convert_uploaded_audio(self, episode_id: str, temp_input_path: str):
    """
    Convert uploaded audio file to MP3 in background.
    Used for large files that would timeout in the API request.
    """
    db = SessionLocal()
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            logger.error(f"Episode {episode_id} not found")
            return

        # Update status to downloading (processing)
        episode.status = EpisodeStatus.downloading
        db.commit()

        try:
            # Create output path
            os.makedirs(settings.audio_dir, exist_ok=True)
            output_path = os.path.join(settings.audio_dir, f"{episode_id}.mp3")

            # Convert to MP3
            if not convert_to_mp3(temp_input_path, output_path):
                raise Exception("Conversion failed")

            # Update episode with result
            episode.audio_path = output_path
            episode.file_size = os.path.getsize(output_path) if os.path.exists(output_path) else None
            episode.status = EpisodeStatus.ready
            episode.error_message = None
            db.commit()

            logger.info(f"Successfully converted uploaded audio for episode {episode_id}")

            # Clean up temp file
            if os.path.exists(temp_input_path):
                os.remove(temp_input_path)

        except Exception as e:
            logger.error(f"Failed to convert audio for episode {episode_id}: {e}")
            episode.status = EpisodeStatus.failed
            episode.error_message = str(e)
            db.commit()

            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()
