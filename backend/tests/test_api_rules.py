import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CUSTOM_RULE = {
    "name": "Custom Email Rule",
    "pii_type": "email",
    "detection_method": "column_name",
    "column_patterns": ["email", "e_mail"],
    "is_active": True,
}


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_rules_includes_builtin(client, builtin_rules):
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == len(builtin_rules)
    assert all(r["is_builtin"] for r in rules)


async def test_list_rules_sorted_by_name(client, builtin_rules):
    resp = await client.get("/api/rules")
    names = [r["name"] for r in resp.json()]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_custom_rule_success(client):
    resp = await client.post("/api/rules", json=_CUSTOM_RULE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Custom Email Rule"
    assert data["pii_type"] == "email"
    assert data["is_builtin"] is False
    assert data["is_active"] is True
    assert "id" in data


async def test_create_rule_with_data_patterns(client):
    rule = {**_CUSTOM_RULE, "detection_method": "regex",
            "data_patterns": [r"\d{6}-[1-4]\d{6}"]}
    resp = await client.post("/api/rules", json=rule)
    assert resp.status_code == 201


async def test_create_rule_missing_required_fields(client):
    resp = await client.post("/api/rules", json={"name": "Incomplete"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

async def test_get_rule_success(client):
    create_resp = await client.post("/api/rules", json=_CUSTOM_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/api/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rule_id


async def test_get_rule_not_found(client):
    resp = await client.get("/api/rules/9999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_rule_name(client):
    create_resp = await client.post("/api/rules", json=_CUSTOM_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.put(f"/api/rules/{rule_id}", json={"name": "Renamed Rule"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Rule"
    assert resp.json()["pii_type"] == "email"  # unchanged


async def test_update_rule_toggle_active(client):
    create_resp = await client.post("/api/rules", json=_CUSTOM_RULE)
    rule_id = create_resp.json()["id"]

    resp = await client.put(f"/api/rules/{rule_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_update_rule_not_found(client):
    resp = await client.put("/api/rules/9999", json={"name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_custom_rule_success(client):
    create_resp = await client.post("/api/rules", json=_CUSTOM_RULE)
    rule_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/rules/{rule_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/rules/{rule_id}")
    assert get_resp.status_code == 404


async def test_delete_builtin_rule_fails(client, builtin_rules):
    rules = (await client.get("/api/rules")).json()
    builtin = next(r for r in rules if r["is_builtin"])

    resp = await client.delete(f"/api/rules/{builtin['id']}")
    assert resp.status_code == 400
    assert "built-in" in resp.json()["detail"].lower()


async def test_delete_rule_not_found(client):
    resp = await client.delete("/api/rules/9999")
    assert resp.status_code == 404
