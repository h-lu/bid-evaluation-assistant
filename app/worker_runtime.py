from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerRunStats:
    processed: int = 0
    succeeded: int = 0
    retrying: int = 0
    failed: int = 0
    acked: int = 0
    requeued: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "processed": self.processed,
            "succeeded": self.succeeded,
            "retrying": self.retrying,
            "failed": self.failed,
            "acked": self.acked,
            "requeued": self.requeued,
        }


class WorkerRuntime:
    """Resident worker runtime used by P3 to process queued jobs."""

    def __init__(
        self,
        *,
        store: Any,
        queue_backend: Any,
        queue_names: list[str] | None = None,
        tenant_burst_limit: int = 1,
        max_messages_per_iteration: int = 20,
        poll_interval_ms: int = 200,
    ) -> None:
        self.store = store
        self.queue_backend = queue_backend
        self.queue_names = list(queue_names or ["jobs"])
        self.tenant_burst_limit = max(1, int(tenant_burst_limit))
        self.max_messages_per_iteration = max(1, int(max_messages_per_iteration))
        self.poll_interval_ms = max(1, int(poll_interval_ms))

    def _list_tenants(self, *, queue_name: str) -> list[str]:
        method = getattr(self.queue_backend, "list_tenants", None)
        if callable(method):
            tenants = method(queue_name=queue_name)
            if isinstance(tenants, list):
                return [str(x) for x in tenants if str(x)]
        return []

    def _process_message(self, *, queue_name: str, tenant_id: str, stats: WorkerRunStats) -> bool:
        msg = self.queue_backend.dequeue(tenant_id=tenant_id, queue_name=queue_name)
        if msg is None:
            return False
        stats.processed += 1
        job_id = str(msg.payload.get("job_id") or "")
        if not job_id:
            self.queue_backend.ack(tenant_id=tenant_id, message_id=msg.message_id)
            stats.acked += 1
            return True

        try:
            result = self.store.run_job_once(job_id=job_id, tenant_id=tenant_id)
        except Exception:
            # Keep worker loop alive on unexpected execution failures.
            self.queue_backend.ack(tenant_id=tenant_id, message_id=msg.message_id)
            stats.acked += 1
            stats.failed += 1
            return True
        final_status = str(result.get("final_status", ""))
        if final_status == "retrying":
            delay_ms = int(result.get("retry_after_ms", 0) or 0)
            self.queue_backend.nack(
                tenant_id=tenant_id,
                message_id=msg.message_id,
                requeue=True,
                delay_ms=max(0, delay_ms),
            )
            stats.requeued += 1
            stats.retrying += 1
            return True

        self.queue_backend.ack(tenant_id=tenant_id, message_id=msg.message_id)
        stats.acked += 1
        if final_status in {"succeeded", "needs_manual_decision"}:
            stats.succeeded += 1
        else:
            stats.failed += 1
        return True

    def run_once(self) -> dict[str, int]:
        stats = WorkerRunStats()
        for queue_name in self.queue_names:
            while stats.processed < self.max_messages_per_iteration:
                tenants = self._list_tenants(queue_name=queue_name)
                if not tenants:
                    break
                progressed = False
                for tenant_id in tenants:
                    for _ in range(self.tenant_burst_limit):
                        if stats.processed >= self.max_messages_per_iteration:
                            break
                        handled = self._process_message(
                            queue_name=queue_name,
                            tenant_id=tenant_id,
                            stats=stats,
                        )
                        progressed = progressed or handled
                        if not handled:
                            break
                if not progressed:
                    break
        return stats.as_dict()

    def run_forever(self, *, stop_after_iterations: int | None = None) -> dict[str, int]:
        aggregate = WorkerRunStats()
        iterations = 0
        while True:
            current = self.run_once()
            aggregate.processed += int(current["processed"])
            aggregate.succeeded += int(current["succeeded"])
            aggregate.retrying += int(current["retrying"])
            aggregate.failed += int(current["failed"])
            aggregate.acked += int(current["acked"])
            aggregate.requeued += int(current["requeued"])
            iterations += 1
            if stop_after_iterations is not None and iterations >= max(1, stop_after_iterations):
                break
            if int(current["processed"]) == 0:
                time.sleep(self.poll_interval_ms / 1000.0)
        return aggregate.as_dict()


def _env_int(env: Mapping[str, str], name: str, *, default: int, minimum: int = 0) -> int:
    raw = str(env.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def create_worker_runtime_from_env(
    *,
    store: Any,
    queue_backend: Any,
    environ: Mapping[str, str] | None = None,
) -> WorkerRuntime:
    env = os.environ if environ is None else environ
    queue_names_raw = str(env.get("WORKER_QUEUE_NAMES", "jobs")).strip()
    queue_names = [x.strip() for x in queue_names_raw.split(",") if x.strip()] or ["jobs"]
    parse_concurrency = _env_int(env, "WORKER_CONCURRENCY_PARSE", default=2, minimum=1)
    eval_concurrency = _env_int(env, "WORKER_CONCURRENCY_EVAL", default=2, minimum=1)
    max_messages_per_iteration = parse_concurrency + eval_concurrency
    tenant_burst_limit = _env_int(env, "WORKER_TENANT_BURST_LIMIT", default=1, minimum=1)
    poll_interval_ms = _env_int(env, "WORKER_POLL_INTERVAL_MS", default=200, minimum=1)
    return WorkerRuntime(
        store=store,
        queue_backend=queue_backend,
        queue_names=queue_names,
        tenant_burst_limit=tenant_burst_limit,
        max_messages_per_iteration=max_messages_per_iteration,
        poll_interval_ms=poll_interval_ms,
    )
