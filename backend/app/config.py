from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Base URL for public RSS links (e.g., https://podcasts.example.com)
    base_url: str = "http://localhost:8000"

    # Admin origin for CORS (e.g., http://localhost:3000)
    admin_origin: str = "http://localhost:3000"

    # Plain password for web interface (will be hashed at runtime)
    app_password: str = "changeme"

    # JWT settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Database
    database_url: str = "sqlite:///./data/db.sqlite"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Data paths
    data_dir: str = "./data"
    audio_dir: str = "./data/audio"
    artwork_dir: str = "./data/artwork"
    thumbnail_dir: str = "./data/thumbnails"

    # Playlist refresh settings
    playlist_refresh_interval: int = 86400  # Default seconds between playlist refreshes (24 hours)
    playlist_refresh_check_interval: int = 300  # How often Beat checks for due playlists (seconds)
    max_new_episodes_per_refresh: int = 50  # Max new episodes added per playlist refresh

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
