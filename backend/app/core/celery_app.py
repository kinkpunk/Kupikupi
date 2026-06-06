from importlib import import_module

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "kupikupi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.jobs.analytics",
        "app.jobs.notifications",
        "app.jobs.seed",
    ],
)

celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

for module_name in celery_app.conf.include:
    import_module(module_name)
