from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.connection import Connection
from app.models.scan import Scan
from app.models.classification import Classification


async def get_summary(db: AsyncSession) -> dict[str, Any]:
    total_connections = await db.scalar(select(func.count()).select_from(Connection))
    total_scans = await db.scalar(select(func.count()).select_from(Scan))
    pii_columns = await db.scalar(
        select(func.count()).select_from(Classification).where(Classification.status != "dismissed")
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
        "pii_columns": pii_columns or 0,
        "recent_scans": recent_scans,
    }
