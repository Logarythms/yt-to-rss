import os
import json
import logging
import subprocess
import shutil
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@dataclass
class AudioMetadata:
    duration: Optional[int] = None  # seconds
    title: Optional[str] = None
    artist: Optional[str] = None


def validate_audio_file(filename: str, file_size: int) -> tuple[bool, str]:
    """
    Validate uploaded audio file.
    Returns (is_valid, error_message).
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"

    return True, ""


def extract_metadata(file_path: str) -> AudioMetadata:
    """
    Extract metadata from audio file using ffprobe.
    Returns AudioMetadata with duration, title, and artist if available.
    """
    metadata = AudioMetadata()

    try:
        # Get duration and format info
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)

            # Get duration from format or first audio stream
            if 'format' in data:
                fmt = data['format']
                if 'duration' in fmt:
                    metadata.duration = int(float(fmt['duration']))

                # Get ID3 tags from format tags
                tags = fmt.get('tags', {})
                # Tags might be lowercase or mixed case
                for key in tags:
                    if key.lower() == 'title':
                        metadata.title = tags[key]
                    elif key.lower() in ('artist', 'album_artist'):
                        metadata.artist = tags[key]

            # Fallback: get duration from audio stream
            if metadata.duration is None and 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'audio' and 'duration' in stream:
                        metadata.duration = int(float(stream['duration']))
                        break

    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timeout for {file_path}")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse ffprobe output: {e}")
    except FileNotFoundError:
        logger.error("ffprobe not found - ensure ffmpeg is installed")

    return metadata


def convert_to_mp3(input_path: str, output_path: str, bitrate: str = '192k') -> bool:
    """
    Convert audio file to MP3 format using ffmpeg.
    Returns True on success, False on failure.
    """
    try:
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # If already MP3, just copy
        if input_path.lower().endswith('.mp3'):
            shutil.copy2(input_path, output_path)
            logger.info(f"Copied MP3 file to {output_path}")
            return True

        result = subprocess.run(
            [
                'ffmpeg',
                '-i', input_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',
                '-ab', bitrate,
                '-y',  # Overwrite output
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for large files
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg conversion failed: {result.stderr}")
            return False

        logger.info(f"Converted to MP3: {output_path}")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"ffmpeg conversion timeout for {input_path}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found - ensure ffmpeg is installed")
        return False
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False


def is_mp3(filename: str) -> bool:
    """Check if file is already MP3 format."""
    return filename.lower().endswith('.mp3')
