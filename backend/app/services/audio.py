import os
import logging
import yt_dlp
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def download_audio(youtube_id: str, output_dir: str = None) -> str:
    """
    Download audio from YouTube video and convert to MP3.
    Returns the path to the downloaded file.
    """
    if output_dir is None:
        output_dir = settings.audio_dir

    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{youtube_id}.mp3")

    # Check if already downloaded
    if os.path.exists(output_path):
        logger.info(f"Audio already exists: {output_path}")
        return output_path

    url = f"https://www.youtube.com/watch?v={youtube_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, f'{youtube_id}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info(f"Downloading audio for {youtube_id}")
        ydl.download([url])

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Download failed: {output_path} not created")

    logger.info(f"Download complete: {output_path}")
    return output_path


def get_audio_file_size(youtube_id: str) -> int:
    """Get file size in bytes for an audio file."""
    path = os.path.join(settings.audio_dir, f"{youtube_id}.mp3")
    if os.path.exists(path):
        return os.path.getsize(path)
    return 0
