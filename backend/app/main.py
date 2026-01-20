import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.config import get_settings
from app.routers import auth, feeds, rss

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create directories and initialize database
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.audio_dir, exist_ok=True)
    os.makedirs(settings.artwork_dir, exist_ok=True)
    init_db()
    yield
    # Shutdown: nothing special needed


app = FastAPI(
    title="yt-to-rss",
    description="Create podcast RSS feeds from YouTube videos",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(feeds.router)
app.include_router(rss.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
