from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.celery_app import celery_app
from app.config import settings
from app.database import SyncSessionLocal
from app.models.export import Export, ExportStatus
from app.models.job import Job, JobStatus
from app.models.publish_job import PublishJob, PublishStatus
from app.services.workspace import (
    WORKSPACE_ROOTS,
    is_workspace_lease_active,
    read_workspace_manifest,
    release_workspace_lease,
)

logger = logging.getLogger(__name__)


def _parse_iso(iso_value: str | None) -> datetime | None:
    if not iso_value:
        return None
    try:
        dt = datetime.fromisoformat(iso_value)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _directory_size(path: Path) -> int:
    size = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                size += item.stat().st_size
            except OSError:
                continue
    return size


def _job_terminal_from_manifest(manifest: dict) -> tuple[bool | None, str]:
    refs = manifest.get("refs") or {}
    job_type = str(manifest.get("job_type") or "").strip()

    with SyncSessionLocal() as db:
        if job_type in {"ingest", "transcribe", "score"}:
            video_id = refs.get("video_id") or manifest.get("video_id")
            if not video_id:
                return None, "missing_video_ref"
            job = (
                db.execute(
                    select(Job)
                    .where(Job.video_id == video_id, Job.type == job_type)
                    .order_by(Job.created_at.desc())
                )
                .scalars()
                .first()
            )
            if not job:
                return None, "db_job_missing"
            return job.status in {JobStatus.done, JobStatus.failed}, f"db_job_status={job.status.value}"

        if job_type == "render":
            export_id = refs.get("export_id")
            if not export_id:
                return None, "missing_export_ref"
            export_row = db.execute(select(Export).where(Export.id == export_id)).scalars().first()
            if not export_row:
                return None, "db_export_missing"
            return export_row.status in {ExportStatus.ready, ExportStatus.error}, f"db_export_status={export_row.status.value}"

        if job_type == "publish":
            publish_job_id = refs.get("publish_job_id")
            if not publish_job_id:
                return None, "missing_publish_ref"
            publish_row = db.execute(select(PublishJob).where(PublishJob.id == publish_job_id)).scalars().first()
            if not publish_row:
                return None, "db_publish_missing"
            terminal = publish_row.status in {
                PublishStatus.published,
                PublishStatus.failed,
                PublishStatus.waiting_user_action,
                PublishStatus.provider_not_configured,
            }
            return terminal, f"db_publish_status={publish_row.status.value}"
    return None, "unknown_job_type"


def sweep_workspaces_impl(*, dry_run: bool) -> dict:
    now = datetime.now(timezone.utc)
    retention_seconds = max(3600, int(settings.workspace_cleanup_retention_hours) * 3600)
    orphan_grace_seconds = max(300, int(settings.workspace_cleanup_orphan_grace_minutes) * 60)

    visited = 0
    reclaimed_dirs = 0
    reclaimed_bytes = 0
    skipped = 0
    disagreements = 0
    failures = 0

    unique_roots = {root.resolve() for root in WORKSPACE_ROOTS.values()}
    for root in unique_roots:
        if not root.exists() or not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            visited += 1
            manifest = read_workspace_manifest(child)
            st = child.stat()
            age_seconds = max(0.0, (now - datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)).total_seconds())

            if "clipbandit-storage" in str(child):
                skipped += 1
                continue

            if manifest is None:
                if age_seconds < orphan_grace_seconds:
                    skipped += 1
                    continue
                bytes_size = _directory_size(child)
                if not dry_run:
                    shutil.rmtree(child, ignore_errors=True)
                reclaimed_dirs += 1
                reclaimed_bytes += bytes_size
                continue

            lease_id = str(manifest.get("lease_id") or "").strip()
            lease_active = bool(lease_id and is_workspace_lease_active(lease_id))
            manifest_state = str(manifest.get("state") or "active").strip()
            manifest_heartbeat = _parse_iso(manifest.get("last_heartbeat_at"))
            if manifest_heartbeat:
                age_seconds = max(0.0, (now - manifest_heartbeat).total_seconds())

            db_terminal, db_reason = _job_terminal_from_manifest(manifest)
            stale_lease_candidate = False

            if lease_active and db_terminal is True:
                disagreements += 1
                if age_seconds < orphan_grace_seconds:
                    skipped += 1
                    logger.warning(
                        "[workspace_cleanup] disagreement=lease_active_db_terminal path=%s reason=%s",
                        child,
                        db_reason,
                    )
                    continue
                stale_lease_candidate = True

            if (not lease_active) and db_terminal is False:
                disagreements += 1
                skipped += 1
                logger.warning(
                    "[workspace_cleanup] disagreement=lease_missing_db_running path=%s reason=%s",
                    child,
                    db_reason,
                )
                continue

            eligible = False
            if manifest_state in {"terminal_success", "terminal_failed"} and age_seconds >= retention_seconds:
                eligible = True
            elif not lease_active and db_terminal is True and age_seconds >= retention_seconds:
                eligible = True
            elif not lease_active and db_terminal is None and age_seconds >= orphan_grace_seconds:
                eligible = True

            if not eligible:
                skipped += 1
                continue

            bytes_size = _directory_size(child)
            try:
                if stale_lease_candidate and lease_id:
                    release_workspace_lease(lease_id)
                if not dry_run:
                    shutil.rmtree(child, ignore_errors=True)
                reclaimed_dirs += 1
                reclaimed_bytes += bytes_size
            except Exception as exc:
                failures += 1
                logger.warning("[workspace_cleanup] failed path=%s error=%s", child, exc)

    payload = {
        "dry_run": dry_run,
        "visited": visited,
        "reclaimed_dirs": reclaimed_dirs,
        "reclaimed_bytes": reclaimed_bytes,
        "skipped": skipped,
        "disagreements": disagreements,
        "failures": failures,
    }
    logger.info("[workspace_cleanup] summary=%s", payload)
    return payload


@celery_app.task(name="app.worker.tasks.cleanup.sweep_workspaces", queue="ingest")
def sweep_workspaces(dry_run: bool = False):
    return sweep_workspaces_impl(dry_run=dry_run)
