import os
from datetime import timezone
from feedgen.feed import FeedGenerator
from sqlalchemy.orm import Session
from app.models import Feed, Episode, EpisodeStatus
from app.config import get_settings
from app.services.audio import get_audio_file_size

settings = get_settings()


def make_timezone_aware(dt):
    """Convert naive datetime to UTC timezone-aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def generate_rss_feed(feed: Feed, db: Session) -> str:
    """Generate RSS XML for a podcast feed."""
    fg = FeedGenerator()
    fg.load_extension('podcast')

    base_url = settings.base_url.rstrip('/')

    # Basic feed info
    fg.title(feed.name)
    fg.link(href=f"{base_url}/rss/{feed.id}", rel='self')
    fg.description(feed.description or feed.name)
    fg.language('en')

    # Podcast-specific info
    author = feed.author or 'yt-to-rss'
    fg.podcast.itunes_author(author)
    fg.podcast.itunes_summary(feed.description or feed.name)
    fg.podcast.itunes_explicit('no')

    # Feed artwork
    if feed.artwork_path:
        artwork_url = f"{base_url}/artwork/{feed.id}"
        fg.image(artwork_url)
        fg.podcast.itunes_image(artwork_url)

    # Add episodes (only ready ones)
    episodes = (
        db.query(Episode)
        .filter(Episode.feed_id == feed.id, Episode.status == EpisodeStatus.ready)
        .order_by(Episode.published_at.desc())
        .all()
    )

    for episode in episodes:
        fe = fg.add_entry()
        fe.id(episode.id)
        fe.title(episode.title)
        fe.description(episode.description or '')

        if episode.published_at:
            fe.pubDate(make_timezone_aware(episode.published_at))

        # Audio enclosure
        audio_url = f"{base_url}/audio/{episode.id}.mp3"
        # Use file_size from episode record, fallback to filesystem check for YouTube episodes
        file_size = episode.file_size
        if file_size is None and episode.youtube_id:
            file_size = get_audio_file_size(episode.youtube_id)
        fe.enclosure(audio_url, str(file_size or 0), 'audio/mpeg')

        # Podcast extensions
        if episode.duration:
            # Convert seconds to HH:MM:SS
            hours, remainder = divmod(episode.duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            fe.podcast.itunes_duration(duration_str)

        # Episode artwork - prefer local thumbnail, fallback to YouTube proxy
        if episode.thumbnail_path:
            thumbnail_url = f"{base_url}/episode-thumbnail/{episode.id}.jpg"
            fe.podcast.itunes_image(thumbnail_url)
        elif episode.thumbnail_url:
            thumbnail_url = f"{base_url}/thumbnail/{episode.id}.jpg"
            fe.podcast.itunes_image(thumbnail_url)

        # Link to original YouTube video (only for YouTube episodes)
        if episode.youtube_id:
            fe.link(href=f"https://www.youtube.com/watch?v={episode.youtube_id}")

    return fg.rss_str(pretty=True).decode('utf-8')
