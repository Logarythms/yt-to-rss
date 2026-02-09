from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    'yt-to-rss',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['app.tasks.download', 'app.tasks.convert', 'app.tasks.refresh']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
    beat_schedule={
        'check-playlist-refreshes': {
            'task': 'app.tasks.refresh.check_playlist_refreshes',
            'schedule': settings.playlist_refresh_check_interval,
        },
    },
)
