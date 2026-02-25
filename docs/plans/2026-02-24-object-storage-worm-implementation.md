# Object Storage WORM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Verify and complete the Object Storage WORM implementation per `docs/design/2026-02-23-object-storage-worm-spec.md`

**Architecture:** The core implementation exists in `app/object_storage.py` with LocalObjectStorage and S3ObjectStorage backends. Integration with legal hold and storage cleanup is in `app/store_ops.py`. API endpoints are in `app/routes/internal.py`.

**Tech Stack:** Python 3.11, FastAPI, boto3 (optional), pytest

---

## Status Summary

| Section | Spec Requirement | Implementation Status |
|---------|-----------------|----------------------|
| 3.1 Interface | 9 methods | ✅ Complete |
| 3.2 URI | `object://{backend}/{bucket}/{key}` | ✅ Complete |
| 4 Key Spec | documents/reports paths | ✅ Complete |
| 5 WORM | no overwrite, block delete | ✅ Complete |
| 6 Legal Hold | impose/release/block cleanup | ✅ Complete |
| 6.1 Retention | time-based protection | ✅ Complete |
| 7 API | cleanup returns 409 | ✅ Complete |
| 8 Config | 12 env vars | ✅ Complete |
| 9 Acceptance | 5 criteria | ⚠️ Needs verification |

---

## Task 1: Verify Acceptance Criterion 1 - Upload Persistence

**Files:**
- Test: `tests/test_object_storage_worm.py`

**Step 1: Review existing test**

```python
# test_upload_persists_object_storage already exists
def test_upload_persists_object_storage(client):
    content = b"%PDF-1.4 object-storage"
    document_id = _upload_document(client, tenant_id="tenant_obj", content=content)
    doc = store.get_document_for_tenant(document_id=document_id, tenant_id="tenant_obj")
    assert doc is not None
    storage_uri = doc.get("storage_uri")
    assert isinstance(storage_uri, str) and storage_uri
    stored = store.object_storage.get_object(storage_uri=storage_uri)
    assert stored == content
```

**Step 2: Run test to verify**

Run: `pytest tests/test_object_storage_worm.py::test_upload_persists_object_storage -v`
Expected: PASS

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: acceptance 1 - upload persists to object storage"
```

---

## Task 2: Verify Acceptance Criterion 2 - Report Archival

**Files:**
- Test: `tests/test_object_storage_worm.py`

**Step 1: Review existing test**

```python
# test_report_archived_to_object_storage already exists
def test_report_archived_to_object_storage(client):
    # Creates evaluation and verifies report.json is stored
```

**Step 2: Run test to verify**

Run: `pytest tests/test_object_storage_worm.py::test_report_archived_to_object_storage -v`
Expected: PASS

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: acceptance 2 - report archived to object storage"
```

---

## Task 3: Verify Acceptance Criterion 3 - Legal Hold Blocks Cleanup

**Files:**
- Test: `tests/test_object_storage_worm.py`
- Test: `tests/test_legal_hold_api.py`

**Step 1: Review existing tests**

```python
# test_legal_hold_blocks_object_storage_cleanup exists
# test_legal_hold_lifecycle_and_cleanup_guard exists
```

**Step 2: Run tests to verify**

Run: `pytest tests/test_object_storage_worm.py::test_legal_hold_blocks_object_storage_cleanup tests/test_legal_hold_api.py::test_legal_hold_lifecycle_and_cleanup_guard -v`
Expected: PASS (both)

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: acceptance 3 - legal hold blocks cleanup"
```

---

## Task 4: Verify Acceptance Criterion 4 - Retention Blocks Cleanup

**Files:**
- Test: `tests/test_object_storage_worm.py`

**Step 1: Review existing test**

```python
# test_retention_blocks_object_storage_cleanup exists
def test_retention_blocks_object_storage_cleanup(client, monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_RETENTION_DAYS", "1")
    # Verifies cleanup returns 409 RETENTION_ACTIVE
```

**Step 2: Run test to verify**

Run: `pytest tests/test_object_storage_worm.py::test_retention_blocks_object_storage_cleanup -v`
Expected: PASS

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: acceptance 4 - retention blocks cleanup"
```

---

## Task 5: Verify Acceptance Criterion 5 - Cleanup After Release

**Files:**
- Test: `tests/test_object_storage_worm.py`
- Test: `tests/test_legal_hold_api.py`

**Step 1: Review test flow**

Both tests verify the complete lifecycle:
1. impose legal hold
2. cleanup blocked (409)
3. release with dual approval
4. cleanup succeeds
5. audit log written

**Step 2: Run full test suite**

Run: `pytest tests/test_object_storage_worm.py tests/test_legal_hold_api.py -v`
Expected: All PASS

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: acceptance 5 - cleanup after release with audit"
```

---

## Task 5.5: Verify trace_id Propagation (SSOT §2.2)

**Files:**
- Test: `tests/test_object_storage_worm.py`

**Step 1: 验证 audit log 包含 trace_id**

SSOT §2.2 要求：无 `trace_id` 的请求视为不合规请求。审计日志必须包含 trace_id。

```python
def test_cleanup_audit_log_includes_trace_id(client):
    """Audit log for storage cleanup must include trace_id (SSOT §2.2)."""
    content = b"%PDF-1.4 trace_test"
    document_id = _upload_document(client, tenant_id="tenant_trace", content=content)

    trace_id = "trace_cleanup_test_001"
    cleanup = client.post(
        "/api/v1/internal/storage/cleanup",
        headers={
            "x-internal-debug": "true",
            "x-trace-id": trace_id,
            "x-tenant-id": "tenant_trace",
        },
        json={
            "object_type": "document",
            "object_id": document_id,
            "reason": "test_cleanup",
        },
    )
    assert cleanup.status_code == 200

    # Verify audit log contains trace_id
    audit_logs = store.list_audit_logs(tenant_id="tenant_trace", action="storage_cleanup_executed")
    assert any(log.get("trace_id") == trace_id for log in audit_logs)
```

**Step 2: Run test to verify**

Run: `pytest tests/test_object_storage_worm.py::test_cleanup_audit_log_includes_trace_id -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_object_storage_worm.py && git commit -m "test: verify trace_id in storage cleanup audit (SSOT §2.2)"
```

---

## Task 5.6: Verify WORM Idempotency (SSOT §2.2)

**Files:**
- Test: `tests/test_object_storage_worm.py`

**Step 1: 验证重复 put_object 返回相同 URI**

SSOT §2.2 要求：任何写操作必须有幂等策略。WORM 模式下，重复上传应返回相同 URI 且不覆盖。

```python
def test_worm_mode_idempotent_put():
    """WORM mode should return same URI without overwriting (SSOT §2.2)."""
    from app.object_storage import LocalObjectStorage, ObjectStorageConfig

    config = ObjectStorageConfig(
        backend="local",
        bucket="test",
        root="/tmp/bea-test-worm",
        prefix="",
        worm_mode=True,
        endpoint="",
        region="",
        access_key="",
        secret_key="",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = LocalObjectStorage(config=config)
    storage.reset()

    content1 = b"original content v1"
    content2 = b"modified content v2"

    # First put
    uri1 = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=content1,
    )

    # Second put with same key - should NOT overwrite
    uri2 = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=content2,
    )

    # Same URI returned
    assert uri1 == uri2

    # Original content preserved
    stored = storage.get_object(storage_uri=uri1)
    assert stored == content1
    assert stored != content2
