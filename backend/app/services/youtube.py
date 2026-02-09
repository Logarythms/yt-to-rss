import re
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import yt_dlp

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    youtube_id: str
    title: str
    description: str
    thumbnail_url: str
    duration: int  # seconds
    published_at: Optional[datetime]


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_playlist_url(url: str) -> bool:
    """Check if URL is a YouTube playlist."""
    return 'playlist?list=' in url or '&list=' in url


def get_video_info(url_or_id: str) -> VideoInfo:
    """Get video metadata using yt-dlp."""
    # If it looks like just an ID, convert to URL
    if len(url_or_id) == 11 and not url_or_id.startswith('http'):
        url = f"https://www.youtube.com/watch?v={url_or_id}"
    else:
        url = url_or_id

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        published_at = None
        if info.get('upload_date'):
            try:
                published_at = datetime.strptime(info['upload_date'], '%Y%m%d')
            except ValueError:
                pass

        # Get best thumbnail
        thumbnail_url = info.get('thumbnail', '')
        if not thumbnail_url and info.get('thumbnails'):
            thumbnail_url = info['thumbnails'][-1].get('url', '')

        return VideoInfo(
            youtube_id=info['id'],
            title=info.get('title', 'Unknown Title'),
            description=info.get('description', ''),
            thumbnail_url=thumbnail_url,
            duration=info.get('duration', 0) or 0,
            published_at=published_at,
        )


def extract_playlist_id(url: str) -> Optional[str]:
    """Extract YouTube playlist ID from a URL."""
    match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None


def get_playlist_info(url: str) -> dict:
    """Get playlist metadata (title)."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': 1,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', 'Unknown Playlist'),
            'id': info.get('id', ''),
        }


def get_playlist_video_ids(url: str) -> list[str]:
    """Extract all video IDs from a playlist."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': 500,  # Limit to 500 videos
    }

    video_ids = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info.get('_type') == 'playlist':
            for entry in info.get('entries', []):
                if entry and entry.get('id'):
                    video_ids.append(entry['id'])
        elif info.get('id'):
            video_ids.append(info['id'])

    return video_ids


def extract_video_ids_from_urls(urls: list[str]) -> list[str]:
    """Extract all video IDs from a list of URLs (handles both videos and playlists)."""
    video_ids = []
    seen = set()

    for url in urls:
        url = url.strip()
        if not url:
            continue

        try:
            if is_playlist_url(url):
                ids = get_playlist_video_ids(url)
                for vid in ids:
                    if vid not in seen:
                        seen.add(vid)
                        video_ids.append(vid)
            else:
                vid = extract_video_id(url)
                if vid and vid not in seen:
                    seen.add(vid)
                    video_ids.append(vid)
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            continue

    return video_ids


@dataclass
class ExtractedUrls:
    video_ids: list[str]
    playlist_urls: list[tuple[str, str]]  # (url, playlist_id) pairs


def extract_video_ids_and_playlists(urls: list[str]) -> ExtractedUrls:
    """Extract video IDs and detect playlist URLs for tracking.

    Returns both the expanded video IDs and the original playlist URLs.
    """
    video_ids = []
    playlist_urls = []
    seen = set()

    for url in urls:
        url = url.strip()
        if not url:
            continue

        try:
            if is_playlist_url(url):
                playlist_id = extract_playlist_id(url)
                if playlist_id:
                    playlist_urls.append((url, playlist_id))
                ids = get_playlist_video_ids(url)
                for vid in ids:
                    if vid not in seen:
                        seen.add(vid)
                        video_ids.append(vid)
            else:
                vid = extract_video_id(url)
                if vid and vid not in seen:
                    seen.add(vid)
                    video_ids.append(vid)
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            continue

    return ExtractedUrls(video_ids=video_ids, playlist_urls=playlist_urls)
