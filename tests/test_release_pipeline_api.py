from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.store import store


def _all_gates_true() -> dict:
    return {
        "quality": True,
        "performance": True,
        "security": True,
        "cost": True,
        "rollout": True,
        "rollback": True,
        "ops": True,
    }


def test_release_pipeline_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/release/pipeline/execute",
        json={"release_id": "rel_p5_001", "replay_passed": True, "gate_results": _all_gates_true()},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_release_pipeline_blocks_when_readiness_fails(client):
    resp = client.post(
        "/api/v1/internal/release/pipeline/execute",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_pipeline"},
        json={
            "release_id": "rel_p5_002",
            "replay_passed": False,
            "gate_results": _all_gates_true(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["admitted"] is False
    assert data["stage"] == "release_blocked"
    assert "REPLAY_E2E_FAILED" in data["failed_checks"]
    assert data["readiness_required"] is True


def test_release_pipeline_ready_when_gates_and_replay_pass(client):
    resp = client.post(
        "/api/v1/internal/release/pipeline/execute",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_pipeline"},
        json={
            "release_id": "rel_p5_003",
            "replay_passed": True,
            "gate_results": _all_gates_true(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["admitted"] is True
    assert data["stage"] == "release_ready"
    assert data["canary"]["ratio"] >= 0
    assert data["rollback"]["max_minutes"] >= 1


def test_release_pipeline_can_bypass_readiness_when_disabled(monkeypatch):
    client = TestClient(create_app())
    original = store.p6_readiness_required
    try:
        store.p6_readiness_required = False
        resp = client.post(
            "/api/v1/internal/release/pipeline/execute",
            headers={"x-internal-debug": "true", "x-tenant-id": "tenant_pipeline"},
            json={
                "release_id": "rel_p5_004",
                "replay_passed": False,
                "gate_results": {"quality": False},
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["readiness_required"] is False
        assert data["admitted"] is True
        assert data["stage"] == "release_ready"
    finally:
        store.p6_readiness_required = original
