import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.dependencies import get_db
from app.models.deep_inspect import DeepInspectJob, DeepInspectMatch, JobCreate, JobRead, MatchRead
from app.services import deep_inspect_service

router = APIRouter(prefix="/deep-inspect", tags=["deep-inspect"])


def _to_read(job: DeepInspectJob) -> JobRead:
    pct = 0.0
    if job.total_rows and job.total_rows > 0:
        pct = round(job.scanned_rows / job.total_rows * 100, 1)
    return JobRead(
        id=job.id,
        connection_id=job.connection_id,
        schema_name=job.schema_name,
        table_name=job.table_name,
        columns=json.loads(job.columns) if job.columns else [],
        status=job.status,
        batch_size=job.batch_size,
        total_rows=job.total_rows,
        scanned_rows=job.scanned_rows,
        pii_matches=job.pii_matches,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress_pct=pct,
    )


@router.get("", response_model=list[JobRead])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[JobRead]:
    result = await db.execute(select(DeepInspectJob).order_by(desc(DeepInspectJob.id)))
    return [_to_read(j) for j in result.scalars().all()]


@router.post("", response_model=JobRead, status_code=201)
async def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = DeepInspectJob(
        connection_id=payload.connection_id,
        schema_name=payload.schema_name,
        table_name=payload.table_name,
        columns=json.dumps(payload.columns),
        batch_size=max(100, min(payload.batch_size, 10000)),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background_tasks.add_task(deep_inspect_service.run_job, job.id)
    return _to_read(job)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)) -> JobRead:
    job = await db.get(DeepInspectJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_read(job)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    job = await db.get(DeepInspectJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    job.status = "cancelled"
    await db.commit()
    return {"success": True}


@router.get("/{job_id}/matches", response_model=list[MatchRead])
async def get_matches(
    job_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, le=500),
    column: str | None = None,
    pii_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[MatchRead]:
    q = select(DeepInspectMatch).where(DeepInspectMatch.job_id == job_id)
    if column:
        q = q.where(DeepInspectMatch.column_name == column)
    if pii_type:
        q = q.where(DeepInspectMatch.pii_type == pii_type)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return [MatchRead.model_validate(m) for m in result.scalars().all()]
