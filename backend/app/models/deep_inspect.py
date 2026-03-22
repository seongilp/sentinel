from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel
from app.database import Base


class DeepInspectJob(Base):
    __tablename__ = "deep_inspect_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    columns: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/completed/failed/cancelled
    batch_size: Mapped[int] = mapped_column(Integer, default=1000)
    total_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scanned_rows: Mapped[int] = mapped_column(Integer, default=0)
    pii_matches: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class DeepInspectMatch(Base):
    __tablename__ = "deep_inspect_matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    row_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pii_type: Mapped[str] = mapped_column(String(100), nullable=False)
    matched_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# Pydantic schemas
class JobCreate(BaseModel):
    connection_id: int
    schema_name: str
    table_name: str
    columns: list[str] = []  # empty = all columns
    batch_size: int = 1000


class JobRead(BaseModel):
    id: int
    connection_id: int
    schema_name: str
    table_name: str
    columns: list[str]
    status: str
    batch_size: int
    total_rows: Optional[int]
    scanned_rows: int
    pii_matches: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_pct: float = 0.0

    model_config = {"from_attributes": True}


class MatchRead(BaseModel):
    id: int
    job_id: int
    row_offset: int
    column_name: str
    pii_type: str
    matched_value: str
    confidence: float

    model_config = {"from_attributes": True}
