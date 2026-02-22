from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _evaluation_payload() -> dict:
    return {
        "project_id": "prj_trace",
        "supplier_id": "sup_trace",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
        "query_options": {"mode_hint": "hybrid", "top_k": 20},
    }


def test_api_write_requires_trace_id_when_strict_enabled(monkeypatch):
    monkeypatch.setenv("TRACE_ID_STRICT_REQUIRED", "true")
    client = TestClient(create_app())

    missing = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_trace_missing"},
        json=_evaluation_payload(),
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "TRACE_ID_REQUIRED"

    ok = client.post(
        "/api/v1/evaluations",
        headers={
            "Idempotency-Key": "idem_trace_ok",
            "x-trace-id": "trace_required_ok",
        },
        json=_evaluation_payload(),
    )
    assert ok.status_code == 202
