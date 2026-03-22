from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.dependencies import get_db
from app.models.scan import Scan, ScanCreate, ScanRead, ScanScheduleUpdate
from app.models.classification import Classification
from app.services.scan_service import run_scan
from app.services.audit_service import log

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("", response_model=list[ScanRead])
async def list_scans(db: AsyncSession = Depends(get_db)) -> list[ScanRead]:
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ScanRead, status_code=201)
async def create_scan(
    payload: ScanCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanRead:
    is_scheduled = bool(payload.cron_expression)
    scan = Scan(
        connection_id=payload.connection_id,
        status="scheduled" if is_scheduled else "pending",
        target_schemas=json.dumps(payload.target_schemas) if payload.target_schemas else None,
        sample_size=payload.sample_size,
        confidence_threshold=payload.confidence_threshold,
        cron_expression=payload.cron_expression,
        is_scheduled=is_scheduled,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    await log(db, "scan.created", "scan", scan.id, {"connection_id": scan.connection_id, "scheduled": is_scheduled}, menu="scans", result="success")

    if is_scheduled:
        from app.services.scheduler_service import register_scan_job
        register_scan_job(scan.id, payload.cron_expression)  # type: ignore[arg-type]
    else:
        background_tasks.add_task(run_scan, scan.id)
    return scan


@router.get("/{scan_id}", response_model=ScanRead)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScanRead:
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/results")
async def get_scan_results(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Classification)
        .where(Classification.scan_id == scan_id)
        .order_by(Classification.schema_name, Classification.table_name, Classification.confidence.desc())
    )
    items = result.scalars().all()
    return [
        {
            "id": c.id,
            "schema_name": c.schema_name,
            "table_name": c.table_name,
            "column_name": c.column_name,
            "data_type": c.data_type,
            "pii_type": c.pii_type,
            "confidence": c.confidence,
            "sensitivity_level": c.sensitivity_level,
            "status": c.status,
            "detector": c.detector,
            "evidence": c.evidence,
        }
        for c in items
    ]


@router.post("/{scan_id}/rerun", response_model=ScanRead, status_code=201)
async def rerun_scan(
    scan_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanRead:
    """기존 스캔과 동일한 설정으로 새 스캔을 즉시 실행한다."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    original = result.scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    new_scan = Scan(
        connection_id=original.connection_id,
        status="pending",
        target_schemas=original.target_schemas,
        sample_size=original.sample_size,
        confidence_threshold=original.confidence_threshold,
        cron_expression=None,
        is_scheduled=False,
    )
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)
    await log(db, "scan.created", "scan", new_scan.id, {
        "connection_id": new_scan.connection_id,
        "rerun_of": scan_id,
    }, menu="scans", result="success")
    background_tasks.add_task(run_scan, new_scan.id)
    return new_scan


@router.post("/{scan_id}/schedule", response_model=ScanRead)
async def update_scan_schedule(
    scan_id: int,
    payload: ScanScheduleUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScanRead:
    """스캔의 cron 스케줄을 설정하거나 제거한다."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.scheduler_service import register_scan_job, remove_scan_job

    scan.cron_expression = payload.cron_expression
    scan.is_scheduled = payload.cron_expression is not None
    if scan.is_scheduled:
        scan.status = "scheduled"
        register_scan_job(scan_id, payload.cron_expression)  # type: ignore[arg-type]
    else:
        scan.status = "completed" if scan.completed_at else "cancelled"
        remove_scan_job(scan_id)

    await db.commit()
    await db.refresh(scan)
    await log(db, "scan.scheduled", "scan", scan_id, {"cron": payload.cron_expression}, menu="scans", result="success")
    return scan


@router.post("/{scan_id}/cancel", response_model=ScanRead)
async def cancel_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScanRead:
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel scan with status '{scan.status}'")
    scan.status = "cancelled"
    await db.commit()
    await db.refresh(scan)
    return scan
