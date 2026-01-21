import os
import logging
from PIL import Image
from io import BytesIO

from app.services.image_utils import letterbox_to_square

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_DIMENSION = 1400  # iTunes recommended podcast artwork size
THUMBNAIL_QUALITY = 85
MAX_THUMBNAIL_SIZE = 10 * 1024 * 1024  # 10MB max thumbnail size


def validate_thumbnail(filename: str) -> tuple[bool, str]:
    """
    Validate thumbnail file by extension.
    Returns (is_valid, error_message).
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid image format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    return True, ""


def process_thumbnail(
    input_data: bytes,
    output_path: str,
    max_dimension: int = MAX_DIMENSION
) -> bool:
    """
    Process and save thumbnail image.
    - Resizes if larger than max_dimension
    - Converts to JPEG
    - Saves to output_path

    Returns True on success, False on failure.
    """
    try:
        # Check file size limit
        if len(input_data) > MAX_THUMBNAIL_SIZE:
            logger.warning(f"Thumbnail too large: {len(input_data)} bytes (max {MAX_THUMBNAIL_SIZE})")
            return False

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Open image
        img = Image.open(BytesIO(input_data))

        # Convert to RGB (required for JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            # Create white background for transparent images
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize if needed (maintain aspect ratio)
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            logger.info(f"Resized thumbnail to {img.width}x{img.height}")

        # Letterbox to square aspect ratio
        img = letterbox_to_square(img)

        # Save as JPEG
        img.save(output_path, 'JPEG', quality=THUMBNAIL_QUALITY, optimize=True)
        logger.info(f"Saved thumbnail: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to process thumbnail: {e}")
        return False


def delete_thumbnail(thumbnail_path: str) -> bool:
    """
    Delete a thumbnail file.
    Returns True on success or if file doesn't exist.
    """
    try:
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            logger.info(f"Deleted thumbnail: {thumbnail_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete thumbnail: {e}")
        return False
