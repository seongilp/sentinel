import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.scan import Scan, ScanCreate
from app.models.connection import Connection
from app.models.classification import Classification
from app.models.rule import Rule
from app.connectors.factory import create_connector
from app.detectors.orchestrator import DetectionOrchestrator


async def run_scan(scan_id: int) -> None:
    """BackgroundTask에서 실행되는 실제 PII 스캔 함수"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        if not scan:
            return

        conn_result = await db.execute(select(Connection).where(Connection.id == scan.connection_id))
        connection = conn_result.scalar_one_or_none()
        if not connection:
            scan.status = "failed"
            scan.error_message = "Connection not found"
            await db.commit()
            return

        rule_result = await db.execute(select(Rule).where(Rule.is_active == True))
        rules = list(rule_result.scalars().all())

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        await db.commit()

        connector = None
        try:
            connector = create_connector(connection.db_type, {
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "username": connection.username,
                "password": connection.encrypted_password,
            })

            orchestrator = DetectionOrchestrator(rules=rules)

            if scan.target_schemas:
                schemas = json.loads(scan.target_schemas)
            else:
                schemas = await connector.list_schemas()
                excluded = {"information_schema", "performance_schema", "mysql", "sys", "pg_catalog"}
                schemas = [s for s in schemas if s.lower() not in excluded]

            total_tables = 0
            total_columns = 0
            pii_found = 0

            for schema in schemas:
                try:
                    tables = await connector.list_tables(schema)
                except Exception:
                    continue

                for table in tables:
                    total_tables += 1
                    try:
                        columns = await connector.get_columns(schema, table)
                    except Exception:
                        continue

                    for col_info in columns:
                        total_columns += 1

                        detections = orchestrator.detect_by_column_name(col_info)

                        try:
                            sample = await connector.sample_column(
                                schema, table, col_info.column_name, limit=scan.sample_size
                            )
                            detections = orchestrator.detect_with_samples(col_info, sample.values, existing=detections)
                        except Exception:
                            pass

                        final = [d for d in detections if d.confidence >= scan.confidence_threshold]

                        for detection in final:
                            if detection.confidence >= 0.8:
                                sensitivity = "high"
                            elif detection.confidence >= 0.6:
                                sensitivity = "medium"
                            else:
                                sensitivity = "low"

                            classification = Classification(
                                scan_id=scan_id,
                                connection_id=connection.id,
                                schema_name=schema,
                                table_name=table,
                                column_name=col_info.column_name,
                                data_type=col_info.data_type,
                                pii_type=detection.pii_type,
                                confidence=detection.confidence,
                                sensitivity_level=sensitivity,
                                status="pending",
                                detector=detection.detector,
                                evidence=detection.evidence,
                            )
                            db.add(classification)
                            pii_found += 1

            await db.commit()

            scan.status = "completed"
            scan.completed_at = datetime.now(timezone.utc)
            scan.total_tables = total_tables
            scan.total_columns = total_columns
            scan.pii_columns_found = pii_found
            await db.commit()
            from app.services.audit_service import log as audit_log
            await audit_log(db, "scan.completed", "scan", scan_id, {
                "total_tables": total_tables,
                "total_columns": total_columns,
                "pii_columns_found": pii_found,
            }, menu="scans", result="success")

        except Exception as e:
            if scan:
                scan.status = "failed"
                scan.error_message = str(e)[:1000]
                scan.completed_at = datetime.now(timezone.utc)
                await db.commit()
                from app.services.audit_service import log as audit_log
                await audit_log(db, "scan.failed", "scan", scan_id, {
                    "error": str(e)[:500],
                }, menu="scans", result="failure")
        finally:
            if connector:
                await connector.close()


async def get_all(db: AsyncSession) -> list[Scan]:
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, scan_id: int) -> Scan | None:
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, payload: ScanCreate) -> Scan:
    scan = Scan(
        connection_id=payload.connection_id,
        status="pending",
        target_schemas=json.dumps(payload.target_schemas) if payload.target_schemas else None,
        sample_size=payload.sample_size,
        confidence_threshold=payload.confidence_threshold,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def cancel(db: AsyncSession, scan: Scan) -> Scan:
    scan.status = "cancelled"
    await db.commit()
    await db.refresh(scan)
    return scan
