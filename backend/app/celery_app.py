from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "youtube_music_automation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Print configuration for debugging
print(f"Celery app configured with broker: {settings.REDIS_URL}")
print(f"Celery app configured with backend: {settings.REDIS_URL}")
print(f"Celery app include modules: {celery_app.conf.include}")
