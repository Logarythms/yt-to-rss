# yt-to-rss

A self-hosted web application that creates podcast RSS feeds from YouTube videos. Add individual videos or entire playlists, customize feed metadata, and subscribe using any podcast app.

## Features

- **Create podcast feeds** from YouTube videos and playlists
- **Automatic audio extraction** - downloads and converts to MP3
- **Custom metadata** - set feed name, author, description, and artwork
- **Valid podcast RSS** - compatible with all major podcast apps
- **Background processing** - videos download asynchronously via Celery workers
- **Storage monitoring** - track disk usage per feed
- **Secure by design** - admin interface separated from public endpoints

## Architecture

| Service | Description |
|---------|-------------|
| **backend** | FastAPI application (API + RSS serving) |
| **frontend** | React/Vite app served via nginx |
| **worker** | Celery worker for background video processing |
| **redis** | Message broker for task queue |

## Quick Start

1. **Clone and configure**
   ```bash
   git clone <repo-url> yt-to-rss
   cd yt-to-rss
   cp .env.example .env
   # Edit .env to set your password and public URL
   ```

2. **Start the stack**
   ```bash
   docker-compose up -d --build
   ```

3. **Access the admin interface**
   - Open `http://localhost:3000` (or `http://<server-ip>:3000` from LAN)
   - Login with your configured password (default: `changeme`)

4. **Create a feed and add videos**
   - Click "New Feed" and fill in the details
   - Add YouTube video or playlist URLs
   - Copy the RSS URL and add it to your podcast app

## Configuration

Edit `.env` or set environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Public URL for RSS feed links | `http://localhost:8080` |
| `APP_PASSWORD` | Admin interface password | `changeme` |
| `SECRET_KEY` | JWT signing key | (change in production!) |

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

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Celery, yt-dlp, feedgen
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
│       ├── models.py            # Feed, Episode models
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
