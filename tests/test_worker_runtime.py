from __future__ import annotations

from app.queue_backend import InMemoryQueueBackend
from app.store import InMemoryStore
from app.worker_runtime import WorkerRuntime


def _seed_job(store: InMemoryStore, *, tenant_id: str, idx: int) -> str:
    created = store.create_upload_job(
        {
            "tenant_id": tenant_id,
            "trace_id": f"trace_{tenant_id}_{idx}",
            "project_id": f"prj_{tenant_id}",
            "supplier_id": f"sup_{tenant_id}",
            "doc_type": "bid",
            "filename": f"{tenant_id}_{idx}.pdf",
            "file_sha256": f"{tenant_id}_{idx}",
            "file_size": 12,
        }
    )
    return str(created["job_id"])


def test_worker_runtime_processes_multiple_tenants_fairly():
    s = InMemoryStore()
    q = InMemoryQueueBackend()
    rt = WorkerRuntime(
        store=s,
        queue_backend=q,
        queue_names=["jobs"],
        tenant_burst_limit=1,
        max_messages_per_iteration=2,
    )

    job_a = _seed_job(s, tenant_id="tenant_a", idx=1)
    job_b = _seed_job(s, tenant_id="tenant_b", idx=1)
    q.enqueue(tenant_id="tenant_a", queue_name="jobs", payload={"job_id": job_a, "job_type": "upload"})
    q.enqueue(tenant_id="tenant_b", queue_name="jobs", payload={"job_id": job_b, "job_type": "upload"})

    result = rt.run_once()
    assert result["processed"] == 2
    assert result["succeeded"] == 2
    assert s.get_job_for_tenant(job_id=job_a, tenant_id="tenant_a")["status"] == "succeeded"
    assert s.get_job_for_tenant(job_id=job_b, tenant_id="tenant_b")["status"] == "succeeded"


def test_store_reads_worker_runtime_config_from_env(monkeypatch):
    monkeypatch.setenv("RESUME_TOKEN_TTL_HOURS", "12")
    monkeypatch.setenv("WORKER_MAX_RETRIES", "5")
    monkeypatch.setenv("WORKER_RETRY_BACKOFF_BASE_MS", "2000")
    monkeypatch.setenv("WORKER_RETRY_BACKOFF_MAX_MS", "45000")
    monkeypatch.setenv("WORKFLOW_CHECKPOINT_BACKEND", "postgres")
    configured = InMemoryStore()
    assert configured.resume_token_ttl_hours == 12
    assert configured.worker_max_retries == 5
    assert configured.worker_retry_backoff_base_ms == 2000
    assert configured.worker_retry_backoff_max_ms == 45000
    assert configured.workflow_checkpoint_backend == "postgres"
