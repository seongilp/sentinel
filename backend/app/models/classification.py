from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from app.database import Base


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pii_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    # high|medium|low
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # confirmed|dismissed|pending
    detector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ClassificationUpdate(BaseModel):
    status: Optional[str] = None
    sensitivity_level: Optional[str] = None


class ClassificationRead(BaseModel):
    id: int
    scan_id: int
    connection_id: int
    schema_name: str
    table_name: str
    column_name: str
    data_type: Optional[str] = None
    pii_type: str
    confidence: float
    sensitivity_level: str
    status: str
    detector: Optional[str] = None
    evidence: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
