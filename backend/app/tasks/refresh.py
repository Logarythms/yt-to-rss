import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.config import get_settings
from app.database import SessionLocal
from app.models import Episode, EpisodeStatus, Feed, PlaylistSource
from app.services.youtube import get_playlist_video_ids
from app.tasks.download import download_episode

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=2)
def refresh_playlist(self, playlist_source_id: str):
    """Refresh a single playlist source, creating episodes for new videos."""
    db = SessionLocal()
    try:
        source = db.query(PlaylistSource).filter(
            PlaylistSource.id == playlist_source_id
        ).first()
        if not source:
            logger.error(f"PlaylistSource {playlist_source_id} not found")
            return {"added": 0, "error": "Playlist source not found"}

        if source.enabled != "true":
            logger.info(f"PlaylistSource {playlist_source_id} is disabled, skipping")
            return {"added": 0, "skipped": True}

        feed = db.query(Feed).filter(Feed.id == source.feed_id).first()
        if not feed:
            logger.error(f"Feed {source.feed_id} not found for playlist source {playlist_source_id}")
            return {"added": 0, "error": "Feed not found"}

        # Get current video IDs from YouTube
        try:
            video_ids = get_playlist_video_ids(source.playlist_url)
        except Exception as e:
            logger.error(f"Failed to fetch playlist {source.playlist_url}: {e}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=300 * (2 ** self.request.retries))
            return {"added": 0, "error": str(e)}

        # Get existing youtube_ids in this feed
        existing_ids = {
            e.youtube_id for e in
            db.query(Episode.youtube_id)
            .filter(Episode.feed_id == source.feed_id, Episode.youtube_id.isnot(None))
            .all()
        }

        # Create episodes for new videos (respect limit)
        new_episodes = []
        for vid in video_ids:
            if vid in existing_ids:
                continue
            if len(new_episodes) >= settings.max_new_episodes_per_refresh:
                logger.warning(
                    f"Hit max_new_episodes_per_refresh ({settings.max_new_episodes_per_refresh}) "
                    f"for playlist {source.playlist_id}"
                )
                break

            episode = Episode(
                feed_id=source.feed_id,
                youtube_id=vid,
                title=f"Loading... ({vid})",
                status=EpisodeStatus.pending,
            )
            db.add(episode)
            db.flush()
            new_episodes.append(episode)

        # Update last_refreshed_at
        source.last_refreshed_at = datetime.utcnow()

        # Commit before queuing tasks (same pattern as add_videos endpoint)
        db.commit()

        # Queue downloads after commit
        for episode in new_episodes:
            download_episode.delay(episode.id)

        logger.info(
            f"Refreshed playlist {source.playlist_id}: "
            f"{len(new_episodes)} new episodes added"
        )
        return {"added": len(new_episodes)}

    except Exception as e:
        logger.error(f"Error refreshing playlist source {playlist_source_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task
def check_playlist_refreshes():
    """Periodic task: check all playlist sources and refresh those that are due."""
    db = SessionLocal()
    try:
        sources = db.query(PlaylistSource).filter(
            PlaylistSource.enabled == "true"
        ).all()

        refreshed = 0
        for source in sources:
            # Determine effective interval
            interval = source.refresh_interval_override or settings.playlist_refresh_interval

            # Check if refresh is due
            if source.last_refreshed_at:
                next_refresh = source.last_refreshed_at + timedelta(seconds=interval)
                if datetime.utcnow() < next_refresh:
                    continue

            # Queue refresh task
            refresh_playlist.delay(source.id)
            refreshed += 1

        logger.info(f"Queued {refreshed} playlist refreshes")
        return {"queued": refreshed}

    finally:
        db.close()
