from app.store import store


def _eval_payload(force_hitl: bool = True) -> dict:
    return {
        "project_id": "prj_gate_f",
        "supplier_id": "sup_gate_f",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": force_hitl},
        "query_options": {"mode_hint": "hybrid", "top_k": 10},
    }


def _strategy_payload(release_id: str = "rel_gate_f_001") -> dict:
    return {
        "release_id": release_id,
        "selector": {
            "risk_mix_threshold": 0.72,
            "relation_mode": "global",
        },
        "score_calibration": {
            "confidence_scale": 1.05,
            "score_bias": -0.5,
        },
        "tool_policy": {
            "require_double_approval_actions": ["dlq_discard"],
            "allowed_tools": ["retrieval", "evaluation", "dlq"],
        },
    }


def test_data_feedback_run_ingests_dlq_and_manual_override_samples(client):
    tenant_headers = {"x-tenant-id": "tenant_f"}
    created = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_gate_f_eval_1", **tenant_headers},
        json=_eval_payload(force_hitl=True),
    )
    assert created.status_code == 202
    evaluation_id = created.json()["data"]["evaluation_id"]

    report = client.get(
        f"/api/v1/evaluations/{evaluation_id}/report",
        headers=tenant_headers,
    )
    resume_token = report.json()["data"]["interrupt"]["resume_token"]

    resumed = client.post(
        f"/api/v1/evaluations/{evaluation_id}/resume",
        headers={"Idempotency-Key": "idem_gate_f_resume_1", **tenant_headers},
        json={
            "resume_token": resume_token,
            "decision": "edit_scores",
            "comment": "manual override candidate",
            "editor": {"reviewer_id": "u_gate_f"},
            "edited_scores": [{"criteria_id": "delivery", "score": 17.5}],
        },
    )
    assert resumed.status_code == 202

    dlq_item = store.seed_dlq_item(
        job_id="job_gate_f_dlq_1",
        error_class="permanent",
        error_code="DOC_PARSE_OUTPUT_NOT_FOUND",
        tenant_id="tenant_f",
    )

    resp = client.post(
        "/api/v1/internal/ops/data-feedback/run",
        headers={"x-internal-debug": "true", **tenant_headers},
        json={
            "release_id": "rel_gate_f_001",
            "dlq_ids": [dlq_item["dlq_id"]],
            "version_bump": "patch",
            "include_manual_override_candidates": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["release_id"] == "rel_gate_f_001"
    assert data["counterexample_added"] == 1
    assert data["gold_candidates_added"] == 1
    assert data["dataset_version_before"] != data["dataset_version_after"]


def test_data_feedback_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/ops/data-feedback/run",
        json={
            "release_id": "rel_gate_f_001",
            "dlq_ids": [],
            "version_bump": "patch",
            "include_manual_override_candidates": True,
        },
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_strategy_tuning_apply_updates_strategy_version_and_payload(client):
    first = client.post(
        "/api/v1/internal/ops/strategy-tuning/apply",
        headers={"x-internal-debug": "true"},
        json=_strategy_payload(),
    )
    assert first.status_code == 200
    first_data = first.json()["data"]
    assert first_data["strategy_version"] == "stg_v1"
    assert first_data["selector"]["risk_mix_threshold"] == 0.72
    assert first_data["score_calibration"]["confidence_scale"] == 1.05
    assert first_data["tool_policy"]["require_double_approval_actions"] == ["dlq_discard"]

    second = client.post(
        "/api/v1/internal/ops/strategy-tuning/apply",
        headers={"x-internal-debug": "true"},
        json=_strategy_payload(release_id="rel_gate_f_002"),
    )
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["strategy_version"] == "stg_v2"
    assert second_data["release_id"] == "rel_gate_f_002"


def test_strategy_tuning_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/ops/strategy-tuning/apply",
        json=_strategy_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
