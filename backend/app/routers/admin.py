import os
import logging
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Feed, Episode
from app.auth import get_current_user
from app.services.image_utils import letterbox_to_square

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

OUTPUT_QUALITY = 90


class MigrateImagesRequest(BaseModel):
    dry_run: bool = False


class MigrateImagesResponse(BaseModel):
    total_images: int
    processed: int
    skipped: int
    failed: int
    errors: list[str]


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
    Process all existing images to make them square with black letterboxing.
    Use dry_run=true to preview changes without modifying files.
    """
    total_images = 0
    processed = 0
    skipped = 0
    failed = 0
    errors = []

    # Process feed artwork
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

    # Process episode thumbnails
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
        total_images=total_images,
        processed=processed,
        skipped=skipped,
        failed=failed,
        errors=errors[:50]  # Limit error messages
    )
