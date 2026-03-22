import asyncio
import json
import logging
import re
from datetime import datetime, timezone


from app.database import AsyncSessionLocal
from app.models.connection import Connection
from app.models.deep_inspect import DeepInspectJob, DeepInspectMatch
from app.connectors.factory import create_connector

logger = logging.getLogger(__name__)

MAX_STORED_MATCHES = 50_000  # cap to prevent DB bloat

# Built-in PII patterns (subset of regex_pattern.py)
_PII_PATTERNS: list[tuple[str, str, re.Pattern]] = []


def _load_patterns() -> None:
    from pathlib import Path
    builtin_path = Path(__file__).parent.parent / "rules" / "builtin.json"
    if not builtin_path.exists():
        return
    rules = json.loads(builtin_path.read_text())
    for rule in rules:
        if not rule.get("is_active", True):
            continue
        for pat in rule.get("data_patterns", []):
            try:
                _PII_PATTERNS.append((rule["pii_type"], pat, re.compile(pat)))
            except re.error:
                pass


_load_patterns()


def _detect_value(value: str) -> list[tuple[str, float]]:
    """Returns list of (pii_type, confidence) for a single value."""
    if not value or len(value) < 4:
        return []
    results = []
    for pii_type, _, pattern in _PII_PATTERNS:
        if pattern.search(value):
            results.append((pii_type, 0.85))
    return results


async def run_job(job_id: int) -> None:
    """Background task: full table scan with batch processing."""
    async with AsyncSessionLocal() as db:
        job = await db.get(DeepInspectJob, job_id)
        if job is None:
            return

        # Mark as running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # Get connection
            conn_row = await db.get(Connection, job.connection_id)
            if conn_row is None:
                raise ValueError(f"Connection {job.connection_id} not found")

            connector = create_connector(conn_row.db_type, {
                "host": conn_row.host,
                "port": conn_row.port,
                "database": conn_row.database,
                "username": conn_row.username,
                "password": conn_row.encrypted_password,
            })

            columns = json.loads(job.columns) if job.columns else []

            # If no columns specified, get all
            if not columns:
                col_infos = await connector.get_columns(job.schema_name, job.table_name)
                columns = [c.column_name for c in col_infos]
                job.columns = json.dumps(columns)
                await db.commit()

            # Count total rows
            total = await connector.count_rows(job.schema_name, job.table_name)
            job.total_rows = total
            await db.commit()

            offset = 0
            scanned = 0
            match_count = 0
            batch_size = job.batch_size

            while offset < total:
                # Check for cancellation
                await db.refresh(job)
                if job.status == "cancelled":
                    break

                rows = await connector.fetch_rows(
                    job.schema_name, job.table_name, columns, batch_size, offset
                )
                if not rows:
                    break

                new_matches: list[DeepInspectMatch] = []
                for row_idx, row in enumerate(rows):
                    for col_idx, value in enumerate(row):
                        if value is None:
                            continue
                        str_value = str(value)
                        detections = _detect_value(str_value)
                        for pii_type, confidence in detections:
                            if match_count >= MAX_STORED_MATCHES:
                                break
                            new_matches.append(DeepInspectMatch(
                                job_id=job_id,
                                row_offset=offset + row_idx,
                                column_name=columns[col_idx],
                                pii_type=pii_type,
                                matched_value=str_value[:500],
                                confidence=confidence,
                            ))
                            match_count += 1

                if new_matches:
                    db.add_all(new_matches)

                scanned += len(rows)
                job.scanned_rows = scanned
                job.pii_matches = match_count
                await db.commit()

                offset += batch_size

                # Throttle: small sleep to avoid overwhelming the source DB
                await asyncio.sleep(0.01)

            await connector.close()

            if job.status != "cancelled":
                job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            logger.error("Deep inspect job %d failed: %s", job_id, e, exc_info=True)
            job.status = "failed"
            job.error_message = str(e)[:1000]
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
