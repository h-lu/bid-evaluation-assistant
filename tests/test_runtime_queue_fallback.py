from __future__ import annotations

from app.main import _create_queue_backend_for_runtime
from app.queue_backend import InMemoryQueueBackend


def test_runtime_queue_backend_falls_back_to_memory_when_true_stack_not_required(monkeypatch):
    def _raise_runtime(_environ=None):
        raise RuntimeError("queue init failed")

    monkeypatch.setattr("app.main.create_queue_from_env", _raise_runtime)
    backend = _create_queue_backend_for_runtime({"BEA_REQUIRE_TRUESTACK": "false"})
    assert isinstance(backend, InMemoryQueueBackend)


def test_runtime_queue_backend_does_not_fallback_when_true_stack_required(monkeypatch):
    def _raise_runtime(_environ=None):
        raise RuntimeError("queue init failed")

    monkeypatch.setattr("app.main.create_queue_from_env", _raise_runtime)
    try:
        _create_queue_backend_for_runtime({"BEA_REQUIRE_TRUESTACK": "true"})
    except RuntimeError as exc:
        assert "queue init failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when true stack is required")
