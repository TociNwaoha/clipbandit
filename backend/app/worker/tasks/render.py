import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.export import Export, ExportStatus
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.render.render_export", bind=True, queue="render", max_retries=0)
def render_export(self, export_id: str, job_id: str | None = None):
    """
    Prompt 5 MVP behavior:
    - Export creation is real and enqueued.
    - Render lifecycle is honest.
    - Full FFmpeg render pipeline lands in Prompt 6.
    """
    logger.info("[render] task received export_id=%s job_id=%s", export_id, job_id)

    try:
        export_uuid = uuid.UUID(export_id)
    except ValueError:
        logger.error("[render] invalid export id: %s", export_id)
        return {"export_id": export_id, "status": "error", "message": "invalid export id"}

    job_uuid: uuid.UUID | None = None
    if job_id:
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            logger.warning("[render] invalid job id: %s", job_id)

    with SyncSessionLocal() as db:
        export = db.execute(select(Export).where(Export.id == export_uuid)).scalars().first()
        if not export:
            logger.error("[render] export not found export_id=%s", export_id)
            if job_uuid:
                job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
                if job:
                    job.status = JobStatus.failed
                    job.error = f"Export not found: {export_id}"
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()
            return {"export_id": export_id, "status": "error", "message": "export not found"}

        job: Job | None = None
        if job_uuid:
            job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
            if job:
                job.status = JobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job.attempts = (job.attempts or 0) + 1

        export.status = ExportStatus.rendering
        export.error_message = None
        db.commit()
        logger.info("[render] export status set to rendering export_id=%s", export_id)

        # Honest status until full renderer is implemented.
        not_implemented_message = "Render pipeline is not implemented yet. Prompt 6 will produce final files."
        export.status = ExportStatus.error
        export.error_message = not_implemented_message

        if job:
            job.status = JobStatus.failed
            job.error = not_implemented_message
            job.completed_at = datetime.now(timezone.utc)

        db.commit()
        logger.info("[render] export marked error (expected stub) export_id=%s", export_id)

    return {
        "export_id": export_id,
        "status": "error",
        "message": "render stub active",
    }
