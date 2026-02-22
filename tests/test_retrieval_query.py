from app.store import store


def _seed_retrieval_sources():
    store.register_citation_source(
        chunk_id="ck_retr_a1",
        source={
            "chunk_id": "ck_retr_a1",
            "document_id": "doc_a1",
            "tenant_id": "tenant_a",
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "doc_type": "bid",
            "page": 3,
            "bbox": [10, 20, 120, 160],
            "text": "delivery period is 30 days",
            "context": "delivery clause",
            "score_raw": 0.72,
        },
    )
    store.register_citation_source(
        chunk_id="ck_retr_a2",
        source={
            "chunk_id": "ck_retr_a2",
            "document_id": "doc_a2",
            "tenant_id": "tenant_a",
            "project_id": "prj_x",
            "supplier_id": "sup_a",
            "doc_type": "attachment",
            "page": 7,
            "bbox": [15, 30, 140, 180],
            "text": "warranty period is 12 months",
            "context": "warranty clause",
            "score_raw": 0.81,
        },
    )
    store.register_citation_source(
        chunk_id="ck_retr_b1",
        source={
            "chunk_id": "ck_retr_b1",
            "document_id": "doc_b1",
            "tenant_id": "tenant_b",
            "project_id": "prj_a",
            "supplier_id": "sup_b",
            "doc_type": "bid",
            "page": 1,
            "bbox": [5, 10, 80, 90],
            "text": "cross tenant data",
            "context": "blocked",
            "score_raw": 0.99,
        },
    )


def test_retrieval_query_selects_mode_for_relation_and_filters_scope(client):
    _seed_retrieval_sources()

    resp = client.post(
        "/api/v1/retrieval/query",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "show delivery obligations",
            "query_type": "relation",
            "top_k": 20,
            "doc_scope": ["bid"],
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["selected_mode"] == "global"
    assert data["index_name"] == "lightrag:tenant_a:prj_a"
    assert data["degraded"] is False
    assert data["constraints_preserved"] is True
    assert data["constraint_diff"] == []
    assert data["rewrite_reason"]
    assert data["rewritten_query"]
    assert data["total"] == 1
    assert data["items"][0]["chunk_id"] == "ck_retr_a1"
    metadata = data["items"][0]["metadata"]
    assert metadata["tenant_id"] == "tenant_a"
    assert metadata["project_id"] == "prj_a"
    assert metadata["supplier_id"] == "sup_a"
    assert metadata["document_id"] == "doc_a1"
    assert metadata["doc_type"] == "bid"


def test_retrieval_query_high_risk_forces_mix_mode(client):
    _seed_retrieval_sources()

    resp = client.post(
        "/api/v1/retrieval/query",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "summarize price constraints",
            "query_type": "fact",
            "high_risk": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["selected_mode"] == "mix"


def test_retrieval_query_rejects_invalid_query_type(client):
    resp = client.post(
        "/api/v1/retrieval/query",
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "bad type",
            "query_type": "unknown",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "REQ_VALIDATION_FAILED"


def test_retrieval_preview_returns_minimal_evidence_fields(client):
    _seed_retrieval_sources()

    resp = client.post(
        "/api/v1/retrieval/preview",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "preview delivery evidence",
            "query_type": "relation",
            "doc_scope": ["bid"],
        },
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["selected_mode"] == "global"
    assert data["index_name"] == "lightrag:tenant_a:prj_a"
    assert data["total"] == 1
    item = data["items"][0]
    assert item["chunk_id"] == "ck_retr_a1"
    assert item["document_id"] == "doc_a1"
    assert item["page"] == 3
    assert item["bbox"] == [10, 20, 120, 160]
    assert item["text"] == "delivery period is 30 days"


def test_retrieval_preview_uses_hybrid_for_summary(client):
    _seed_retrieval_sources()
    resp = client.post(
        "/api/v1/retrieval/preview",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "summarize evidence",
            "query_type": "summary",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["selected_mode"] == "hybrid"


def test_retrieval_query_applies_term_constraints(client):
    _seed_retrieval_sources()
    resp = client.post(
        "/api/v1/retrieval/query",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "delivery and warranty",
            "query_type": "fact",
            "must_include_terms": ["delivery"],
            "must_exclude_terms": ["warranty"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["chunk_id"] == "ck_retr_a1"


def test_retrieval_query_degrades_when_rerank_disabled(client):
    _seed_retrieval_sources()
    resp = client.post(
        "/api/v1/retrieval/query",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "delivery",
            "query_type": "fact",
            "enable_rerank": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["degraded"] is True
    assert data["items"][0]["score_rerank"] is None


def test_retrieval_query_exposes_rewrite_and_constraint_fields(client):
    _seed_retrieval_sources()
    resp = client.post(
        "/api/v1/retrieval/query",
        headers={"x-tenant-id": "tenant_a"},
        json={
            "project_id": "prj_a",
            "supplier_id": "sup_a",
            "query": "  delivery   obligations ",
            "query_type": "relation",
            "must_include_terms": ["delivery"],
            "must_exclude_terms": ["warranty"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["rewritten_query"]
    assert data["rewrite_reason"] == "normalize_whitespace_and_constraints"
    assert data["constraints_preserved"] is True
    assert data["constraint_diff"] == []