```

**Step 2: Run test to verify**

Run: `pytest tests/test_object_storage_worm.py::test_worm_mode_idempotent_put -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_object_storage_worm.py && git commit -m "test: verify WORM idempotency (SSOT §2.2)"
```

---

## Task 6: Add Integration Test for S3 Backend (Optional)

**Files:**
- Create: `tests/test_s3_object_storage.py`
- Modify: `tests/conftest.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from app.object_storage import S3ObjectStorage, ObjectStorageConfig


@pytest.fixture
def mock_s3_client():
    with patch("app.object_storage.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.session.Session.return_value.client.return_value = mock_client
        yield mock_client


def test_s3_put_object_with_worm_mode(mock_s3_client):
    config = ObjectStorageConfig(
        backend="s3",
        bucket="test-bucket",
        root="/tmp",
        prefix="",
        worm_mode=True,
        endpoint="http://localhost:9000",
        region="us-east-1",
        access_key="key",
        secret_key="secret",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = S3ObjectStorage(config=config)

    mock_s3_client.head_object.side_effect = Exception("Not found")

    uri = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=b"content",
        content_type="application/pdf",
    )

    assert uri == "object://s3/test-bucket/tenants/tenant_1/documents/doc_1/raw/test.pdf"
    mock_s3_client.put_object.assert_called_once()
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_s3_object_storage.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_s3_object_storage.py && git commit -m "test: add S3 backend integration test"
```

---

## Task 7: Run Full Test Suite

**Files:**
- All test files

**Step 1: Run all object storage related tests**

Run: `pytest tests/test_object_storage_worm.py tests/test_legal_hold_api.py -v --tb=short`
Expected: All PASS

**Step 2: Run store operations tests**

Run: `pytest tests/test_store*.py -v --tb=short`
Expected: All PASS

**Step 3: Commit verification**

```bash
git add -A && git commit -m "verify: all object storage tests pass"
```

---

## Task 8: Update Design Document Status

**Files:**
- Modify: `docs/design/2026-02-23-object-storage-worm-spec.md`

**Step 1: Update status to Verified**

Change:
```markdown
> 状态：Active
```

To:
```markdown
> 状态：Verified
> 实现完成：2026-02-24
> 验收测试：全部通过
```

**Step 2: Add implementation notes section**

Add at end of file:
```markdown
## 11. 实现状态

| 组件 | 文件 | 状态 |
|------|------|------|
| LocalObjectStorage | app/object_storage.py | ✅ |
| S3ObjectStorage | app/object_storage.py | ✅ |
| Legal Hold Integration | app/store_ops.py | ✅ |
| Retention Support | app/object_storage.py | ✅ |
| API Endpoints | app/routes/internal.py | ✅ |
| Unit Tests | tests/test_object_storage_worm.py | ✅ |
| API Tests | tests/test_legal_hold_api.py | ✅ |
```

**Step 3: Commit**

```bash
git add docs/design/2026-02-23-object-storage-worm-spec.md
git commit -m "docs: mark object storage WORM spec as verified"
```

---

## Verification Checklist

- [ ] All 5 acceptance criteria verified
- [ ] All tests pass
- [ ] Design document updated
- [ ] trace_id propagation verified (SSOT §2.2)
- [ ] WORM idempotency verified (SSOT §2.2)
- [ ] No TODO/TBD remaining in implementation

---

## SSOT Alignment Summary

| SSOT Section | Requirement | Plan Coverage |
|--------------|-------------|---------------|
| §2.2 | trace_id 贯穿 | ✅ Task 5.5 |
| §2.2 | 幂等策略 | ✅ Task 5.6 |
| §2.3 | legal hold 不可自动清理 | ✅ Task 3, 4, 5 |
| §2.3 | 高风险动作双人复核 | ✅ Task 5 |
| §4.1 | Object Storage(WORM) | ✅ All Tasks |
| §7.3 | legal hold 违规删除 = 0 | ✅ Task 3, 4 |
