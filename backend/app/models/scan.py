from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from app.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # pending|running|completed|failed|cancelled|scheduled
    target_schemas: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # JSON list
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    total_tables: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_columns: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pii_columns_found: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ScanCreate(BaseModel):
    connection_id: int
    target_schemas: Optional[list[str]] = None
    sample_size: int = 100
    confidence_threshold: float = 0.5
    cron_expression: Optional[str] = None


class ScanScheduleUpdate(BaseModel):
    cron_expression: Optional[str] = None  # None = remove schedule


class ScanRead(BaseModel):
    id: int
    connection_id: int
    status: str
    target_schemas: Optional[str] = None
    sample_size: int
    confidence_threshold: float
    total_tables: Optional[int] = None
    total_columns: Optional[int] = None
    pii_columns_found: Optional[int] = None
    error_message: Optional[str] = None
    cron_expression: Optional[str] = None
    is_scheduled: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
