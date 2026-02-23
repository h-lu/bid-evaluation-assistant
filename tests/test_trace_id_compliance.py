from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
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


def _issue_token(*, secret: str, tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"user_{tenant_id}",
        "tenant_id": tenant_id,
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": "test-issuer",
        "aud": "test-audience",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_api_write_requires_trace_id_when_strict_enabled(monkeypatch):
    monkeypatch.setenv("TRACE_ID_STRICT_REQUIRED", "true")
    monkeypatch.setenv("JWT_SHARED_SECRET", "jwt_test_secret_trace_32bytes_min_for_sha256")
    monkeypatch.setenv("JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("JWT_REQUIRED_CLAIMS", "tenant_id,sub,exp")
    client = TestClient(create_app())
    token = _issue_token(secret="jwt_test_secret_trace_32bytes_min_for_sha256", tenant_id="tenant_trace")

    missing = client.post(
        "/api/v1/evaluations",
        headers={"Idempotency-Key": "idem_trace_missing", "Authorization": f"Bearer {token}"},
        json=_evaluation_payload(),
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "TRACE_ID_REQUIRED"

    ok = client.post(
        "/api/v1/evaluations",
        headers={
            "Idempotency-Key": "idem_trace_ok",
            "x-trace-id": "trace_required_ok",
            "Authorization": f"Bearer {token}",
        },
        json=_evaluation_payload(),
    )
    assert ok.status_code == 202
