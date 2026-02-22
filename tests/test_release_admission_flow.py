def _gate_results_all_pass() -> dict:
    return {
        "quality": True,
        "performance": True,
        "security": True,
        "cost": True,
        "rollout": True,
        "rollback": True,
        "ops": True,
    }


def test_release_admission_full_flow(client):
    headers = {"x-internal-debug": "true", "x-tenant-id": "tenant_release_flow"}
    release_id = "rel_p6_full_001"

    rollout = client.post(
        "/api/v1/internal/release/rollout/plan",
        headers=headers,
        json={
            "release_id": release_id,
            "tenant_whitelist": ["tenant_release_flow"],
            "enabled_project_sizes": ["small", "medium"],
            "high_risk_hitl_enforced": True,
        },
    )
    assert rollout.status_code == 200

    decision = client.post(
        "/api/v1/internal/release/rollout/decision",
        headers=headers,
        json={
            "release_id": release_id,
            "tenant_id": "tenant_release_flow",
            "project_size": "small",
            "high_risk": False,
        },
    )
    assert decision.status_code == 200
    assert decision.json()["data"]["admitted"] is True

    replay = client.post(
        "/api/v1/internal/release/replay/e2e",
        headers=headers,
        json={
            "release_id": release_id,
            "project_id": "prj_release_flow",
            "supplier_id": "sup_release_flow",
            "doc_type": "bid",
            "force_hitl": True,
            "decision": "approve",
        },
    )
    assert replay.status_code == 200
    assert replay.json()["data"]["passed"] is True

    readiness = client.post(
        "/api/v1/internal/release/readiness/evaluate",
        headers=headers,
        json={
            "release_id": release_id,
            "replay_passed": True,
            "gate_results": _gate_results_all_pass(),
        },
    )
    assert readiness.status_code == 200
    assert readiness.json()["data"]["admitted"] is True

    pipeline = client.post(
        "/api/v1/internal/release/pipeline/execute",
        headers=headers,
        json={
            "release_id": release_id,
            "replay_passed": True,
            "gate_results": _gate_results_all_pass(),
        },
    )
    assert pipeline.status_code == 200
    data = pipeline.json()["data"]
    assert data["admitted"] is True
    assert data["stage"] == "release_ready"
    assert data["readiness_assessment_id"].startswith("ra_")
