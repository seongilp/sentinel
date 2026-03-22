from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pii_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_method: Mapped[str] = mapped_column(String(50), nullable=False)
    # column_name|regex|both
    column_patterns: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # JSON list
    data_patterns: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # JSON list
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RuleCreate(BaseModel):
    name: str
    pii_type: str
    detection_method: str
    column_patterns: Optional[list[str]] = None
    data_patterns: Optional[list[str]] = None
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    pii_type: Optional[str] = None
    detection_method: Optional[str] = None
    column_patterns: Optional[list[str]] = None
    data_patterns: Optional[list[str]] = None
    is_active: Optional[bool] = None


class RuleRead(BaseModel):
    id: int
    name: str
    pii_type: str
    detection_method: str
    column_patterns: Optional[str] = None
    data_patterns: Optional[str] = None
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
