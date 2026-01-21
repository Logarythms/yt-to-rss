from PIL import Image


def letterbox_to_square(img: Image.Image) -> Image.Image:
    """Add black letterboxing to make image square (1:1 aspect ratio).

    Handles RGBA/P/LA modes by converting to RGB with black background.
    """
    width, height = img.size

    if width == height:
        # Still need to ensure RGB for consistency
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (0, 0, 0))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            return background
        elif img.mode != 'RGB':
            return img.convert('RGB')
        return img

    # Defensive: convert to RGB if not already
    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (0, 0, 0))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    target_size = max(width, height)
    letterbox_bg = Image.new('RGB', (target_size, target_size), (0, 0, 0))

    x_offset = (target_size - width) // 2
    y_offset = (target_size - height) // 2
    letterbox_bg.paste(img, (x_offset, y_offset))

    return letterbox_bg
