from __future__ import annotations


def _tenant_headers(tenant_id: str) -> dict[str, str]:
    return {"x-tenant-id": tenant_id, "Idempotency-Key": f"idem_{tenant_id}"}


def test_projects_crud_flow(client):
    create = client.post(
        "/api/v1/projects",
        headers=_tenant_headers("tenant_proj"),
        json={"project_code": "PRJ-001", "name": "Project One", "ruleset_version": "v1.2.0"},
    )
    assert create.status_code == 201
    project_id = create.json()["data"]["project_id"]

    listed = client.get("/api/v1/projects", headers={"x-tenant-id": "tenant_proj"})
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    fetched = client.get(f"/api/v1/projects/{project_id}", headers={"x-tenant-id": "tenant_proj"})
    assert fetched.status_code == 200
    assert fetched.json()["data"]["project_code"] == "PRJ-001"

    updated = client.put(
        f"/api/v1/projects/{project_id}",
        headers={"x-tenant-id": "tenant_proj"},
        json={"name": "Project One Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Project One Updated"

    deleted = client.delete(f"/api/v1/projects/{project_id}", headers={"x-tenant-id": "tenant_proj"})
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True


def test_suppliers_crud_flow(client):
    create = client.post(
        "/api/v1/suppliers",
        headers=_tenant_headers("tenant_sup"),
        json={"supplier_code": "SUP-001", "name": "Supplier One", "qualification": {"tier": "A"}},
    )
    assert create.status_code == 201
    supplier_id = create.json()["data"]["supplier_id"]

    listed = client.get("/api/v1/suppliers", headers={"x-tenant-id": "tenant_sup"})
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    fetched = client.get(f"/api/v1/suppliers/{supplier_id}", headers={"x-tenant-id": "tenant_sup"})
    assert fetched.status_code == 200
    assert fetched.json()["data"]["supplier_code"] == "SUP-001"

    updated = client.put(
        f"/api/v1/suppliers/{supplier_id}",
        headers={"x-tenant-id": "tenant_sup"},
        json={"name": "Supplier One Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Supplier One Updated"

    deleted = client.delete(f"/api/v1/suppliers/{supplier_id}", headers={"x-tenant-id": "tenant_sup"})
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True


def test_rule_packs_crud_flow(client):
    create = client.post(
        "/api/v1/rules",
        headers=_tenant_headers("tenant_rule"),
        json={"rule_pack_version": "v2.0.0", "name": "Ruleset v2", "rules": {"max_score": 100}},
    )
    assert create.status_code == 201

    listed = client.get("/api/v1/rules", headers={"x-tenant-id": "tenant_rule"})
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1

    fetched = client.get("/api/v1/rules/v2.0.0", headers={"x-tenant-id": "tenant_rule"})
    assert fetched.status_code == 200
    assert fetched.json()["data"]["name"] == "Ruleset v2"

    updated = client.put(
        "/api/v1/rules/v2.0.0",
        headers={"x-tenant-id": "tenant_rule"},
        json={"status": "inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "inactive"

    deleted = client.delete("/api/v1/rules/v2.0.0", headers={"x-tenant-id": "tenant_rule"})
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
