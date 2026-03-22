"""APScheduler-based cron scan scheduler."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Module-level singleton
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def _parse_cron(expr: str) -> CronTrigger:
    """Parse a 5-field cron expression into an APScheduler CronTrigger."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (expected 5 fields): {expr!r}")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute, hour=hour, day=day,
        month=month, day_of_week=day_of_week,
    )


async def _execute_scheduled_scan(template_scan_id: int) -> None:
    """Create a new scan from the template and execute it."""
    from app.database import AsyncSessionLocal
    from app.models.scan import Scan
    from app.services.scan_service import run_scan
    from app.services.audit_service import log
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Scan).where(Scan.id == template_scan_id))
        template = result.scalar_one_or_none()
        if template is None or not template.is_scheduled:
            logger.warning("Scheduled scan template %d not found or no longer scheduled", template_scan_id)
            return

        child = Scan(
            connection_id=template.connection_id,
            status="pending",
            target_schemas=template.target_schemas,
            sample_size=template.sample_size,
            confidence_threshold=template.confidence_threshold,
            cron_expression=None,
            is_scheduled=False,
        )
        db.add(child)
        await db.commit()
        await db.refresh(child)
        await log(db, "scan.created", "scan", child.id, {
            "connection_id": child.connection_id,
            "triggered_by": f"schedule:{template_scan_id}",
        }, menu="scans", result="success")

    logger.info("Scheduled scan triggered: template=%d child=%d", template_scan_id, child.id)
    await run_scan(child.id)


def register_scan_job(scan_id: int, cron_expression: str) -> None:
    trigger = _parse_cron(cron_expression)
    scheduler.add_job(
        _execute_scheduled_scan,
        trigger=trigger,
        args=[scan_id],
        id=f"scan_{scan_id}",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Registered scheduled scan job: scan_id=%d cron=%r", scan_id, cron_expression)


def remove_scan_job(scan_id: int) -> None:
    try:
        scheduler.remove_job(f"scan_{scan_id}")
        logger.info("Removed scheduled scan job: scan_id=%d", scan_id)
    except Exception:
        pass


async def restore_scheduled_scans() -> None:
    """On startup, re-register all active scheduled scans from the DB."""
    from app.database import AsyncSessionLocal
    from app.models.scan import Scan
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Scan).where(Scan.is_scheduled == True)  # noqa: E712
        )
        scheduled = result.scalars().all()

    for scan in scheduled:
        if scan.cron_expression:
            try:
                register_scan_job(scan.id, scan.cron_expression)
            except Exception as e:
                logger.error("Failed to restore scan job %d: %s", scan.id, e)

    logger.info("Restored %d scheduled scan job(s)", len(scheduled))
