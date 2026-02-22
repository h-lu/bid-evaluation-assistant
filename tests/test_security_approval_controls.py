from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _strategy_payload() -> dict:
    return {
        "release_id": "rel_sec_001",
        "selector": {"risk_mix_threshold": 0.71, "relation_mode": "global"},
        "score_calibration": {"confidence_scale": 1.01, "score_bias": 0.0},
        "tool_policy": {
            "require_double_approval_actions": ["dlq_discard"],
            "allowed_tools": ["retrieval", "evaluation", "dlq"],
        },
    }


def test_strategy_tuning_requires_approval_when_action_enabled(monkeypatch):
    monkeypatch.setenv("SECURITY_APPROVAL_REQUIRED_ACTIONS", "strategy_tuning_apply,dlq_discard")
    client = TestClient(create_app())

    blocked = client.post(
        "/api/v1/internal/ops/strategy-tuning/apply",
        headers={"x-internal-debug": "true"},
        json=_strategy_payload(),
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "APPROVAL_REQUIRED"

    allowed = client.post(
        "/api/v1/internal/ops/strategy-tuning/apply",
        headers={
            "x-internal-debug": "true",
            "x-reviewer-id": "u_security_reviewer",
            "x-reviewer-id-2": "u_security_reviewer_2",
            "x-approval-reason": "production tuning approved",
        },
        json=_strategy_payload(),
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["strategy_version"].startswith("stg_v")
