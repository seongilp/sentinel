from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.connection import Connection, ConnectionCreate, ConnectionUpdate


async def get_all(db: AsyncSession) -> list[Connection]:
    result = await db.execute(select(Connection))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, connection_id: int) -> Connection | None:
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, payload: ConnectionCreate) -> Connection:
    connection = Connection(
        name=payload.name,
        db_type=payload.db_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        encrypted_password=payload.password,
        extra_params=payload.extra_params,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


async def update(db: AsyncSession, connection: Connection, payload: ConnectionUpdate) -> Connection:
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        connection.encrypted_password = update_data.pop("password")
    for field, value in update_data.items():
        setattr(connection, field, value)
    await db.commit()
    await db.refresh(connection)
    return connection


async def delete(db: AsyncSession, connection: Connection) -> None:
    await db.delete(connection)
    await db.commit()
