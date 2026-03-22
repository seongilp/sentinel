from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from app.dependencies import get_db
from app.models.audit_log import AuditLog, AuditLogRead
from app.services import audit_service

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    details: dict[str, Any] | None = None
    menu: str | None = None
    result: str = "success"
    user_id: str = "system"


@router.post("", response_model=AuditLogRead, status_code=201)
async def create_audit_log(
    body: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
) -> AuditLogRead:
    entry = await audit_service.log(
        db,
        action=body.action,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        details=body.details,
        user_id=body.user_id,
        menu=body.menu,
        result=body.result,
    )
    return AuditLogRead.model_validate(entry)


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0),
    menu: str | None = Query(default=None),
    result: str | None = Query(default=None),
    action: str | None = Query(default=None),
) -> list[AuditLogRead]:
    query = select(AuditLog)
    if menu:
        query = query.where(AuditLog.menu == menu)
    if result:
        query = query.where(AuditLog.result == result)
    if action:
        query = query.where(AuditLog.action.contains(action))
    result_rows = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result_rows.scalars().all())
