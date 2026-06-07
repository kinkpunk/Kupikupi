from importlib import import_module

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "kupikupi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.jobs.analytics",
        "app.jobs.fx",
        "app.jobs.notifications",
        "app.jobs.retention",
        "app.jobs.seed",
        "app.jobs.sync",
    ],
)

celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "sync-due-source-configs": {
        "task": "sync.run_due_source_configs",
        "schedule": settings.source_sync_schedule_seconds,
    },
    "generate-notifications": {
        "task": "notifications.generate",
        "schedule": settings.notifications_generate_schedule_seconds,
    },
    "dispatch-notifications": {
        "task": "notifications.dispatch",
        "schedule": settings.notifications_dispatch_schedule_seconds,
    },
    "recompute-price-analytics": {
        "task": "analytics.recompute_all",
        "schedule": settings.analytics_recompute_schedule_seconds,
    },
    "update-fx-rates": {
        "task": "fx.update_rates",
        "schedule": settings.fx_rate_update_schedule_seconds,
    },
    "cleanup-retention": {
        "task": "retention.cleanup",
        "schedule": settings.retention_cleanup_schedule_seconds,
    },
}

for module_name in celery_app.conf.include:
    import_module(module_name)
