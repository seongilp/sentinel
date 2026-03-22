from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db
from app.models.connection import Connection
from app.models.scan import Scan
from app.models.classification import Classification
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    total_connections = await db.scalar(select(func.count()).select_from(Connection))
    total_scans = await db.scalar(select(func.count()).select_from(Scan))
    scans_completed = await db.scalar(select(func.count()).select_from(Scan).where(Scan.status == "completed"))
    scans_pending = await db.scalar(select(func.count()).select_from(Scan).where(Scan.status.in_(["pending", "running", "scheduled"])))
    scans_cancelled = await db.scalar(select(func.count()).select_from(Scan).where(Scan.status.in_(["cancelled", "failed"])))
    pii_columns = await db.scalar(
        select(func.count()).select_from(Classification).where(Classification.status != "dismissed")
    )
    high_risk = await db.scalar(
        select(func.count()).select_from(Classification).where(
            Classification.status != "dismissed",
            Classification.sensitivity_level == "high",
        )
    )

    recent_result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(5)
    )
    recent_scans = [
        {
            "id": s.id,
            "connection_id": s.connection_id,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
        }
        for s in recent_result.scalars().all()
    ]

    return {
        "total_connections": total_connections or 0,
        "total_scans": total_scans or 0,
        "scans_completed": scans_completed or 0,
        "scans_pending": scans_pending or 0,
        "scans_cancelled": scans_cancelled or 0,
        "pii_columns": pii_columns or 0,
        "high_risk": high_risk or 0,
        "recent_scans": recent_scans,
    }


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)) -> list[Any]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)
    )
    return [
        {
            "id": a.id,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "details": a.details,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]
