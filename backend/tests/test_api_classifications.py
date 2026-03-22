import pytest
from app.models.classification import Classification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _insert_classification(db_session, **kwargs) -> Classification:
    defaults = dict(
        scan_id=1, connection_id=1,
        schema_name="mydb", table_name="users",
        column_name="email", pii_type="email",
        confidence=0.8, sensitivity_level="high", status="pending",
    )
    clf = Classification(**{**defaults, **kwargs})
    db_session.add(clf)
    await db_session.commit()
    await db_session.refresh(clf)
    return clf


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_classifications_empty(client):
    resp = await client.get("/api/classifications")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_classifications_returns_all(client, db_session):
    await _insert_classification(db_session, column_name="email")
    await _insert_classification(db_session, column_name="phone", pii_type="phone")

    resp = await client.get("/api/classifications")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_classifications_returns_all_items(client, db_session):
    c1 = await _insert_classification(db_session, column_name="email")
    c2 = await _insert_classification(db_session, column_name="phone", pii_type="phone")

    resp = await client.get("/api/classifications")
    ids = {r["id"] for r in resp.json()}
    assert c1.id in ids
    assert c2.id in ids


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_classification_status_to_confirmed(client, db_session):
    clf = await _insert_classification(db_session)
    resp = await client.put(f"/api/classifications/{clf.id}", json={"status": "confirmed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


async def test_update_classification_status_to_dismissed(client, db_session):
    clf = await _insert_classification(db_session)
    resp = await client.put(f"/api/classifications/{clf.id}", json={"status": "dismissed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


async def test_update_classification_sensitivity_level(client, db_session):
    clf = await _insert_classification(db_session, sensitivity_level="high")
    resp = await client.put(f"/api/classifications/{clf.id}",
                            json={"sensitivity_level": "low"})
    assert resp.status_code == 200
    assert resp.json()["sensitivity_level"] == "low"


async def test_update_classification_multiple_fields(client, db_session):
    clf = await _insert_classification(db_session)
    resp = await client.put(f"/api/classifications/{clf.id}",
                            json={"status": "confirmed", "sensitivity_level": "medium"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["sensitivity_level"] == "medium"


async def test_update_classification_not_found(client):
    resp = await client.put("/api/classifications/9999",
                            json={"status": "confirmed"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_update_classification_preserves_other_fields(client, db_session):
    clf = await _insert_classification(db_session, pii_type="phone", confidence=0.75)
    resp = await client.put(f"/api/classifications/{clf.id}", json={"status": "confirmed"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_type"] == "phone"
    assert data["confidence"] == 0.75
