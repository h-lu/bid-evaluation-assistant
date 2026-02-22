from __future__ import annotations

import os
import threading
import uuid
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class QueueMessage:
    message_id: str
    tenant_id: str
    queue_name: str
    payload: dict[str, Any]
    attempt: int = 0


class InMemoryQueueBackend:
    """Queue abstraction used by P1 before swapping in Redis backend."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._queues: dict[str, deque[QueueMessage]] = {}
        self._inflight: dict[str, QueueMessage] = {}

    @staticmethod
    def queue_key(*, tenant_id: str, queue_name: str) -> str:
        return f"bea:{tenant_id}:queue:{queue_name}"

    def enqueue(self, *, tenant_id: str, queue_name: str, payload: dict[str, Any]) -> QueueMessage:
        with self._lock:
            key = self.queue_key(tenant_id=tenant_id, queue_name=queue_name)
            msg = QueueMessage(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                queue_name=queue_name,
                payload=payload,
                attempt=int(payload.get("attempt", 0)),
            )
            self._queues.setdefault(key, deque()).append(msg)
            return msg

    def dequeue(self, *, tenant_id: str, queue_name: str) -> QueueMessage | None:
        with self._lock:
            key = self.queue_key(tenant_id=tenant_id, queue_name=queue_name)
            queue = self._queues.setdefault(key, deque())
            if not queue:
                return None
            msg = queue.popleft()
            self._inflight[msg.message_id] = msg
            return msg

    def ack(self, *, message_id: str) -> None:
        with self._lock:
            self._inflight.pop(message_id, None)

    def nack(self, *, message_id: str, requeue: bool = True) -> QueueMessage | None:
        with self._lock:
            msg = self._inflight.pop(message_id, None)
            if msg is None:
                return None
            msg.attempt += 1
            if requeue:
                key = self.queue_key(tenant_id=msg.tenant_id, queue_name=msg.queue_name)
                self._queues.setdefault(key, deque()).appendleft(msg)
            return msg

    def pending_count(self, *, tenant_id: str, queue_name: str) -> int:
        with self._lock:
            key = self.queue_key(tenant_id=tenant_id, queue_name=queue_name)
            return len(self._queues.get(key, deque()))

    def reset(self) -> None:
        with self._lock:
            self._queues.clear()
            self._inflight.clear()


def create_queue_from_env(environ: Mapping[str, str] | None = None) -> InMemoryQueueBackend:
    env = os.environ if environ is None else environ
    backend = env.get("BEA_QUEUE_BACKEND", "memory").strip().lower()
    if backend != "memory":
        raise RuntimeError(f"unsupported queue backend: {backend}")
    return InMemoryQueueBackend()
