from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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

    def ack(self, *, tenant_id: str, message_id: str) -> None:
        with self._lock:
            msg = self._inflight.get(message_id)
            if msg is None:
                return
            if msg.tenant_id != tenant_id:
                raise RuntimeError("tenant mismatch for queue message")
            self._inflight.pop(message_id, None)

    def nack(self, *, tenant_id: str, message_id: str, requeue: bool = True) -> QueueMessage | None:
        with self._lock:
            msg = self._inflight.pop(message_id, None)
            if msg is None:
                return None
            if msg.tenant_id != tenant_id:
                self._inflight[message_id] = msg
                raise RuntimeError("tenant mismatch for queue message")
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


class SqliteQueueBackend:
    """SQLite-backed queue used for local persistence and replay tests."""

    def __init__(self, db_path: str | Path) -> None:
        self._lock = threading.RLock()
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @staticmethod
    def queue_key(*, tenant_id: str, queue_name: str) -> str:
        return InMemoryQueueBackend.queue_key(tenant_id=tenant_id, queue_name=queue_name)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue_messages (
                    message_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    queue_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_messages_lookup
                ON queue_messages(tenant_id, queue_name, status, created_at)
                """
            )
            conn.commit()

    @staticmethod
    def _utcnow() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> QueueMessage:
        payload = json.loads(row["payload"])
        return QueueMessage(
            message_id=row["message_id"],
            tenant_id=row["tenant_id"],
            queue_name=row["queue_name"],
            payload=payload,
            attempt=row["attempt"],
        )

    def enqueue(self, *, tenant_id: str, queue_name: str, payload: dict[str, Any]) -> QueueMessage:
        with self._lock:
            now = self._utcnow()
            msg = QueueMessage(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                queue_name=queue_name,
                payload=payload,
                attempt=int(payload.get("attempt", 0)),
            )
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO queue_messages(
                        message_id, tenant_id, queue_name, payload, attempt, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                    """,
                    (
                        msg.message_id,
                        msg.tenant_id,
                        msg.queue_name,
                        json.dumps(msg.payload, ensure_ascii=True, sort_keys=True),
                        msg.attempt,
                        now,
                        now,
                    ),
                )
                conn.commit()
            return msg

    def dequeue(self, *, tenant_id: str, queue_name: str) -> QueueMessage | None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT message_id, tenant_id, queue_name, payload, attempt
                    FROM queue_messages
                    WHERE tenant_id = ? AND queue_name = ? AND status = 'pending'
                    ORDER BY created_at ASC, message_id ASC
                    LIMIT 1
                    """,
                    (tenant_id, queue_name),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return None
                conn.execute(
                    """
                    UPDATE queue_messages
                    SET status = 'inflight', updated_at = ?
                    WHERE message_id = ?
                    """,
                    (self._utcnow(), row["message_id"]),
                )
                conn.commit()
                return self._row_to_message(row)

    def ack(self, *, tenant_id: str, message_id: str) -> None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT tenant_id
                    FROM queue_messages
                    WHERE message_id = ? AND status = 'inflight'
                    LIMIT 1
                    """,
                    (message_id,),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return
                if row["tenant_id"] != tenant_id:
                    raise RuntimeError("tenant mismatch for queue message")
                conn.execute("DELETE FROM queue_messages WHERE message_id = ?", (message_id,))
                conn.commit()

    def nack(self, *, tenant_id: str, message_id: str, requeue: bool = True) -> QueueMessage | None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT message_id, tenant_id, queue_name, payload, attempt
                    FROM queue_messages
                    WHERE message_id = ? AND status = 'inflight'
                    LIMIT 1
                    """,
                    (message_id,),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return None
                if row["tenant_id"] != tenant_id:
                    conn.commit()
                    raise RuntimeError("tenant mismatch for queue message")
                next_attempt = int(row["attempt"]) + 1
                status = "pending" if requeue else "discarded"
                conn.execute(
                    """
                    UPDATE queue_messages
                    SET attempt = ?, status = ?, updated_at = ?
                    WHERE message_id = ?
                    """,
                    (next_attempt, status, self._utcnow(), message_id),
                )
                conn.commit()
                msg = self._row_to_message(row)
                msg.attempt = next_attempt
                return msg

    def pending_count(self, *, tenant_id: str, queue_name: str) -> int:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(1) AS cnt
                    FROM queue_messages
                    WHERE tenant_id = ? AND queue_name = ? AND status = 'pending'
                    """,
                    (tenant_id, queue_name),
                ).fetchone()
                return int(row["cnt"]) if row is not None else 0

    def reset(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM queue_messages")
                conn.commit()


def _import_redis() -> Any:
    try:
        import redis  # type: ignore
    except ImportError as exc:
        raise RuntimeError("redis is required for BEA_QUEUE_BACKEND=redis; install redis>=5") from exc
    return redis


class RedisQueueBackend:
    """Redis-backed queue for production-like message semantics."""

    def __init__(self, *, dsn: str, namespace: str = "bea") -> None:
        if not dsn.strip():
            raise ValueError("REDIS_DSN must be provided for redis queue backend")
        self._dsn = dsn.strip()
        self._namespace = namespace.strip() or "bea"
        self._lock = threading.RLock()
        redis = _import_redis()
        self._client = redis.Redis.from_url(self._dsn, decode_responses=True)

    def _registry_key(self) -> str:
        return f"{self._namespace}:queue:keys"

    def _pending_key(self, *, tenant_id: str, queue_name: str) -> str:
        return f"{self._namespace}:{tenant_id}:queue:{queue_name}:pending"

    def _inflight_key(self, *, tenant_id: str, queue_name: str) -> str:
        return f"{self._namespace}:{tenant_id}:queue:{queue_name}:inflight"

    def _msg_key(self, *, message_id: str) -> str:
        return f"{self._namespace}:msg:{message_id}"

    def _idx_key(self, *, message_id: str) -> str:
        return f"{self._namespace}:msgidx:{message_id}"

    def _track_keys(self, *keys: str) -> None:
        for key in keys:
            self._client.sadd(self._registry_key(), key)

    def _load_idx(self, *, message_id: str) -> dict[str, str] | None:
        raw = self._client.get(self._idx_key(message_id=message_id))
        if not isinstance(raw, str) or not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        tenant_id = str(data.get("tenant_id", ""))
        queue_name = str(data.get("queue_name", ""))
        if not tenant_id or not queue_name:
            return None
        return {"tenant_id": tenant_id, "queue_name": queue_name}

    def _load_msg(self, *, message_id: str) -> dict[str, Any] | None:
        raw = self._client.get(self._msg_key(message_id=message_id))
        if not isinstance(raw, str) or not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _save_msg(self, *, message_id: str, data: dict[str, Any]) -> None:
        self._client.set(
            self._msg_key(message_id=message_id),
            json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":")),
        )

    def enqueue(self, *, tenant_id: str, queue_name: str, payload: dict[str, Any]) -> QueueMessage:
        with self._lock:
            msg = QueueMessage(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                queue_name=queue_name,
                payload=payload,
                attempt=int(payload.get("attempt", 0)),
            )
            pending_key = self._pending_key(tenant_id=tenant_id, queue_name=queue_name)
            inflight_key = self._inflight_key(tenant_id=tenant_id, queue_name=queue_name)
            idx_key = self._idx_key(message_id=msg.message_id)
            msg_key = self._msg_key(message_id=msg.message_id)
            self._client.set(
                idx_key,
                json.dumps(
                    {"tenant_id": tenant_id, "queue_name": queue_name},
                    sort_keys=True,
                    ensure_ascii=True,
                    separators=(",", ":"),
                ),
            )
            self._save_msg(
                message_id=msg.message_id,
                data={
                    "tenant_id": msg.tenant_id,
                    "queue_name": msg.queue_name,
                    "payload": msg.payload,
                    "attempt": msg.attempt,
                    "status": "pending",
                },
            )
            self._client.rpush(pending_key, msg.message_id)
            self._track_keys(pending_key, inflight_key, idx_key, msg_key)
            return msg

    def dequeue(self, *, tenant_id: str, queue_name: str) -> QueueMessage | None:
        with self._lock:
            pending_key = self._pending_key(tenant_id=tenant_id, queue_name=queue_name)
            inflight_key = self._inflight_key(tenant_id=tenant_id, queue_name=queue_name)
            raw_message_id = self._client.lpop(pending_key)
            if not isinstance(raw_message_id, str) or not raw_message_id:
                return None
            msg_data = self._load_msg(message_id=raw_message_id)
            if msg_data is None:
                return None
            msg_data["status"] = "inflight"
            self._save_msg(message_id=raw_message_id, data=msg_data)
            self._client.sadd(inflight_key, raw_message_id)
            self._track_keys(pending_key, inflight_key)
            return QueueMessage(
                message_id=raw_message_id,
                tenant_id=str(msg_data.get("tenant_id", tenant_id)),
                queue_name=str(msg_data.get("queue_name", queue_name)),
                payload=msg_data.get("payload", {}),
                attempt=int(msg_data.get("attempt", 0)),
            )

    def ack(self, *, tenant_id: str, message_id: str) -> None:
        with self._lock:
            idx = self._load_idx(message_id=message_id)
            if idx is None:
                return
            if idx["tenant_id"] != tenant_id:
                raise RuntimeError("tenant mismatch for queue message")
            msg_data = self._load_msg(message_id=message_id)
            if msg_data is None or msg_data.get("status") != "inflight":
                return
            inflight_key = self._inflight_key(tenant_id=tenant_id, queue_name=idx["queue_name"])
            self._client.srem(inflight_key, message_id)
            self._client.delete(self._msg_key(message_id=message_id))
            self._client.delete(self._idx_key(message_id=message_id))

    def nack(self, *, tenant_id: str, message_id: str, requeue: bool = True) -> QueueMessage | None:
        with self._lock:
            idx = self._load_idx(message_id=message_id)
            if idx is None:
                return None
            if idx["tenant_id"] != tenant_id:
                raise RuntimeError("tenant mismatch for queue message")
            msg_data = self._load_msg(message_id=message_id)
            if msg_data is None or msg_data.get("status") != "inflight":
                return None
            inflight_key = self._inflight_key(tenant_id=tenant_id, queue_name=idx["queue_name"])
            pending_key = self._pending_key(tenant_id=tenant_id, queue_name=idx["queue_name"])
            next_attempt = int(msg_data.get("attempt", 0)) + 1
            msg_data["attempt"] = next_attempt
            if requeue:
                msg_data["status"] = "pending"
                self._save_msg(message_id=message_id, data=msg_data)
                self._client.srem(inflight_key, message_id)
                self._client.lpush(pending_key, message_id)
            else:
                msg_data["status"] = "discarded"
                self._save_msg(message_id=message_id, data=msg_data)
                self._client.srem(inflight_key, message_id)
            return QueueMessage(
                message_id=message_id,
                tenant_id=tenant_id,
                queue_name=idx["queue_name"],
                payload=msg_data.get("payload", {}),
                attempt=next_attempt,
            )

    def pending_count(self, *, tenant_id: str, queue_name: str) -> int:
        with self._lock:
            return int(self._client.llen(self._pending_key(tenant_id=tenant_id, queue_name=queue_name)))

    def reset(self) -> None:
        with self._lock:
            registry = self._registry_key()
            keys = self._client.smembers(registry)
            if keys:
                self._client.delete(*list(keys))
            self._client.delete(registry)


def create_queue_from_env(
    environ: Mapping[str, str] | None = None,
) -> InMemoryQueueBackend | SqliteQueueBackend | RedisQueueBackend:
    env = os.environ if environ is None else environ
    backend = env.get("BEA_QUEUE_BACKEND", "memory").strip().lower()
    if backend == "memory":
        return InMemoryQueueBackend()
    if backend == "sqlite":
        db_path = env.get("BEA_QUEUE_SQLITE_PATH", ".runtime/bea_queue.sqlite3")
        return SqliteQueueBackend(db_path)
    if backend == "redis":
        dsn = env.get("REDIS_DSN", "").strip()
        if not dsn:
            raise ValueError("REDIS_DSN must be set when BEA_QUEUE_BACKEND=redis")
        namespace = env.get("BEA_QUEUE_KEY_PREFIX", "bea")
        return RedisQueueBackend(dsn=dsn, namespace=namespace)
    raise RuntimeError(f"unsupported queue backend: {backend}")
