from typing import Any
import io
import csv
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.dependencies import get_db
from app.models.classification import Classification

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pii-inventory")
async def get_pii_inventory(
    db: AsyncSession = Depends(get_db),
    connection_id: int | None = Query(default=None),
    scan_id: int | None = Query(default=None),
) -> list[dict[str, Any]]:
    query = select(Classification).where(Classification.status != "dismissed")
    if connection_id is not None:
        query = query.where(Classification.connection_id == connection_id)
    if scan_id is not None:
        query = query.where(Classification.scan_id == scan_id)
    result = await db.execute(query.order_by(Classification.schema_name, Classification.table_name))
    return [
        {
            "id": c.id,
            "scan_id": c.scan_id,
            "connection_id": c.connection_id,
            "schema_name": c.schema_name,
            "table_name": c.table_name,
            "column_name": c.column_name,
            "pii_type": c.pii_type,
            "confidence": c.confidence,
            "sensitivity_level": c.sensitivity_level,
            "status": c.status,
        }
        for c in result.scalars().all()
    ]


@router.get("/export")
async def export_report(
    format: str = Query(default="csv", description="Export format: json|csv|xlsx"),
    connection_id: int | None = Query(default=None),
    scan_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(Classification).where(Classification.status != "dismissed")
    if connection_id is not None:
        query = query.where(Classification.connection_id == connection_id)
    if scan_id is not None:
        query = query.where(Classification.scan_id == scan_id)
    result = await db.execute(query.order_by(Classification.schema_name, Classification.table_name))
    rows = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "schema_name", "table_name", "column_name", "data_type",
            "pii_type", "confidence", "sensitivity_level", "status", "scan_id",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "schema_name": r.schema_name,
                "table_name": r.table_name,
                "column_name": r.column_name,
                "data_type": r.data_type or "",
                "pii_type": r.pii_type,
                "confidence": round(r.confidence, 3),
                "sensitivity_level": r.sensitivity_level,
                "status": r.status,
                "scan_id": r.scan_id,
            })
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pii_inventory.csv"},
        )

    elif format == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "PII Inventory"
        ws.append(["Schema", "Table", "Column", "Data Type", "PII Type", "Confidence", "Sensitivity", "Status", "Scan ID"])
        for r in rows:
            ws.append([
                r.schema_name, r.table_name, r.column_name, r.data_type or "",
                r.pii_type, round(r.confidence, 3),
                r.sensitivity_level, r.status, r.scan_id,
            ])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=pii_inventory.xlsx"},
        )

    # default: json
    return [
        {
            "schema_name": r.schema_name,
            "table_name": r.table_name,
            "column_name": r.column_name,
            "pii_type": r.pii_type,
            "confidence": r.confidence,
            "sensitivity_level": r.sensitivity_level,
            "status": r.status,
        }
        for r in rows
    ]


@router.get("/daily-trend")
async def get_daily_trend(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, le=90),
    hours: int | None = Query(default=None, le=24),
    connection_id: int | None = Query(default=None),
) -> list[dict[str, Any]]:
    if hours is not None:
        return await _hourly_trend(db, hours, connection_id)

    start_date = date.today() - timedelta(days=days - 1)
    filters = "status != 'dismissed' AND date(created_at) >= :start_date"
    params: dict[str, Any] = {"start_date": start_date.isoformat()}
    if connection_id is not None:
        filters += " AND connection_id = :conn_id"
        params["conn_id"] = connection_id

    sql = text(f"""
        SELECT
            strftime('%Y-%m-%d', created_at) AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN sensitivity_level = 'high'   THEN 1 ELSE 0 END) AS high,
            SUM(CASE WHEN sensitivity_level = 'medium' THEN 1 ELSE 0 END) AS medium,
            SUM(CASE WHEN sensitivity_level = 'low'    THEN 1 ELSE 0 END) AS low
        FROM classifications
        WHERE {filters}
        GROUP BY day
        ORDER BY day
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()
    date_map = {r[0]: {"total": r[1], "high": r[2], "medium": r[3], "low": r[4]} for r in rows}

    data = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        entry = date_map.get(d, {"total": 0, "high": 0, "medium": 0, "low": 0})
        data.append({"date": d, **entry})
    return data


async def _hourly_trend(
    db: AsyncSession,
    hours: int,
    connection_id: int | None,
) -> list[dict[str, Any]]:
    from datetime import datetime

    now = datetime.utcnow()

    if hours == 1:
        # 10-minute buckets, last 60 minutes
        step_minutes = 10
        n_slots = 6
        start_dt = now - timedelta(hours=1)
        slot_expr = (
            "strftime('%Y-%m-%d %H:', created_at) || "
            "CASE (cast(strftime('%M', created_at) as integer) / 10) "
            "WHEN 0 THEN '00' WHEN 1 THEN '10' WHEN 2 THEN '20' "
            "WHEN 3 THEN '30' WHEN 4 THEN '40' ELSE '50' END"
        )
    else:
        # 1-hour buckets, last 24 hours
        step_minutes = 60
        n_slots = 24
        start_dt = now - timedelta(hours=24)
        slot_expr = "strftime('%Y-%m-%d %H:00', created_at)"

    filters = "status != 'dismissed' AND created_at >= :start_dt"
    params: dict[str, Any] = {"start_dt": start_dt.strftime("%Y-%m-%d %H:%M:%S")}
    if connection_id is not None:
        filters += " AND connection_id = :conn_id"
        params["conn_id"] = connection_id

    sql = text(f"""
        SELECT
            {slot_expr} AS slot,
            COUNT(*) AS total,
            SUM(CASE WHEN sensitivity_level = 'high'   THEN 1 ELSE 0 END) AS high,
            SUM(CASE WHEN sensitivity_level = 'medium' THEN 1 ELSE 0 END) AS medium,
            SUM(CASE WHEN sensitivity_level = 'low'    THEN 1 ELSE 0 END) AS low
        FROM classifications
        WHERE {filters}
        GROUP BY slot
        ORDER BY slot
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()
    slot_map = {r[0]: {"total": r[1], "high": r[2], "medium": r[3], "low": r[4]} for r in rows}

    data = []
    for i in range(n_slots):
        dt = start_dt + timedelta(minutes=step_minutes * i)
        if hours == 1:
            bucket = (dt.minute // 10) * 10
            slot_key = dt.strftime(f"%Y-%m-%d %H:{bucket:02d}")
            label = dt.strftime(f"%H:{bucket:02d}")
        else:
            slot_key = dt.strftime("%Y-%m-%d %H:00")
            label = dt.strftime("%H:00")
        entry = slot_map.get(slot_key, {"total": 0, "high": 0, "medium": 0, "low": 0})
        data.append({"date": label, **entry})
    return data
