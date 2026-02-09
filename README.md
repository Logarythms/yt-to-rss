# yt-to-rss

A self-hosted web application that creates podcast RSS feeds from YouTube videos. Add individual videos or entire playlists, customize feed metadata, and subscribe using any podcast app.

## Features

- **Create podcast feeds** from YouTube videos and playlists
- **Automatic playlist refresh** - tracked playlists are periodically checked for new videos
- **Upload custom audio** - add your own MP3, M4A, WAV, FLAC, or OGG files
- **Automatic audio extraction** - downloads and converts to MP3
- **Custom metadata** - set feed name, author, description, and artwork
- **Automatic square images** - artwork and thumbnails are automatically letterboxed to 1:1 aspect ratio
- **Editable episodes** - customize episode title, description, and publish date
- **Valid podcast RSS** - compatible with all major podcast apps
- **Background processing** - videos download asynchronously via Celery workers
- **Storage monitoring** - track disk usage per feed
- **Secure by design** - admin interface separated from public endpoints, rate limiting, SSRF protection

## Architecture

| Service | Description |
|---------|-------------|
| **backend** | FastAPI application (API + RSS serving) |
| **frontend** | React/Vite app served via nginx |
| **worker** | Celery worker for background video processing |
| **beat** | Celery Beat scheduler for periodic playlist refresh |
| **redis** | Message broker for task queue |

## Quick Start

1. **Clone and configure**
   ```bash
   git clone <repo-url> yt-to-rss
   cd yt-to-rss
   cp .env.example .env
   ```

2. **Set required secrets in `.env`**
   ```bash
   APP_PASSWORD=your-secure-password-here
   SECRET_KEY=$(openssl rand -hex 32)
   ```
   > **Important:** The app will refuse to start with default/empty secrets.

3. **Start the stack**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the admin interface**
   - Open `http://localhost:3000` (or `http://<server-ip>:3000` from LAN)
   - Login with your configured password

5. **Create a feed and add videos**
   - Click "New Feed" and fill in the details
   - Add YouTube video or playlist URLs
   - Copy the RSS URL and add it to your podcast app

## Configuration

Edit `.env` or set environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PASSWORD` | Admin interface password | **Required** |
| `SECRET_KEY` | JWT signing key (32+ chars recommended) | **Required** |
| `BASE_URL` | Public URL for RSS feed links | `http://localhost:8080` |
| `ADMIN_ORIGIN` | Admin UI origin for CORS | `http://localhost:3000` |
| `PLAYLIST_REFRESH_INTERVAL` | Default seconds between playlist refreshes | `3600` (1 hour) |
| `PLAYLIST_REFRESH_CHECK_INTERVAL` | How often the scheduler checks for due playlists | `300` (5 min) |
| `MAX_NEW_EPISODES_PER_REFRESH` | Max new episodes added per playlist refresh | `50` |

> **Security Note:** `APP_PASSWORD` and `SECRET_KEY` have no defaults. The app will fail to start if they are not set or if they match the old default values (`changeme` / `your-secret-key-change-in-production`).

## Port Configuration

| Port | Purpose | Exposure |
|------|---------|----------|
| **8080** | Public endpoints (RSS, audio, artwork) | Safe to expose to internet |
| **3000** | Admin interface (web UI + API) | Local network only |

**Important:** Only port-forward 8080 on your router. Keep port 3000 restricted to your local network.

## Usage

### Creating a Feed

1. Click "New Feed" in the navigation
2. Enter a name, author, and description
3. Optionally upload custom artwork (recommended: 1400x1400 square image)
4. Click "Create Feed"

### Adding Videos

1. Open a feed from the home page
2. Click "Add Videos"
3. Paste YouTube URLs (one per line)
   - Individual videos: `https://www.youtube.com/watch?v=...`
   - Playlists: `https://www.youtube.com/playlist?list=...`
   - Short URLs: `https://youtu.be/...`
4. Videos will download in the background
5. Playlists are automatically tracked for future refresh

### Uploading Audio Files

1. Open a feed from the home page
2. Click "Upload Audio"
3. Select an audio file (MP3, M4A, WAV, FLAC, or OGG up to 500MB)
4. Optionally add a custom title, description, and thumbnail
5. Files are converted to MP3 automatically (large files process in background)

### Editing Episodes

1. Open a feed from the home page
2. Click "Edit" on any episode to expand the edit panel
3. Modify the title and/or description
4. Click "Save" to apply changes
5. Use "Clear" to revert a field to its original value (from YouTube or upload)

### Playlist Auto-Refresh

When you add a YouTube playlist, it is automatically tracked. New videos added to the playlist on YouTube will be detected and downloaded automatically.

- Playlists are checked on a configurable interval (default: every hour)
- Use the "Refresh Now" button on a feed's edit page to check immediately
- Tracked playlists can be enabled/disabled or removed without deleting episodes
- Configure `PLAYLIST_REFRESH_INTERVAL` to change the default check frequency
- Per-playlist interval overrides are supported via the API

### Subscribing to Feeds

1. Open a feed and copy the RSS URL
2. Add it to your podcast app:
   - **Apple Podcasts:** Library → Add Show by URL
   - **Pocket Casts:** Search → Add by URL
   - **Overcast:** Add Podcast → Add URL
   - **AntennaPod:** + → Add Podcast → RSS URL

## Storage

Monitor disk usage at `http://localhost:3000/storage`:
- Total disk usage and free space
- Per-feed storage breakdown
- Episode counts

### Maintenance

The Storage page includes maintenance tools:
- **Make Images Square** - retroactively apply letterboxing to existing artwork and thumbnails
  - Use "Preview" to see how many images would be processed
  - Already-square images are skipped automatically

## Security

- **Required secrets** - App refuses to start with default/empty passwords
- **JWT authentication** - Tokens include issuer/audience claims, 24-hour expiry
- **Rate limiting** - Login endpoint limited to 5 attempts per minute
- **CORS protection** - Only configured admin origin can access API
- **SSRF prevention** - Thumbnail proxy only allows YouTube domains
- **Path traversal prevention** - File serving validates paths stay within allowed directories
- **File validation** - Uploaded audio/artwork verified using ffprobe and PIL
- **Security headers** - X-Content-Type-Options, X-Frame-Options, X-XSS-Protection

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Celery, yt-dlp, feedgen, slowapi
- **Frontend:** React 18, Vite, TailwindCSS, React Router
- **Infrastructure:** Docker, docker-compose, Redis, nginx

## Development

### Running locally (without Docker)

**Backend:**
```bash
cd backend
pip install -e .
uvicorn app.main:app --reload
```

**Worker:**
```bash
cd backend
celery -A app.celery_app worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
yt-to-rss/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Settings
│       ├── database.py          # SQLAlchemy + migrations
│       ├── models.py            # Feed, Episode, PlaylistSource models
│       ├── schemas.py           # Pydantic schemas
│       ├── auth.py              # JWT authentication
│       ├── routers/             # API endpoints
│       ├── services/            # YouTube, audio, RSS
│       └── tasks/               # Celery tasks
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── App.jsx
        ├── api.js               # API client
        ├── components/          # React components
        └── pages/               # Page components
```

## Troubleshooting

### Videos stuck in "pending" status
- Check worker logs: `docker-compose logs worker`
- Ensure Redis is running: `docker-compose ps`
- Restart the worker: `docker-compose restart worker`

### Database migration errors
- The app auto-migrates on startup
- For a fresh start: `docker-compose down -v` (deletes all data)

### Clipboard not working
- The clipboard API requires HTTPS or localhost
- A fallback is included for LAN access

## License

MIT
