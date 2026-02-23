import pathlib
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
import jwt

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app, queue_backend
from app.store import store


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


class AuthenticatedClient:
    def __init__(self, client: TestClient, *, jwt_secret: str):
        self._client = client
        self._jwt_secret = jwt_secret

    def request(self, method: str, url: str, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        if url.startswith("/api/v1/") and not url.startswith("/api/v1/internal/"):
            if "Authorization" not in headers:
                tenant_id = headers.get("x-tenant-id") or "tenant_default"
                token = _issue_token(secret=self._jwt_secret, tenant_id=str(tenant_id))
                headers["Authorization"] = f"Bearer {token}"
        return self._client.request(method, url, headers=headers, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture(autouse=True)
def reset_store(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEA_OBJECT_STORAGE_BACKEND", "local")
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    monkeypatch.setenv("JWT_SHARED_SECRET", "jwt_test_secret")
    monkeypatch.setenv("JWT_ISSUER", "test-issuer")
    monkeypatch.setenv("JWT_AUDIENCE", "test-audience")
    monkeypatch.setenv("JWT_REQUIRED_CLAIMS", "tenant_id,sub,exp")
    store.reset()
    if hasattr(queue_backend, "reset"):
        queue_backend.reset()
    yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    base = TestClient(app)
    return AuthenticatedClient(base, jwt_secret="jwt_test_secret")
