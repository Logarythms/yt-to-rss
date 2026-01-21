import os
import logging
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.database import init_db
from app.config import get_settings
from app.limiter import limiter
from app.routers import admin, auth, feeds, rss

logger = logging.getLogger(__name__)
settings = get_settings()

# Default secrets that must be changed
DEFAULT_SECRETS = {
    "app_password": "changeme",
    "secret_key": "your-secret-key-change-in-production",
}


def validate_secrets():
    """Ensure default secrets have been changed."""
    errors = []
    if settings.app_password == DEFAULT_SECRETS["app_password"]:
        errors.append("APP_PASSWORD is still set to the default value 'changeme'")
    if settings.secret_key == DEFAULT_SECRETS["secret_key"]:
        errors.append("SECRET_KEY is still set to the default value")

    if errors:
        raise RuntimeError(
            "SECURITY ERROR: Default secrets detected!\n"
            + "\n".join(f"  - {e}" for e in errors)
            + "\n\nPlease set secure values in your .env file or environment variables."
        )


def verify_ffprobe_available():
    """Verify ffprobe is installed and available."""
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            logger.warning("ffprobe returned non-zero exit code - audio validation may not work")
        else:
            logger.info("ffprobe is available")
    except FileNotFoundError:
        logger.error("ffprobe not found - audio file validation will fail closed")
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe version check timed out")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate configuration
    validate_secrets()
    verify_ffprobe_available()

    # Create directories and initialize database
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.audio_dir, exist_ok=True)
    os.makedirs(settings.artwork_dir, exist_ok=True)
    os.makedirs(settings.thumbnail_dir, exist_ok=True)
    init_db()
    yield
    # Shutdown: nothing special needed


app = FastAPI(
    title="yt-to-rss",
    description="Create podcast RSS feeds from YouTube videos",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - restrict to configured admin origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.admin_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(feeds.router)
app.include_router(rss.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
