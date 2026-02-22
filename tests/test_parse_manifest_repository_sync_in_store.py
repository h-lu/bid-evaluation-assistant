from __future__ import annotations

from app.store import InMemoryStore


class CopyingParseManifestsRepository:
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def upsert(self, *, manifest: dict) -> dict:
        item = dict(manifest)
        self._rows[str(item["job_id"])] = item
        return dict(item)

    def get(self, *, tenant_id: str, job_id: str) -> dict | None:
        row = self._rows.get(job_id)
        if row is None or row.get("tenant_id") != tenant_id:
            return None
        return dict(row)


def _payload() -> dict:
    return {
        "project_id": "prj_parse_repo",
        "supplier_id": "sup_parse_repo",
        "doc_type": "bid",
        "filename": "repo.pdf",
        "file_sha256": "abc123",
        "file_size": 128,
        "tenant_id": "tenant_parse_repo",
        "trace_id": "trace_parse_repo",
    }


def test_parse_manifest_status_is_persisted_via_repository_on_success():
    store = InMemoryStore()
    store.parse_manifests_repository = CopyingParseManifestsRepository()

    created = store.create_upload_job(_payload())
    job_id = created["job_id"]

    run = store.run_job_once(job_id=job_id, tenant_id="tenant_parse_repo")
    assert run["final_status"] == "succeeded"

    manifest = store.get_parse_manifest_for_tenant(job_id=job_id, tenant_id="tenant_parse_repo")
    assert manifest is not None
    assert manifest["status"] == "succeeded"
    assert manifest["error_code"] is None
    assert manifest["started_at"] is not None
    assert manifest["ended_at"] is not None


def test_parse_manifest_status_is_persisted_via_repository_on_retry():
    store = InMemoryStore()
    store.parse_manifests_repository = CopyingParseManifestsRepository()

    created = store.create_upload_job(_payload())
    job_id = created["job_id"]

    run = store.run_job_once(
        job_id=job_id,
        tenant_id="tenant_parse_repo",
        transient_fail=True,
        force_error_code="DOC_PARSE_SCHEMA_INVALID",
    )
    assert run["final_status"] == "retrying"

    manifest = store.get_parse_manifest_for_tenant(job_id=job_id, tenant_id="tenant_parse_repo")
    assert manifest is not None
    assert manifest["status"] == "retrying"
    assert manifest["error_code"] == "DOC_PARSE_SCHEMA_INVALID"
