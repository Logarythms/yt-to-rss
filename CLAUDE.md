# CLAUDE.md - Project Context for Claude

## Project Overview

yt-to-rss is a self-hosted web application that converts YouTube videos into podcast RSS feeds. Users can add videos or playlists, and the app downloads the audio, generates valid podcast RSS, and serves it for podcast apps to consume.

## Architecture

### Services (Docker Compose)

- **backend** (port 8000 internal): FastAPI app handling API requests and serving RSS/audio
- **frontend** (ports 80/3000 internal → 8080/3000 external): React SPA + nginx reverse proxy
- **worker**: Celery worker processing video downloads
- **redis**: Message broker for Celery

### Port Mapping

- `8080` → Public (RSS, audio, artwork, thumbnails only)
- `3000` → Admin UI + API (local network access)

The nginx config (`frontend/nginx.conf`) defines two server blocks to separate public and admin traffic.

## Key Files

### Backend (`backend/app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, CORS, router includes, startup (init_db) |
| `config.py` | Pydantic settings from environment variables |
| `database.py` | SQLAlchemy engine, sessions, `init_db()` with migrations |
| `models.py` | SQLAlchemy models: `Feed`, `Episode` |
| `schemas.py` | Pydantic request/response schemas |
| `auth.py` | Password verification, JWT creation/validation |
| `routers/auth.py` | Login endpoint |
| `routers/feeds.py` | Feed CRUD, episode management, storage info |
| `routers/rss.py` | Public endpoints: RSS XML, audio files, artwork, thumbnails |
| `services/youtube.py` | yt-dlp wrapper for metadata and playlist extraction |
| `services/audio.py` | Audio download and conversion to MP3 |
| `services/rss_generator.py` | feedgen-based RSS XML generation |
| `tasks/download.py` | Celery task for downloading episodes |
| `celery_app.py` | Celery configuration |

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `App.jsx` | React Router setup, auth protection |
| `api.js` | API client with token management |
| `components/Layout.jsx` | Navigation, logout |
| `components/Login.jsx` | Login form |
| `components/FeedForm.jsx` | Create/edit feed form |
| `components/FeedList.jsx` | Feed grid display |
| `components/EpisodeList.jsx` | Episode list with actions |
| `components/AddVideosModal.jsx` | URL input modal |
| `pages/Home.jsx` | Feed listing page |
| `pages/CreateFeed.jsx` | New feed page |
| `pages/EditFeed.jsx` | Feed detail/edit page |
| `pages/Storage.jsx` | Storage usage page |

## Database Schema

### Feed
- `id` (UUID, PK)
- `name` (string)
- `author` (string, nullable)
- `description` (text, nullable)
- `artwork_path` (string, nullable)
- `created_at`, `updated_at` (datetime)

### Episode
- `id` (UUID, PK)
- `feed_id` (FK → Feed)
- `youtube_id` (string)
- `title` (string)
- `description` (text, nullable)
- `thumbnail_url` (string, nullable)
- `audio_path` (string, nullable)
- `file_size` (int, nullable) - bytes
- `duration` (int, nullable) - seconds
- `published_at` (datetime, nullable)
- `status` (enum: pending, downloading, ready, failed)
- `error_message` (text, nullable)
- `created_at` (datetime)

## Common Tasks

### Adding a new field to Feed or Episode

1. Add column to model in `models.py`
2. Add migration in `database.py` `run_migrations()`
3. Update schemas in `schemas.py`
4. Update API endpoints in `routers/feeds.py`
5. Update frontend components/API client

### Adding a new API endpoint

1. Add route in appropriate router (`routers/*.py`)
2. Add schema if needed (`schemas.py`)
3. Add API method in `frontend/src/api.js`
4. Use in React components

### Modifying RSS output

Edit `services/rss_generator.py`. Uses the `feedgen` library with podcast extension.

## Important Patterns

### Authentication
- Password stored as plain text in config (compared with `secrets.compare_digest`)
- JWT tokens for API auth, stored in localStorage
- Public endpoints (RSS, audio, etc.) require no auth

### Background Tasks
- Episode downloads run as Celery tasks
- Frontend polls every 5 seconds to update episode status
- Failed tasks can be retried via API

### Database Migrations
- Simple migration system in `database.py`
- Checks for column existence before adding
- Runs automatically on startup via `init_db()`

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `BASE_URL` | backend | Public URL for RSS feed links |
| `APP_PASSWORD` | backend | Admin login password |
| `SECRET_KEY` | backend | JWT signing |
| `DATABASE_URL` | backend | SQLite path |
| `REDIS_URL` | backend, worker | Celery broker |
| `DATA_DIR`, `AUDIO_DIR`, `ARTWORK_DIR` | backend | File storage paths |

## Build Commands

```bash
# Full rebuild
docker-compose build --no-cache

# Rebuild specific service
docker-compose build --no-cache backend

# View logs
docker-compose logs -f backend worker

# Restart services
docker-compose restart backend worker
```

## Known Limitations

- SQLite database (not suitable for high concurrency)
- No user management (single password for all access)
- Thumbnail proxy fetches from YouTube on each request (no caching)
- yt-dlp may need updates for YouTube changes
