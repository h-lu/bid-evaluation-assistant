from app.store import store


def _rollout_plan_payload(
    *,
    release_id: str = "rel_gate_e_001",
    tenant_whitelist: list[str] | None = None,
    enabled_project_sizes: list[str] | None = None,
    high_risk_hitl_enforced: bool = True,
) -> dict:
    return {
        "release_id": release_id,
        "tenant_whitelist": tenant_whitelist or ["tenant_a"],
        "enabled_project_sizes": enabled_project_sizes or ["small", "medium"],
        "high_risk_hitl_enforced": high_risk_hitl_enforced,
    }


def _rollback_payload(
    *,
    release_id: str = "rel_gate_e_001",
    threshold: int = 2,
    breaches: list[dict] | None = None,
) -> dict:
    return {
        "release_id": release_id,
        "consecutive_threshold": threshold,
        "breaches": breaches
        or [
            {
                "gate": "quality",
                "metric_code": "DEEPEVAL_HALLUCINATION_RATE_HIGH",
                "consecutive_failures": 2,
            }
        ],
    }


def test_rollout_plan_and_decision_pass(client):
    plan = client.post(
        "/api/v1/internal/release/rollout/plan",
        headers={"x-internal-debug": "true"},
        json=_rollout_plan_payload(),
    )
    assert plan.status_code == 200
    plan_data = plan.json()["data"]
    assert plan_data["release_id"] == "rel_gate_e_001"
    assert plan_data["tenant_whitelist"] == ["tenant_a"]
    assert plan_data["enabled_project_sizes"] == ["small", "medium"]
    assert plan_data["high_risk_hitl_enforced"] is True

    decision = client.post(
        "/api/v1/internal/release/rollout/decision",
        headers={"x-internal-debug": "true"},
        json={
            "release_id": "rel_gate_e_001",
            "tenant_id": "tenant_a",
            "project_size": "small",
            "high_risk": False,
        },
    )
    assert decision.status_code == 200
    data = decision.json()["data"]
    assert data["admitted"] is True
    assert data["matched_whitelist"] is True
    assert data["force_hitl"] is False
    assert data["reasons"] == []


def test_rollout_decision_blocks_by_whitelist_or_project_size(client):
    client.post(
        "/api/v1/internal/release/rollout/plan",
        headers={"x-internal-debug": "true"},
        json=_rollout_plan_payload(enabled_project_sizes=["small"]),
    )

    blocked_tenant = client.post(
        "/api/v1/internal/release/rollout/decision",
        headers={"x-internal-debug": "true"},
        json={
            "release_id": "rel_gate_e_001",
            "tenant_id": "tenant_b",
            "project_size": "small",
            "high_risk": False,
        },
    )
    assert blocked_tenant.status_code == 200
    blocked_tenant_data = blocked_tenant.json()["data"]
    assert blocked_tenant_data["admitted"] is False
    assert "TENANT_NOT_IN_WHITELIST" in blocked_tenant_data["reasons"]

    blocked_size = client.post(
        "/api/v1/internal/release/rollout/decision",
        headers={"x-internal-debug": "true"},
        json={
            "release_id": "rel_gate_e_001",
            "tenant_id": "tenant_a",
            "project_size": "large",
            "high_risk": False,
        },
    )
    assert blocked_size.status_code == 200
    blocked_size_data = blocked_size.json()["data"]
    assert blocked_size_data["admitted"] is False
    assert "PROJECT_SIZE_NOT_ENABLED" in blocked_size_data["reasons"]


def test_rollout_decision_forces_hitl_for_high_risk(client):
    client.post(
        "/api/v1/internal/release/rollout/plan",
        headers={"x-internal-debug": "true"},
        json=_rollout_plan_payload(),
    )
    resp = client.post(
        "/api/v1/internal/release/rollout/decision",
        headers={"x-internal-debug": "true"},
        json={
            "release_id": "rel_gate_e_001",
            "tenant_id": "tenant_a",
            "project_size": "medium",
            "high_risk": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["admitted"] is True
    assert data["force_hitl"] is True


def test_gate_e_rollout_endpoints_require_internal_header(client):
    plan = client.post(
        "/api/v1/internal/release/rollout/plan",
        json=_rollout_plan_payload(),
    )
    assert plan.status_code == 403
    assert plan.json()["error"]["code"] == "AUTH_FORBIDDEN"

    decision = client.post(
        "/api/v1/internal/release/rollout/decision",
        json={
            "release_id": "rel_gate_e_001",
            "tenant_id": "tenant_a",
            "project_size": "small",
            "high_risk": False,
        },
    )
    assert decision.status_code == 403
    assert decision.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_rollback_execute_triggers_and_runs_replay_verification(client):
    resp = client.post(
        "/api/v1/internal/release/rollback/execute",
        headers={"x-internal-debug": "true"},
        json=_rollback_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["triggered"] is True
    assert data["trigger_gate"] == "quality"
    assert data["rollback_order"] == [
        "model_config",
        "retrieval_params",
        "workflow_version",
        "release_version",
    ]
    replay = data["replay_verification"]
    assert replay["job_id"].startswith("job_")
    assert replay["status"] == "succeeded"
    assert data["rollback_completed_within_30m"] is True
    assert data["service_restored"] is True

    replay_job = client.get(f"/api/v1/jobs/{replay['job_id']}")
    assert replay_job.status_code == 200
    assert replay_job.json()["data"]["status"] == "succeeded"

    assert any(x.get("action") == "rollback_executed" for x in store.audit_logs)
    assert any(x.get("action") == "rollback_replay_verified" for x in store.audit_logs)


def test_rollback_execute_no_trigger_when_below_threshold(client):
    resp = client.post(
        "/api/v1/internal/release/rollback/execute",
        headers={"x-internal-debug": "true"},
        json=_rollback_payload(
            threshold=2,
            breaches=[
                {
                    "gate": "performance",
                    "metric_code": "API_P95_EXCEEDED",
                    "consecutive_failures": 1,
                }
            ],
        ),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["triggered"] is False
    assert data["trigger_gate"] is None
    assert data["replay_verification"] is None


def test_rollback_execute_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/release/rollback/execute",
        json=_rollback_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
