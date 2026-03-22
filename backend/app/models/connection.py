from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

from app.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[str] = mapped_column(String(50), nullable=False)  # mysql|oracle|mongodb|clickhouse
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    extra_params: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)  # JSON string
    info_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON snapshot
    info_cached_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConnectionCreate(BaseModel):
    name: str
    db_type: str
    host: str
    port: int
    database: Optional[str] = None  # None = all databases
    username: str
    password: Optional[str] = None
    extra_params: Optional[str] = None


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    extra_params: Optional[str] = None


class ConnectionRead(BaseModel):
    id: int
    name: str
    db_type: str
    host: str
    port: int
    database: Optional[str] = None
    username: str
    extra_params: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
