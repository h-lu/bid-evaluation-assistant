def test_internal_release_replay_e2e_success(client):
    resp = client.post(
        "/api/v1/internal/release/replay/e2e",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_release"},
        json={
            "release_id": "rel_p6_001",
            "project_id": "prj_release",
            "supplier_id": "sup_release",
            "doc_type": "bid",
            "force_hitl": True,
            "decision": "approve",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["release_id"] == "rel_p6_001"
    assert data["tenant_id"] == "tenant_release"
    assert data["replay_run_id"].startswith("rpy_")
    assert data["parse"]["status"] == "succeeded"
    assert data["evaluation"]["needs_human_review"] is False
    assert data["passed"] is True


def test_internal_release_readiness_evaluate_success(client):
    resp = client.post(
        "/api/v1/internal/release/readiness/evaluate",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_release"},
        json={
            "release_id": "rel_p6_001",
            "dataset_version": "v1.0.0",
            "replay_passed": True,
            "gate_results": {
                "quality": True,
                "performance": True,
                "security": True,
                "cost": True,
                "rollout": True,
                "rollback": True,
                "ops": True,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["release_id"] == "rel_p6_001"
    assert data["admitted"] is True
    assert data["failed_checks"] == []
    assert data["assessment_id"].startswith("ra_")


def test_internal_release_readiness_evaluate_blocks_when_replay_failed(client):
    resp = client.post(
        "/api/v1/internal/release/readiness/evaluate",
        headers={"x-internal-debug": "true", "x-tenant-id": "tenant_release"},
        json={
            "release_id": "rel_p6_002",
            "replay_passed": False,
            "gate_results": {
                "quality": True,
                "performance": True,
                "security": True,
                "cost": True,
                "rollout": True,
                "rollback": True,
                "ops": True,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["admitted"] is False
    assert "REPLAY_E2E_FAILED" in data["failed_checks"]


def test_internal_release_p6_endpoints_require_internal_header(client):
    replay = client.post("/api/v1/internal/release/replay/e2e", json={"release_id": "rel_x"})
    assert replay.status_code == 403
    assert replay.json()["error"]["code"] == "AUTH_FORBIDDEN"

    readiness = client.post(
        "/api/v1/internal/release/readiness/evaluate",
        json={"release_id": "rel_x", "replay_passed": True, "gate_results": {}},
    )
    assert readiness.status_code == 403
    assert readiness.json()["error"]["code"] == "AUTH_FORBIDDEN"
