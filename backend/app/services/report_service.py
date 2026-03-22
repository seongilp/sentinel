from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.classification import Classification


async def get_pii_inventory(
    db: AsyncSession, scan_id: int | None = None
) -> list[dict[str, Any]]:
    query = select(Classification).where(Classification.status != "dismissed")
    if scan_id is not None:
        query = query.where(Classification.scan_id == scan_id)
    result = await db.execute(query.order_by(Classification.schema_name, Classification.table_name))
    return [
        {
            "id": c.id,
            "schema_name": c.schema_name,
            "table_name": c.table_name,
            "column_name": c.column_name,
            "pii_type": c.pii_type,
            "confidence": c.confidence,
            "sensitivity_level": c.sensitivity_level,
            "status": c.status,
        }
        for c in result.scalars().all()
    ]
