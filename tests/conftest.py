import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app, queue_backend
from app.store import store


@pytest.fixture(autouse=True)
def reset_store(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEA_OBJECT_STORAGE_BACKEND", "local")
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "object_store"))
    store.reset()
    if hasattr(queue_backend, "reset"):
        queue_backend.reset()
    yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
