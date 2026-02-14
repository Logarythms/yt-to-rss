#!/usr/bin/env python3
"""
One-time migration script to import episodes from a dir2cast directory.

Reads MP3 files from a source directory, extracts ID3 tags (title, artwork),
reads descriptions from matching .txt files, and uses file modification dates
as episode dates. All episodes are added to an existing feed.

Usage:
    python migrate_dir2cast.py <source_dir> <feed_name> [--dry-run]

Must be run inside the backend container:
    docker compose exec backend python migrate_dir2cast.py /path/to/files "RLM Commentaries"
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from datetime import datetime
from uuid import uuid4

# Set up Django-style imports for the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import Feed, Episode, EpisodeStatus, EpisodeSource
from app.services.audio_converter import extract_metadata, extract_embedded_artwork
from app.services.thumbnail import process_thumbnail
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg'}


def get_file_date(file_path: str) -> datetime:
    """Get the modification time of a file."""
    return datetime.utcfromtimestamp(os.path.getmtime(file_path))


def read_description(txt_path: str) -> str | None:
    """Read episode description from a .txt file."""
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None


def get_audio_duration_and_size(file_path: str) -> tuple[int | None, int]:
    """Get duration from metadata and file size."""
    metadata = extract_metadata(file_path)
    file_size = os.path.getsize(file_path)
    return metadata.duration, file_size


def migrate(source_dir: str, feed_name: str, dry_run: bool = False):
    """Migrate audio files from source_dir into the specified feed."""
    if not os.path.isdir(source_dir):
        logger.error(f"Source directory not found: {source_dir}")
        sys.exit(1)

    init_db()
    db = SessionLocal()

    try:
        # Find the feed
        feed = db.query(Feed).filter(Feed.name == feed_name).first()
        if not feed:
            logger.error(f"Feed not found: '{feed_name}'")
            available = [f.name for f in db.query(Feed).all()]
            if available:
                logger.info(f"Available feeds: {', '.join(available)}")
            sys.exit(1)

        logger.info(f"Migrating to feed: {feed.name} ({feed.id})")

        # Find audio files
        audio_files = sorted([
            f for f in os.listdir(source_dir)
            if os.path.splitext(f.lower())[1] in AUDIO_EXTENSIONS
        ])

        if not audio_files:
            logger.warning("No audio files found in source directory")
            return

        logger.info(f"Found {len(audio_files)} audio file(s)")

        # Check for existing episodes to avoid duplicates
        existing_filenames = set(
            e.original_filename for e in
            db.query(Episode.original_filename)
            .filter(Episode.feed_id == feed.id, Episode.original_filename.isnot(None))
            .all()
        )

        added = 0
        skipped = 0

        for filename in audio_files:
            source_path = os.path.join(source_dir, filename)

            if filename in existing_filenames:
                logger.info(f"  SKIP (already exists): {filename}")
                skipped += 1
                continue

            # Extract metadata
            metadata = extract_metadata(source_path)
            title = metadata.title or os.path.splitext(filename)[0]
            file_date = get_file_date(source_path)
            file_size = os.path.getsize(source_path)

            # Read description from .txt file
            txt_path = os.path.join(source_dir, os.path.splitext(filename)[0] + '.txt')
            description = read_description(txt_path)

            logger.info(f"  {'[DRY RUN] ' if dry_run else ''}ADD: {title}")
            logger.info(f"    Date: {file_date.strftime('%Y-%m-%d')}, Size: {file_size / (1024*1024):.1f}MB, Duration: {metadata.duration}s")
            if description:
                logger.info(f"    Description: {description[:80]}...")

            if dry_run:
                added += 1
                continue

            episode_id = str(uuid4())

            # Copy audio file
            os.makedirs(settings.audio_dir, exist_ok=True)
            dest_audio_path = os.path.join(settings.audio_dir, f"{episode_id}.mp3")
            shutil.copy2(source_path, dest_audio_path)

            # Extract embedded artwork
            thumbnail_path = None
            artwork_data = extract_embedded_artwork(source_path)
            if artwork_data:
                os.makedirs(settings.thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(settings.thumbnail_dir, f"{episode_id}.jpg")
                if not process_thumbnail(artwork_data, thumbnail_path):
                    thumbnail_path = None
                else:
                    logger.info(f"    Extracted artwork")

            # Create episode
            episode = Episode(
                id=episode_id,
                feed_id=feed.id,
                youtube_id=None,
                title=title,
                description=description,
                thumbnail_url=None,
                audio_path=dest_audio_path,
                file_size=file_size,
                duration=metadata.duration,
                published_at=file_date,
                original_published_at=file_date,
                original_title=title,
                original_description=description,
                status=EpisodeStatus.ready,
                source_type=EpisodeSource.upload,
                original_filename=filename,
                thumbnail_path=thumbnail_path,
            )

            db.add(episode)
            added += 1

        if not dry_run:
            db.commit()

        logger.info(f"\nDone! Added: {added}, Skipped: {skipped}")

    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python migrate_dir2cast.py <source_dir> <feed_name> [--dry-run]")
        print('Example: python migrate_dir2cast.py /data/RedLetterMedia "RLM Commentaries"')
        sys.exit(1)

    source_dir = sys.argv[1]
    feed_name = sys.argv[2]
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        logger.info("=== DRY RUN MODE (no changes will be made) ===\n")

    migrate(source_dir, feed_name, dry_run)
