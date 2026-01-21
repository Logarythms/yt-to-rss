import os
import logging
from io import BytesIO
from urllib.parse import urlparse
import httpx
from PIL import Image
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Feed, Episode
from app.auth import get_current_user
from app.config import get_settings
from app.services.image_utils import letterbox_to_square
from app.services.thumbnail import process_thumbnail

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/admin", tags=["admin"])

OUTPUT_QUALITY = 90

# Allowed domains for thumbnail downloads (SSRF prevention)
ALLOWED_THUMBNAIL_DOMAINS = {'i.ytimg.com', 'i9.ytimg.com', 'img.youtube.com'}


class MigrateImagesRequest(BaseModel):
    dry_run: bool = False


class MigrateImagesResponse(BaseModel):
    thumbnails_downloaded: int
    thumbnails_failed: int
    total_images: int
    processed: int
    skipped: int
    failed: int
    errors: list[str]


def download_thumbnail(episode_id: str, thumbnail_url: str, dry_run: bool) -> tuple[str | None, str]:
    """
    Download thumbnail from YouTube and cache locally.
    Returns (local_path, status) where status is 'downloaded', 'would_download', or error message.
    """
    if not thumbnail_url:
        return None, "no_url"

    # Validate URL domain (SSRF prevention)
    try:
        parsed = urlparse(thumbnail_url)
        if parsed.hostname not in ALLOWED_THUMBNAIL_DOMAINS or parsed.scheme != 'https':
            logger.warning(f"Blocked thumbnail download from untrusted domain: {thumbnail_url}")
            return None, "untrusted_domain"
    except Exception:
        return None, "invalid_url"

    if dry_run:
        return None, "would_download"

    try:
        os.makedirs(settings.thumbnail_dir, exist_ok=True)
        output_path = os.path.join(settings.thumbnail_dir, f"{episode_id}.jpg")

        # Download thumbnail
        with httpx.Client(timeout=30.0) as client:
            response = client.get(thumbnail_url)
            response.raise_for_status()

        # Process and save thumbnail (includes letterboxing)
        if process_thumbnail(response.content, output_path):
            logger.info(f"Downloaded and cached thumbnail for episode {episode_id}")
            return output_path, "downloaded"
        else:
            return None, "processing_failed"

    except Exception as e:
        logger.error(f"Failed to download thumbnail for episode {episode_id}: {e}")
        return None, str(e)


def process_image_file(file_path: str, dry_run: bool) -> str:
    """
    Process an image file to make it square with letterboxing.
    Returns status: 'processed', 'skipped', 'would_process', 'file_not_found', or error message.
    """
    if not file_path or not os.path.exists(file_path):
        return "file_not_found"

    try:
        with open(file_path, 'rb') as f:
            img_data = f.read()

        img = Image.open(BytesIO(img_data))

        # Check if already square
        width, height = img.size
        if width == height:
            return "skipped"

        if dry_run:
            return "would_process"

        # Convert to RGB if needed
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (0, 0, 0))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Apply letterboxing
        img = letterbox_to_square(img)

        # Save back to original path
        img.save(file_path, 'JPEG', quality=OUTPUT_QUALITY, optimize=True)
        logger.info(f"Letterboxed image: {file_path} ({width}x{height} -> {img.size[0]}x{img.size[1]})")

        return "processed"

    except Exception as e:
        logger.error(f"Failed to process image {file_path}: {e}")
        return str(e)


@router.post("/migrate-images", response_model=MigrateImagesResponse)
async def migrate_images(
    request: MigrateImagesRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Download missing thumbnails and make all images square with black letterboxing.
    Use dry_run=true to preview changes without modifying files.
    """
    thumbnails_downloaded = 0
    thumbnails_failed = 0
    total_images = 0
    processed = 0
    skipped = 0
    failed = 0
    errors = []

    # Step 1: Download thumbnails for episodes that have thumbnail_url but no thumbnail_path
    episodes_missing_thumbnails = db.query(Episode).filter(
        Episode.thumbnail_url.isnot(None),
        Episode.thumbnail_path.is_(None)
    ).all()

    for episode in episodes_missing_thumbnails:
        path, status = download_thumbnail(str(episode.id), episode.thumbnail_url, request.dry_run)

        if status == "downloaded":
            episode.thumbnail_path = path
            db.commit()
            thumbnails_downloaded += 1
        elif status == "would_download":
            thumbnails_downloaded += 1
        elif status != "no_url":
            thumbnails_failed += 1
            errors.append(f"Episode '{episode.title}' thumbnail download: {status}")

    # Step 2: Process feed artwork
    feeds = db.query(Feed).filter(Feed.artwork_path.isnot(None)).all()
    for feed in feeds:
        total_images += 1
        status = process_image_file(feed.artwork_path, request.dry_run)

        if status == "skipped":
            skipped += 1
        elif status == "processed" or status == "would_process":
            processed += 1
        else:
            failed += 1
            errors.append(f"Feed '{feed.name}' artwork: {status}")

    # Step 3: Process episode thumbnails (now includes newly downloaded ones)
    episodes = db.query(Episode).filter(Episode.thumbnail_path.isnot(None)).all()
    for episode in episodes:
        total_images += 1
        status = process_image_file(episode.thumbnail_path, request.dry_run)

        if status == "skipped":
            skipped += 1
        elif status == "processed" or status == "would_process":
            processed += 1
        else:
            failed += 1
            errors.append(f"Episode '{episode.title}' thumbnail: {status}")

    return MigrateImagesResponse(
        thumbnails_downloaded=thumbnails_downloaded,
        thumbnails_failed=thumbnails_failed,
        total_images=total_images,
        processed=processed,
        skipped=skipped,
        failed=failed,
        errors=errors[:50]  # Limit error messages
    )
