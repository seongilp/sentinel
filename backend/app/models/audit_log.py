from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    menu: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # connections|scans|rules|...
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(String(50), nullable=False, default="success")  # success|failure|info
    details: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLogRead(BaseModel):
    id: int
    user_id: str = "system"
    menu: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    result: str = "success"
    details: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
