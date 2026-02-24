from __future__ import annotations

import hashlib
import mimetypes

from fastapi import APIRouter, File, Form, Header, Request, Response, UploadFile

from app.errors import ApiError
from app.routes._deps import tenant_id_from_request, trace_id_from_request
from app.schemas import success_envelope
from app.store import store

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    project_id: str = Form(...),
    supplier_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )

    file_bytes = await file.read()
    payload = {
        "project_id": project_id,
        "supplier_id": supplier_id,
        "doc_type": doc_type,
        "filename": file.filename or "upload.bin",
        "file_sha256": hashlib.sha256(file_bytes).hexdigest(),
        "file_size": len(file_bytes),
        "trace_id": trace_id_from_request(request),
        "tenant_id": tenant_id_from_request(request),
    }
    from fastapi.responses import JSONResponse

    data = store.run_idempotent(
        endpoint="POST:/api/v1/documents/upload",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=payload,
        execute=lambda: store.create_upload_job(
            payload,
            file_bytes=file_bytes,
            content_type=file.content_type,
        ),
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


@router.post("/documents/{document_id}/parse")
def parse_document(
    document_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise ApiError(
            code="IDEMPOTENCY_MISSING",
            message="Idempotency-Key header is required",
            error_class="validation",
            retryable=False,
            http_status=400,
        )
    payload = {
        "document_id": document_id,
        "trace_id": trace_id_from_request(request),
        "tenant_id": tenant_id_from_request(request),
    }
    from fastapi.responses import JSONResponse

    data = store.run_idempotent(
        endpoint=f"POST:/api/v1/documents/{document_id}/parse",
        tenant_id=tenant_id_from_request(request),
        idempotency_key=idempotency_key,
        payload=payload,
        execute=lambda: store.create_parse_job(document_id=document_id, payload=payload),
    )
    return JSONResponse(
        status_code=202,
        content=success_envelope(data, trace_id_from_request(request)),
    )


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request):
    document = store.get_document_for_tenant(
        document_id=document_id,
        tenant_id=tenant_id_from_request(request),
    )
    if document is None:
        raise ApiError(
            code="DOC_NOT_FOUND",
            message="document not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    return success_envelope(
        {
            "document_id": document["document_id"],
            "project_id": document["project_id"],
            "supplier_id": document["supplier_id"],
            "doc_type": document["doc_type"],
            "filename": document["filename"],
            "status": document["status"],
        },
        trace_id_from_request(request),
    )


@router.get("/documents/{document_id}/raw")
def get_document_raw(document_id: str, request: Request):
    document = store.get_document_for_tenant(
        document_id=document_id,
        tenant_id=tenant_id_from_request(request),
    )
    if document is None:
        raise ApiError(
            code="DOC_NOT_FOUND",
            message="document not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    storage_uri = document.get("storage_uri")
    if not isinstance(storage_uri, str) or not storage_uri:
        raise ApiError(
            code="DOC_STORAGE_URI_MISSING",
            message="document storage uri missing",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    try:
        payload = store.object_storage.get_object(storage_uri=storage_uri)
    except FileNotFoundError:
        raise ApiError(
            code="DOC_STORAGE_MISSING",
            message="document object not found",
            error_class="validation",
            retryable=False,
            http_status=404,
        )
    filename = document.get("filename") or ""
    content_type, _ = mimetypes.guess_type(str(filename))
    return Response(content=payload, media_type=content_type or "application/octet-stream")


@router.get("/documents/{document_id}/chunks")
def get_document_chunks(document_id: str, request: Request):
    chunks = store.list_document_chunks_for_tenant(
        document_id=document_id,
        tenant_id=tenant_id_from_request(request),
    )
    return success_envelope(
        {
            "document_id": document_id,
            "items": chunks,
            "total": len(chunks),
        },
        trace_id_from_request(request),
    )
