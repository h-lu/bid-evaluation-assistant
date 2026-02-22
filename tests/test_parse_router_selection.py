from io import BytesIO


def test_parse_manifest_selects_mineru_for_pdf(client):
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_router", "supplier_id": "sup_router", "doc_type": "bid"},
        files={"file": ("router.pdf", BytesIO(b"%PDF-1.4 router"), "application/pdf")},
        headers={"Idempotency-Key": "idem_router_pdf_upload"},
    )
    document_id = upload.json()["data"]["document_id"]

    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_router_pdf_parse"},
    )
    job_id = parse.json()["data"]["job_id"]

    manifest = client.get(
        f"/api/v1/internal/parse-manifests/{job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert manifest.status_code == 200
    data = manifest.json()["data"]
    assert data["selected_parser"] == "mineru"
    assert data["fallback_chain"] == ["docling", "ocr"]


def test_parse_manifest_selects_docling_for_docx(client):
    upload = client.post(
        "/api/v1/documents/upload",
        data={"project_id": "prj_router", "supplier_id": "sup_router", "doc_type": "attachment"},
        files={
            "file": (
                "router.docx",
                BytesIO(b"PK\x03\x04 fake-docx"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Idempotency-Key": "idem_router_docx_upload"},
    )
    document_id = upload.json()["data"]["document_id"]

    parse = client.post(
        f"/api/v1/documents/{document_id}/parse",
        headers={"Idempotency-Key": "idem_router_docx_parse"},
    )
    job_id = parse.json()["data"]["job_id"]

    manifest = client.get(
        f"/api/v1/internal/parse-manifests/{job_id}",
        headers={"x-internal-debug": "true"},
    )
    assert manifest.status_code == 200
    data = manifest.json()["data"]
    assert data["selected_parser"] == "docling"
    assert data["fallback_chain"] == ["ocr"]
