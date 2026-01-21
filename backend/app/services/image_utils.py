from PIL import Image


def letterbox_to_square(img: Image.Image) -> Image.Image:
    """Add black letterboxing to make image square (1:1 aspect ratio)."""
    width, height = img.size

    if width == height:
        return img

    target_size = max(width, height)
    background = Image.new('RGB', (target_size, target_size), (0, 0, 0))

    x_offset = (target_size - width) // 2
    y_offset = (target_size - height) // 2
    background.paste(img, (x_offset, y_offset))

    return background
