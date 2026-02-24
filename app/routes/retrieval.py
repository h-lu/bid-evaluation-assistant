from __future__ import annotations

from fastapi import APIRouter, Request

from app.errors import ApiError
from app.routes._deps import tenant_id_from_request, trace_id_from_request
from app.schemas import RetrievalQueryRequest, success_envelope
from app.store import store

router = APIRouter(prefix="/api/v1", tags=["retrieval"])


@router.post("/retrieval/query")
def retrieval_query(payload: RetrievalQueryRequest, request: Request):
    data = store.retrieval_query(
        tenant_id=tenant_id_from_request(request),
        project_id=payload.project_id,
        supplier_id=payload.supplier_id,
        query=payload.query,
        query_type=payload.query_type,
        high_risk=payload.high_risk,
        top_k=payload.top_k,
        doc_scope=list(payload.doc_scope),
        enable_rerank=payload.enable_rerank,
        must_include_terms=payload.must_include_terms,
        must_exclude_terms=payload.must_exclude_terms,
    )
    return success_envelope(data, trace_id_from_request(request))


@router.post("/retrieval/preview")
def retrieval_preview(payload: RetrievalQueryRequest, request: Request):
    data = store.retrieval_preview(
        tenant_id=tenant_id_from_request(request),
        project_id=payload.project_id,
        supplier_id=payload.supplier_id,
        query=payload.query,
        query_type=payload.query_type,
        high_risk=payload.high_risk,
        top_k=payload.top_k,
        doc_scope=list(payload.doc_scope),
        enable_rerank=payload.enable_rerank,
        must_include_terms=payload.must_include_terms,
        must_exclude_terms=payload.must_exclude_terms,
    )
    return success_envelope(data, trace_id_from_request(request))


@router.get("/citations/{chunk_id}/source")
def get_citation_source(chunk_id: str, request: Request):
    source = store.get_citation_source(
        chunk_id=chunk_id,
        tenant_id=tenant_id_from_request(request),
    )
    if source is None:
        raise ApiError(
            code="CITATION_NOT_FOUND",
            message="citation source not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(source, trace_id_from_request(request))
