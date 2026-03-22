from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models.audit_log import AuditLog


async def log(
    db: AsyncSession,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
    *,
    user_id: str = "system",
    menu: str | None = None,
    result: str = "success",
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        menu=menu,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
