import os
import logging
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_ARTWORK_SIZE = 10 * 1024 * 1024  # 10MB max file size
MAX_DIMENSION = 3000  # Maximum dimension in pixels
MIN_DIMENSION = 100   # Minimum dimension in pixels
OUTPUT_QUALITY = 90


def validate_artwork_extension(filename: str) -> tuple[bool, str]:
    """
    Validate artwork file extension.
    Returns (is_valid, error_message).
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid image format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    return True, ""


def validate_and_process_artwork(
    input_data: bytes,
    output_path: str,
) -> tuple[bool, str]:
    """
    Validate and process artwork image.
    - Validates it's actually an image using PIL
    - Checks dimensions are reasonable
    - Converts to JPEG for consistency
    - Saves to output_path

    Returns (success, error_message).
    """
    try:
        # Check file size limit
        if len(input_data) > MAX_ARTWORK_SIZE:
            return False, f"File too large. Maximum size: {MAX_ARTWORK_SIZE // (1024*1024)}MB"

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Validate it's actually an image by opening with PIL
        try:
            img = Image.open(BytesIO(input_data))
            img.verify()  # Verify it's a valid image
            # Re-open after verify (verify closes the image)
            img = Image.open(BytesIO(input_data))
        except Exception as e:
            logger.warning(f"Invalid image data: {e}")
            return False, "Invalid image file"

        # Check dimensions
        width, height = img.size
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            return False, f"Image too small. Minimum dimension: {MIN_DIMENSION}px"
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            return False, f"Image too large. Maximum dimension: {MAX_DIMENSION}px"

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

        # Save as JPEG
        img.save(output_path, 'JPEG', quality=OUTPUT_QUALITY, optimize=True)
        logger.info(f"Saved artwork: {output_path} ({width}x{height})")
        return True, ""

    except Exception as e:
        logger.error(f"Failed to process artwork: {e}")
        return False, "Failed to process image"


def delete_artwork(artwork_path: str) -> bool:
    """
    Delete an artwork file.
    Returns True on success or if file doesn't exist.
    """
    try:
        if artwork_path and os.path.exists(artwork_path):
            os.remove(artwork_path)
            logger.info(f"Deleted artwork: {artwork_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete artwork: {e}")
        return False
