import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Autouse: prevent run_scan background task from changing scan status
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_run_scan():
    with patch("app.api.scans.run_scan", new=AsyncMock(return_value=None)):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_connection(client):
    resp = await client.post("/api/connections", json={
        "name": "Test DB", "db_type": "mysql",
        "host": "localhost", "port": 3306,
        "database": "mydb", "username": "root",
    })
    return resp.json()["id"]


async def _create_scan(client, connection_id: int, **kwargs):
    payload = {"connection_id": connection_id, **kwargs}
    return await client.post("/api/scans", json=payload)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_scans_empty(client):
    resp = await client.get("/api/scans")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_scans_returns_all(client):
    conn_id = await _create_connection(client)
    await _create_scan(client, conn_id)
    await _create_scan(client, conn_id)
    resp = await client.get("/api/scans")
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_scan_returns_pending(client):
    conn_id = await _create_connection(client)
    resp = await _create_scan(client, conn_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["connection_id"] == conn_id
    assert "id" in data


async def test_create_scan_default_values(client):
    conn_id = await _create_connection(client)
    resp = await _create_scan(client, conn_id)
    data = resp.json()
    assert data["sample_size"] == 100
    assert data["confidence_threshold"] == 0.5


async def test_create_scan_custom_values(client):
    conn_id = await _create_connection(client)
    resp = await _create_scan(client, conn_id,
                              sample_size=50,
                              confidence_threshold=0.7,
                              target_schemas=["mydb"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["sample_size"] == 50
    assert data["confidence_threshold"] == 0.7


async def test_create_scan_creates_audit_log(client, db_session):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    conn_id = await _create_connection(client)
    await _create_scan(client, conn_id)

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "scan.created")
    )
    assert len(result.scalars().all()) == 1


async def test_create_scan_missing_connection_id(client):
    resp = await client.post("/api/scans", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

async def test_get_scan_success(client):
    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    resp = await client.get(f"/api/scans/{scan_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == scan_id


async def test_get_scan_not_found(client):
    resp = await client.get("/api/scans/9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def test_cancel_pending_scan(client):
    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    resp = await client.post(f"/api/scans/{scan_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_cancel_scan_not_found(client):
    resp = await client.post("/api/scans/9999/cancel")
    assert resp.status_code == 404


async def test_cancel_completed_scan_fails(client, db_session):
    from sqlalchemy import select
    from app.models.scan import Scan

    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    # Force-complete the scan directly
    result = await db_session.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one()
    scan.status = "completed"
    await db_session.commit()

    resp = await client.post(f"/api/scans/{scan_id}/cancel")
    assert resp.status_code == 400
    assert "completed" in resp.json()["detail"].lower()


async def test_cancel_cancelled_scan_fails(client):
    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    await client.post(f"/api/scans/{scan_id}/cancel")
    resp = await client.post(f"/api/scans/{scan_id}/cancel")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

async def test_get_scan_results_empty(client):
    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    resp = await client.get(f"/api/scans/{scan_id}/results")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_scan_results_with_data(client, db_session):
    from app.models.classification import Classification

    conn_id = await _create_connection(client)
    create_resp = await _create_scan(client, conn_id)
    scan_id = create_resp.json()["id"]

    # Insert a classification directly
    clf = Classification(
        scan_id=scan_id, connection_id=conn_id,
        schema_name="mydb", table_name="users",
        column_name="email", pii_type="email",
        confidence=0.8, sensitivity_level="high", status="pending",
    )
    db_session.add(clf)
    await db_session.commit()

    resp = await client.get(f"/api/scans/{scan_id}/results")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["pii_type"] == "email"
    assert results[0]["confidence"] == 0.8
