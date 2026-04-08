from celery import Celery

from app.config import settings

celery_app = Celery(
    "clipbandit",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.worker.tasks.ingest",
        "app.worker.tasks.transcribe",
        "app.worker.tasks.score",
        "app.worker.tasks.render",
        "app.worker.tasks.publish",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_routes={
        "app.worker.tasks.ingest.*": {"queue": "ingest"},
        "app.worker.tasks.transcribe.*": {"queue": "transcribe"},
        "app.worker.tasks.score.*": {"queue": "score"},
        "app.worker.tasks.render.*": {"queue": "render"},
        "app.worker.tasks.publish.*": {"queue": "publish"},
    },
    task_queues={
        "ingest": {},
        "transcribe": {},
        "score": {},
        "render": {},
        "publish": {},
    },
)
