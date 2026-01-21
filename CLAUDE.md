# CLAUDE.md - Project Context for Claude

## Instructions for Claude

- **Auto-commit**: After making any code changes, automatically create a git commit with a descriptive message. Do not push to remote.
- **Keep docs updated**: When making changes, update both `README.md` and `CLAUDE.md` to reflect those changes in the same commit.

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
| `main.py` | FastAPI app, CORS, router includes, startup validation, rate limiter setup |
| `config.py` | Pydantic settings from environment variables |
| `database.py` | SQLAlchemy engine, sessions, `init_db()` with migrations |
| `models.py` | SQLAlchemy models: `Feed`, `Episode` |
| `schemas.py` | Pydantic request/response schemas |
| `auth.py` | Password verification, JWT creation/validation with iss/aud claims |
| `limiter.py` | Rate limiter instance (slowapi) |
| `routers/auth.py` | Login endpoint with rate limiting |
| `routers/feeds.py` | Feed CRUD, episode management, audio upload, storage info |
| `routers/rss.py` | Public endpoints: RSS XML, audio files, artwork, thumbnails (with path validation) |
| `services/youtube.py` | yt-dlp wrapper for metadata and playlist extraction |
| `services/audio.py` | Audio download and conversion to MP3 |
| `services/audio_converter.py` | Audio file validation (ffprobe), metadata extraction, MP3 conversion |
| `services/artwork.py` | Artwork validation and processing (PIL) |
| `services/thumbnail.py` | Thumbnail validation and processing (PIL) |
| `services/rss_generator.py` | feedgen-based RSS XML generation |
| `tasks/download.py` | Celery task for downloading YouTube episodes + thumbnail caching |
| `tasks/convert.py` | Celery task for converting uploaded audio files |
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
- `youtube_id` (string, nullable) - null for uploaded audio
- `title` (string)
- `description` (text, nullable)
- `thumbnail_url` (string, nullable) - YouTube thumbnail URL
- `thumbnail_path` (string, nullable) - locally cached thumbnail
- `audio_path` (string, nullable)
- `file_size` (int, nullable) - bytes
- `duration` (int, nullable) - seconds
- `published_at` (datetime, nullable)
- `status` (enum: pending, downloading, ready, failed)
- `error_message` (text, nullable)
- `source_type` (enum: youtube, upload) - default 'youtube'
- `original_filename` (string, nullable) - for uploaded files
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

### Authentication & Security
- App fails to start if `APP_PASSWORD` or `SECRET_KEY` are default values
- Password compared with `secrets.compare_digest` for timing-safe comparison
- JWT tokens include `iss` (yt-to-rss) and `aud` (yt-to-rss-api) claims, validated on verify
- Token expiry: 24 hours
- Rate limiting: 5 login attempts per minute (slowapi)
- CORS restricted to configured `ADMIN_ORIGIN`
- Public endpoints (RSS, audio, etc.) require no auth

### File Security
- Path traversal prevention: `validate_file_path()` in `routers/rss.py` ensures files are within allowed directories
- SSRF prevention: Thumbnail proxy only allows `i.ytimg.com`, `i9.ytimg.com`, `img.youtube.com`
- Artwork/thumbnail validation: PIL verifies images are valid before saving
- Audio validation: ffprobe verifies files contain audio streams (fail-closed)

### Background Tasks
- Episode downloads run as Celery tasks (`tasks/download.py`)
- Large file uploads (>100MB) processed in background (`tasks/convert.py`)
- Frontend polls every 5 seconds to update episode status
- Failed tasks can be retried via API
- Error messages sanitized (full error logged, generic message shown to user)

### Database Migrations
- Simple migration system in `database.py`
- Checks for column existence before adding
- Runs automatically on startup via `init_db()`

## Environment Variables

| Variable | Used By | Purpose | Required |
|----------|---------|---------|----------|
| `APP_PASSWORD` | backend | Admin login password | **Yes** |
| `SECRET_KEY` | backend | JWT signing key | **Yes** |
| `BASE_URL` | backend | Public URL for RSS feed links | No (default: `http://localhost:8080`) |
| `ADMIN_ORIGIN` | backend | CORS allowed origin for admin UI | No (default: `http://localhost:3000`) |
| `DATABASE_URL` | backend | SQLite path | No |
| `REDIS_URL` | backend, worker | Celery broker | No |
| `DATA_DIR` | backend | Base data directory | No |
| `AUDIO_DIR` | backend | Audio file storage | No |
| `ARTWORK_DIR` | backend | Feed artwork storage | No |
| `THUMBNAIL_DIR` | backend | Cached thumbnail storage | No |

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
- yt-dlp may need updates for YouTube changes
