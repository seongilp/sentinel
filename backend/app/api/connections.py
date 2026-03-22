import json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.connection import Connection, ConnectionCreate, ConnectionUpdate, ConnectionRead
from app.services.audit_service import log

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionRead])
async def list_connections(db: AsyncSession = Depends(get_db)) -> list[ConnectionRead]:
    result = await db.execute(select(Connection))
    return list(result.scalars().all())


@router.post("", response_model=ConnectionRead, status_code=201)
async def create_connection(
    payload: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    connection = Connection(
        name=payload.name,
        db_type=payload.db_type,
        host=payload.host,
        port=payload.port,
        database=payload.database or "",
        username=payload.username,
        encrypted_password=payload.password,  # TODO: encrypt in Phase 2
        extra_params=payload.extra_params,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    await log(db, "connection.created", "connection", connection.id, {"name": connection.name, "db_type": connection.db_type}, menu="connections", result="success")
    return connection


@router.post("/check", response_model=dict)
async def check_connection(payload: ConnectionCreate) -> dict:
    """저장 없이 DB 연결 가능 여부만 테스트"""
    try:
        from app.connectors.factory import create_connector
        connector = create_connector(payload.db_type, {
            "host": payload.host,
            "port": payload.port,
            "database": payload.database,
            "username": payload.username,
            "password": payload.password,
        })
        ok = await connector.test_connection()
        await connector.close()
        return {"success": ok, "message": "연결 성공" if ok else "연결 실패"}
    except NotImplementedError:
        return {"success": False, "message": f"{payload.db_type} 커넥터는 Phase 2에서 지원 예정입니다."}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/{connection_id}", response_model=ConnectionRead)
async def get_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.put("/{connection_id}", response_model=ConnectionRead)
async def update_connection(
    connection_id: int,
    payload: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        new_pw = update_data.pop("password")
        if new_pw:  # only overwrite if a non-empty password was provided
            connection.encrypted_password = new_pw
    for field, value in update_data.items():
        setattr(connection, field, value)

    await db.commit()
    await db.refresh(connection)
    await log(db, "connection.updated", "connection", connection.id, {"name": connection.name, "db_type": connection.db_type}, menu="connections", result="success")
    return connection


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn_name = connection.name
    conn_db_type = connection.db_type
    await db.delete(connection)
    await db.commit()
    await log(db, "connection.deleted", "connection", connection_id, {"name": conn_name, "db_type": conn_db_type}, menu="connections", result="success")


@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        from app.connectors.factory import create_connector
        connector = create_connector(connection.db_type, {
            "host": connection.host,
            "port": connection.port,
            "database": connection.database,
            "username": connection.username,
            "password": connection.encrypted_password,
        })
        ok = await connector.test_connection()
        await connector.close()
        return {"success": ok, "message": "연결 성공" if ok else "연결 실패"}
    except NotImplementedError:
        return {"success": False, "message": f"{connection.db_type} 커넥터는 아직 지원되지 않습니다."}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/{connection_id}/columns")
async def get_columns(
    connection_id: int,
    schema: str,
    table: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, str]]:
    """특정 테이블의 컬럼 목록을 반환한다."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        from app.connectors.factory import create_connector
        connector = create_connector(connection.db_type, {
            "host": connection.host,
            "port": connection.port,
            "database": connection.database,
            "username": connection.username,
            "password": connection.encrypted_password,
        })
        cols = await connector.get_columns(schema, table)
        await connector.close()
        return [{"column_name": c.column_name, "data_type": c.data_type} for c in cols]
    except NotImplementedError:
        raise HTTPException(status_code=501, detail=f"{connection.db_type} 커넥터는 아직 지원되지 않습니다.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{connection_id}/info")
async def get_connection_info(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """캐시된 커넥션 정보를 반환한다. 없으면 null cached_at으로 반환."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    if not connection.info_cache:
        return {"cached": False, "cached_at": None}
    data = json.loads(connection.info_cache)
    data["cached"] = True
    data["cached_at"] = connection.info_cached_at.isoformat() if connection.info_cached_at else None
    return data


async def _fetch_and_cache_info(connection: Connection, db: AsyncSession) -> dict[str, Any]:
    """실제 DB에 접속해 테이블/레코드 현황을 조회하고 캐시에 저장한다."""
    from app.connectors.factory import create_connector
    connector = create_connector(connection.db_type, {
        "host": connection.host,
        "port": connection.port,
        "database": connection.database,
        "username": connection.username,
        "password": connection.encrypted_password,
    })
    schemas = await connector.list_schemas()
    total_tables = 0
    total_rows = 0
    schema_details: list[dict] = []
    for schema in schemas:
        tables = await connector.list_tables(schema)
        total_tables += len(tables)
        table_details: list[dict] = []
        for table in tables:
            try:
                row_count = await connector.count_rows(schema, table)
            except Exception:
                row_count = None
            total_rows += row_count or 0
            table_details.append({"name": table, "row_count": row_count})
        schema_details.append({
            "schema": schema,
            "tables": len(tables),
            "table_names": tables,
            "table_details": table_details,
        })
    await connector.close()
    data = {
        "schemas": len(schemas),
        "tables": total_tables,
        "total_rows": total_rows,
        "schema_details": schema_details,
    }
    connection.info_cache = json.dumps(data)
    connection.info_cached_at = datetime.now(timezone.utc)
    await db.commit()
    data["cached"] = True
    data["cached_at"] = connection.info_cached_at.isoformat()
    return data


@router.post("/{connection_id}/info/refresh")
async def refresh_connection_info(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """실제 DB를 조회해 정보를 갱신하고 캐시에 저장한다."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        return await _fetch_and_cache_info(connection, db)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail=f"{connection.db_type} 커넥터는 아직 지원되지 않습니다.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{connection_id}/count")
async def get_table_row_count(
    connection_id: int,
    schema: str,
    table: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """테이블의 전체 행 수를 반환한다."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        from app.connectors.factory import create_connector
        connector = create_connector(connection.db_type, {
            "host": connection.host,
            "port": connection.port,
            "database": connection.database,
            "username": connection.username,
            "password": connection.encrypted_password,
        })
        count = await connector.count_rows(schema, table)
        await connector.close()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
