import pytest
from app.models.connection import Connection
from app.models.scan import Scan
from app.models.classification import Classification


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

async def test_summary_all_zeros(client):
    resp = await client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_connections"] == 0
    assert data["total_scans"] == 0
    assert data["pii_columns"] == 0
    assert data["recent_scans"] == []


async def test_summary_counts_connections(client, db_session):
    db_session.add(Connection(
        name="DB1", db_type="mysql", host="h", port=3306,
        database="d", username="u",
    ))
    db_session.add(Connection(
        name="DB2", db_type="mysql", host="h", port=3306,
        database="d", username="u",
    ))
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    assert resp.json()["total_connections"] == 2


async def test_summary_counts_scans(client, db_session):
    db_session.add(Scan(connection_id=1, status="completed",
                        sample_size=100, confidence_threshold=0.5))
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    assert resp.json()["total_scans"] == 1


async def test_summary_counts_pii_columns_excludes_dismissed(client, db_session):
    for status in ("pending", "confirmed", "dismissed"):
        db_session.add(Classification(
            scan_id=1, connection_id=1,
            schema_name="s", table_name="t", column_name=f"col_{status}",
            pii_type="email", confidence=0.8,
            sensitivity_level="high", status=status,
        ))
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    # Only pending + confirmed counted (dismissed excluded)
    assert resp.json()["pii_columns"] == 2


async def test_summary_recent_scans_limit_5(client, db_session):
    for i in range(7):
        db_session.add(Scan(connection_id=1, status="completed",
                            sample_size=100, confidence_threshold=0.5))
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    assert len(resp.json()["recent_scans"]) == 5


async def test_summary_recent_scans_contains_required_fields(client, db_session):
    db_session.add(Scan(connection_id=42, status="completed",
                        sample_size=100, confidence_threshold=0.5))
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    scan = resp.json()["recent_scans"][0]
    assert "id" in scan
    assert "connection_id" in scan
    assert "status" in scan
    assert "created_at" in scan


# ---------------------------------------------------------------------------
# Recent Activity
# ---------------------------------------------------------------------------

async def test_recent_activity_empty(client):
    resp = await client.get("/api/dashboard/recent-activity")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_recent_activity_populated_by_connection_create(client):
    # Creating a connection via API triggers audit log
    await client.post("/api/connections", json={
        "name": "TestConn", "db_type": "mysql",
        "host": "h", "port": 3306,
        "database": "d", "username": "u",
    })

    resp = await client.get("/api/dashboard/recent-activity")
    assert resp.status_code == 200
    activity = resp.json()
    assert len(activity) >= 1
    assert any(a["action"] == "connection.created" for a in activity)


async def test_recent_activity_limit_20(client, db_session):
    from app.models.audit_log import AuditLog

    for i in range(25):
        db_session.add(AuditLog(action="test.action", entity_type="test", entity_id=i))
    await db_session.commit()

    resp = await client.get("/api/dashboard/recent-activity")
    assert len(resp.json()) == 20


async def test_recent_activity_contains_required_fields(client):
    await client.post("/api/connections", json={
        "name": "Conn", "db_type": "mysql",
        "host": "h", "port": 3306,
        "database": "d", "username": "u",
    })

    resp = await client.get("/api/dashboard/recent-activity")
    item = resp.json()[0]
    assert "id" in item
    assert "action" in item
    assert "created_at" in item
