import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app
from app.store import store


@pytest.fixture(autouse=True)
def reset_store():
    store.reset()
    yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
