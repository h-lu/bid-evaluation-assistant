from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import create_app


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _build_hs256_token(*, secret: str, claims: dict[str, object]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_raw = _b64url(json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_raw}.{payload_raw}.{_b64url(signature)}"


def _auth_client(monkeypatch) -> tuple[TestClient, str]:
    shared_key = "jwt_test_key_material"
    monkeypatch.setenv("JWT_ISSUER", "bea.test")
    monkeypatch.setenv("JWT_AUDIENCE", "bea.api")
    monkeypatch.setenv("JWT_SHARED_SECRET", shared_key)
    monkeypatch.setenv("JWT_REQUIRED_CLAIMS", "tenant_id,sub,exp")
    return TestClient(create_app()), shared_key


def _token_for(*, secret: str, tenant_id: str, ttl_minutes: int = 15, extra: dict[str, object] | None = None) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": "bea.test",
        "aud": "bea.api",
        "sub": f"user_{tenant_id}",
        "tenant_id": tenant_id,
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
        "iat": int(now.timestamp()),
    }
    if extra:
        claims.update(extra)
    return _build_hs256_token(secret=secret, claims=claims)


def test_jwt_required_rejects_missing_authorization(monkeypatch):
    client, _secret = _auth_client(monkeypatch)
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"


def test_jwt_rejects_expired_token(monkeypatch):
    client, secret = _auth_client(monkeypatch)
    token = _token_for(secret=secret, tenant_id="tenant_a", ttl_minutes=-1)
    resp = client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"


def test_jwt_rejects_missing_required_claim(monkeypatch):
    client, secret = _auth_client(monkeypatch)
    now = datetime.now(UTC)
    token = _build_hs256_token(
        secret=secret,
        claims={
            "iss": "bea.test",
            "aud": "bea.api",
            "sub": "user_a",
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
    )
    resp = client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_UNAUTHORIZED"


def test_jwt_blocks_tenant_header_spoofing(monkeypatch):
    client, secret = _auth_client(monkeypatch)
    token = _token_for(secret=secret, tenant_id="tenant_a")
    resp = client.get(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}", "x-tenant-id": "tenant_b"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"


def test_jwt_injects_tenant_context_for_resource_access(monkeypatch):
    client, secret = _auth_client(monkeypatch)
    token_a = _token_for(secret=secret, tenant_id="tenant_a")
    token_b = _token_for(secret=secret, tenant_id="tenant_b")

    created = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_a}", "Idempotency-Key": "idem_jwt_eval_1"},
        json={
            "project_id": "prj_jwt",
            "supplier_id": "sup_jwt",
            "rule_pack_version": "v1.0.0",
            "evaluation_scope": {"include_doc_types": ["bid"], "force_hitl": False},
            "query_options": {"mode_hint": "hybrid", "top_k": 10},
        },
    )
    assert created.status_code == 202
    job_id = created.json()["data"]["job_id"]

    own = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert own.status_code == 200

    cross = client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert cross.status_code == 403
    assert cross.json()["error"]["code"] == "TENANT_SCOPE_VIOLATION"
