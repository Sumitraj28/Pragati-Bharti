from celery import Celery
from app.config import settings

celery_app = Celery(
    "document_intelligence_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="tasks.ping")
def ping_task():
    """Placeholder task for testing worker communication."""
    return {"status": "pong"}
