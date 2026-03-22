import pytest
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAYLOAD = {
    "name": "Test MySQL",
    "db_type": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "mydb",
    "username": "root",
    "password": "secret",
}


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_connections_empty(client):
    resp = await client.get("/api/connections")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_connections_returns_all(client):
    await client.post("/api/connections", json=_PAYLOAD)
    await client.post("/api/connections", json={**_PAYLOAD, "name": "Second"})
    resp = await client.get("/api/connections")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_connection_success(client):
    resp = await client.post("/api/connections", json=_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test MySQL"
    assert data["db_type"] == "mysql"
    assert data["host"] == "localhost"
    assert data["port"] == 3306
    assert data["database"] == "mydb"
    assert data["username"] == "root"
    assert "id" in data
    # Password must not be returned
    assert "password" not in data
    assert "encrypted_password" not in data


async def test_create_connection_missing_required_field(client):
    bad = {k: v for k, v in _PAYLOAD.items() if k != "host"}
    resp = await client.post("/api/connections", json=bad)
    assert resp.status_code == 422


async def test_create_connection_creates_audit_log(client, db_session):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    await client.post("/api/connections", json=_PAYLOAD)
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "connection.created")
    )
    logs = result.scalars().all()
    assert len(logs) == 1


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

async def test_get_connection_success(client):
    create_resp = await client.post("/api/connections", json=_PAYLOAD)
    conn_id = create_resp.json()["id"]

    resp = await client.get(f"/api/connections/{conn_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == conn_id


async def test_get_connection_not_found(client):
    resp = await client.get("/api/connections/9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_connection_success(client):
    create_resp = await client.post("/api/connections", json=_PAYLOAD)
    conn_id = create_resp.json()["id"]

    resp = await client.put(f"/api/connections/{conn_id}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    # Other fields unchanged
    assert resp.json()["db_type"] == "mysql"


async def test_update_connection_not_found(client):
    resp = await client.put("/api/connections/9999", json={"name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_connection_success(client):
    create_resp = await client.post("/api/connections", json=_PAYLOAD)
    conn_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/connections/{conn_id}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/connections/{conn_id}")
    assert get_resp.status_code == 404


async def test_delete_connection_not_found(client):
    resp = await client.delete("/api/connections/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Check (no-save connection test)
# ---------------------------------------------------------------------------

async def test_check_connection_not_implemented_for_oracle(client):
    payload = {**_PAYLOAD, "db_type": "oracle", "port": 1521}
    resp = await client.post("/api/connections/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Phase 2" in data["message"]


async def test_check_connection_not_implemented_for_mongodb(client):
    payload = {**_PAYLOAD, "db_type": "mongodb", "port": 27017}
    resp = await client.post("/api/connections/check", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_check_connection_mysql_success(client):
    mock_connector = AsyncMock()
    mock_connector.test_connection.return_value = True
    mock_connector.close = AsyncMock()

    with patch("app.connectors.factory.create_connector", return_value=mock_connector):
        resp = await client.post("/api/connections/check", json=_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_check_connection_mysql_failure(client):
    mock_connector = AsyncMock()
    mock_connector.test_connection.side_effect = Exception("Connection refused")
    mock_connector.close = AsyncMock()

    with patch("app.connectors.factory.create_connector", return_value=mock_connector):
        resp = await client.post("/api/connections/check", json=_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# Test saved connection
# ---------------------------------------------------------------------------

async def test_test_saved_connection_success(client):
    create_resp = await client.post("/api/connections", json=_PAYLOAD)
    conn_id = create_resp.json()["id"]

    resp = await client.post(f"/api/connections/{conn_id}/test")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_saved_connection_not_found(client):
    resp = await client.post("/api/connections/9999/test")
    assert resp.status_code == 404
