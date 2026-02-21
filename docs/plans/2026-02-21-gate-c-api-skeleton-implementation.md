# Gate C API Skeleton Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runnable FastAPI skeleton that satisfies Gate B API contracts and core async job workflow behavior.

**Architecture:** Use a small FastAPI app with in-memory repositories for jobs, idempotency records, and citation source data. Keep response/error envelopes aligned with the OpenAPI baseline. Validate behavior with pytest contract tests before writing implementation code (TDD).

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Uvicorn, pytest, httpx, anyio

---

### Task 1: Project Skeleton and Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `tests/conftest.py`
- Test: `tests/test_health.py`

**Step 1: Write the failing test**

```python
def test_health_endpoint(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL because app/route does not exist.

**Step 3: Write minimal implementation**

1. Add FastAPI app factory.
2. Add `GET /healthz` returning `{"status":"ok"}`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml app tests
git commit -m "feat: scaffold fastapi app with health endpoint"
```

### Task 2: Response Envelope and Error Model

**Files:**
- Create: `app/schemas.py`
- Create: `app/errors.py`
- Modify: `app/main.py`
- Test: `tests/test_response_envelope.py`

**Step 1: Write the failing tests**

1. Assert every success response includes `meta.trace_id`.
2. Assert errors follow `{success:false,error:{code,message,retryable,class},meta}`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_response_envelope.py -v`
Expected: FAIL due missing envelope helpers.

**Step 3: Write minimal implementation**

1. Add success/error envelope builders.
2. Add request-scoped trace id middleware.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_response_envelope.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app tests
git commit -m "feat: add unified response and error envelope with trace id"
```

### Task 3: Job Store and Idempotency Guard

**Files:**
- Create: `app/store.py`
- Modify: `app/schemas.py`
- Modify: `app/errors.py`
- Test: `tests/test_idempotency.py`

**Step 1: Write the failing tests**

1. Missing `Idempotency-Key` on write endpoint -> `400 IDEMPOTENCY_MISSING`.
2. Same key + same body -> same accepted payload.
3. Same key + different body -> `409 IDEMPOTENCY_CONFLICT`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_idempotency.py -v`
Expected: FAIL before idempotency implementation exists.

**Step 3: Write minimal implementation**

1. In-memory idempotency record keyed by `(endpoint, key)`.
2. Stable request fingerprint for conflict detection.
3. Reuse accepted response for idempotent replay.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_idempotency.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app tests
git commit -m "feat: implement idempotency guard for write endpoints"
```

### Task 4: Core Contract Endpoints

**Files:**
- Modify: `app/main.py`
- Modify: `app/schemas.py`
- Modify: `app/store.py`
- Test: `tests/test_api_contract_core.py`

**Step 1: Write the failing tests**

1. `POST /api/v1/documents/upload` returns `202` with `document_id/job_id/status/next`.
2. `POST /api/v1/evaluations` returns `202` with `evaluation_id/job_id/status`.
3. `GET /api/v1/jobs/{job_id}` returns job data with allowed status values.
4. Unknown job id returns error envelope.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_contract_core.py -v`
Expected: FAIL for missing routes/fields.

**Step 3: Write minimal implementation**

1. Add upload/evaluation/job routes.
2. Create jobs in store with initial `queued` status.
3. Return envelopes aligned to OpenAPI baseline.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_contract_core.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app tests
git commit -m "feat: add async submission and job query contract endpoints"
```

### Task 5: HITL Resume and Citation Source Endpoints

**Files:**
- Modify: `app/main.py`
- Modify: `app/store.py`
- Test: `tests/test_resume_and_citation.py`

**Step 1: Write the failing tests**

1. Valid resume token returns `202` with resume job id.
2. Invalid resume token returns `409 WF_INTERRUPT_RESUME_INVALID`.
3. Citation source endpoint returns `document_id/page/bbox/text/context`.
4. Unknown citation chunk returns error envelope.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_resume_and_citation.py -v`
Expected: FAIL due missing handlers/data.

**Step 3: Write minimal implementation**

1. Add resume token registry and validation.
2. Add citation source in-memory dataset and lookup route.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_resume_and_citation.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add app tests
git commit -m "feat: add resume and citation source contract endpoints"
```

### Task 6: Full Verification and Documentation Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md`
- Modify: `docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md`
- Test: `tests/*.py`

**Step 1: Run full tests**

Run: `pytest -v`
Expected: all tests pass.

**Step 2: Run docs consistency checks**

Run:

```bash
rg -n 'recovered|TODO|TBD|mermaid' README.md docs -g '*.md'
refs=$(rg -o --no-filename '`docs[^`]+\\.(md|yaml)`' README.md docs AGENTS.md CLAUDE.md -g '*.md' | tr -d '`' | sort -u | rg -v '[*?\\[\\]]')
while IFS= read -r p; do [ -z "$p" ] || [ -f "$p" ] || echo "MISSING $p"; done <<< "$refs"
```

Expected: no forbidden markers, no missing refs.

**Step 3: Commit**

```bash
git add README.md docs app tests pyproject.toml
git commit -m "feat: deliver gate-c api skeleton with contract tests"
```
