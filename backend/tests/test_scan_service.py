"""Integration tests for run_scan() — uses real test DB, mocks the connector."""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.connectors.base import ColumnInfo, SampleData
from app.models.connection import Connection
from app.models.scan import Scan
from app.models.rule import Rule
from app.models.classification import Classification
from app.services.scan_service import run_scan
from app.database import AsyncSessionLocal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_connection(db_session) -> Connection:
    conn = Connection(
        name="TestDB", db_type="mysql",
        host="localhost", port=3306,
        database="mydb", username="root",
    )
    db_session.add(conn)
    await db_session.commit()
    await db_session.refresh(conn)
    return conn


async def _make_scan(db_session, connection_id: int, **kwargs) -> Scan:
    defaults = dict(status="pending", sample_size=10, confidence_threshold=0.5)
    scan = Scan(connection_id=connection_id, **{**defaults, **kwargs})
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)
    return scan


async def _make_rule(db_session, pii_type="email") -> Rule:
    rule = Rule(
        name=f"{pii_type} rule", pii_type=pii_type,
        detection_method="column_name", is_builtin=False, is_active=True,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


def _read_scan(scan_id: int):
    """Helper: read scan from DB using a fresh session (avoids stale cache)."""
    import asyncio

    async def _read():
        async with AsyncSessionLocal() as s:
            result = await s.execute(select(Scan).where(Scan.id == scan_id))
            return result.scalar_one_or_none()

    return asyncio.get_event_loop().run_until_complete(_read())


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

async def test_run_scan_completes_with_pii_found(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)
    await _make_rule(db_session, "email")

    col_email = ColumnInfo(schema_name="mydb", table_name="users",
                           column_name="email", data_type="varchar")
    sample_data = SampleData.from_list(col_email, ["alice@example.com", "bob@test.com"])

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = ["mydb"]
    mock_connector.list_tables.return_value = ["users"]
    mock_connector.get_columns.return_value = [col_email]
    mock_connector.sample_column.return_value = sample_data
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        updated = result.scalar_one()
        assert updated.status == "completed"
        assert updated.total_tables == 1
        assert updated.total_columns == 1
        assert updated.pii_columns_found >= 1
        assert updated.completed_at is not None

        clf_result = await s.execute(
            select(Classification).where(Classification.scan_id == scan.id)
        )
        classifications = clf_result.scalars().all()
        assert len(classifications) >= 1
        assert classifications[0].pii_type == "email"
        assert classifications[0].column_name == "email"


async def test_run_scan_no_pii_found_still_completes(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    col = ColumnInfo(schema_name="mydb", table_name="orders",
                     column_name="order_id", data_type="int")
    sample_data = SampleData.from_list(col, ["1001", "1002", "1003"])

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = ["mydb"]
    mock_connector.list_tables.return_value = ["orders"]
    mock_connector.get_columns.return_value = [col]
    mock_connector.sample_column.return_value = sample_data
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        updated = result.scalar_one()
        assert updated.status == "completed"
        assert updated.pii_columns_found == 0


async def test_run_scan_sensitivity_levels_assigned_correctly(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id, confidence_threshold=0.3)

    col = ColumnInfo(schema_name="mydb", table_name="users",
                     column_name="email", data_type="varchar")
    # 10/10 samples → regex confidence 1.0, combined > 0.8 → high
    sample_data = SampleData.from_list(col, ["a@b.com"] * 10)

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = ["mydb"]
    mock_connector.list_tables.return_value = ["users"]
    mock_connector.get_columns.return_value = [col]
    mock_connector.sample_column.return_value = sample_data
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        clf_result = await s.execute(
            select(Classification).where(Classification.scan_id == scan.id)
        )
        classifications = clf_result.scalars().all()
        email_clf = next((c for c in classifications if c.pii_type == "email"), None)
        assert email_clf is not None
        assert email_clf.sensitivity_level == "high"


async def test_run_scan_excludes_system_schemas(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = [
        "information_schema", "performance_schema", "mydb"
    ]
    mock_connector.list_tables.return_value = ["users"]
    mock_connector.get_columns.return_value = []
    mock_connector.sample_column.return_value = SampleData.from_list(
        ColumnInfo("mydb", "users", "id", "int"), []
    )
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    # list_tables should only be called once (for "mydb", not system schemas)
    mock_connector.list_tables.assert_called_once_with("mydb")


async def test_run_scan_uses_target_schemas_when_provided(db_session):
    import json
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    # Manually set target_schemas
    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        s_obj = result.scalar_one()
        s_obj.target_schemas = json.dumps(["custom_schema"])
        await s.commit()

    mock_connector = AsyncMock()
    mock_connector.list_tables.return_value = []
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    # list_schemas should NOT be called — target_schemas is used instead
    mock_connector.list_schemas.assert_not_called()
    mock_connector.list_tables.assert_called_once_with("custom_schema")


async def test_run_scan_connector_closed_on_success(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = []
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    mock_connector.close.assert_called_once()


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

async def test_run_scan_scan_not_found(db_session):
    # Should return without raising
    await run_scan(scan_id=9999)


async def test_run_scan_connection_not_found(db_session):
    # Scan exists but connection_id points to nothing
    scan = await _make_scan(db_session, connection_id=9999)

    await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        updated = result.scalar_one()
        assert updated.status == "failed"
        assert "not found" in (updated.error_message or "").lower()


async def test_run_scan_connector_exception_marks_failed(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    mock_connector = AsyncMock()
    mock_connector.list_schemas.side_effect = Exception("Connection timed out")
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        updated = result.scalar_one()
        assert updated.status == "failed"
        assert "Connection timed out" in (updated.error_message or "")


async def test_run_scan_connector_closed_on_exception(db_session):
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    mock_connector = AsyncMock()
    mock_connector.list_schemas.side_effect = RuntimeError("Boom")
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    mock_connector.close.assert_called_once()


async def test_run_scan_table_error_skipped_continues(db_session):
    """A broken table should be skipped, scan still completes."""
    conn = await _make_connection(db_session)
    scan = await _make_scan(db_session, conn.id)

    col = ColumnInfo("mydb", "good_table", "email", "varchar")
    sample_data = SampleData.from_list(col, ["a@b.com"])

    mock_connector = AsyncMock()
    mock_connector.list_schemas.return_value = ["mydb"]
    mock_connector.list_tables.return_value = ["broken_table", "good_table"]
    # First call raises, second call succeeds
    mock_connector.get_columns.side_effect = [
        Exception("Table access denied"),
        [col],
    ]
    mock_connector.sample_column.return_value = sample_data
    mock_connector.close = AsyncMock()

    with patch("app.services.scan_service.create_connector", return_value=mock_connector):
        await run_scan(scan.id)

    async with AsyncSessionLocal() as s:
        result = await s.execute(select(Scan).where(Scan.id == scan.id))
        updated = result.scalar_one()
        assert updated.status == "completed"
