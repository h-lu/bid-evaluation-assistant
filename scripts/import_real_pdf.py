#!/usr/bin/env python3
"""Import a real PDF document for testing.

Usage:
    python scripts/import_real_pdf.py data/your_file.pdf
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

# Configuration
API_BASE = os.environ.get("API_BASE", "http://localhost:8010")
TENANT_ID = os.environ.get("TENANT_ID", "test_tenant")
JWT_SECRET = os.environ.get(
    "JWT_SHARED_SECRET", "ci_test_secret_key_32bytes_for_sha256!!"
)
JWT_ISSUER = os.environ.get("JWT_ISSUER", "http://jwks:8000/")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "bea-api")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _build_jwt_token(*, secret: str, tenant_id: str, ttl_minutes: int = 60) -> str:
    """Build a JWT token for authentication."""
    now = datetime.now(UTC)
    claims = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": f"user_{tenant_id}",
        "tenant_id": tenant_id,
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
        "iat": int(now.timestamp()),
    }

    header = {"alg": "HS256", "typ": "JWT"}
    header_raw = _b64url(json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    payload_raw = _b64url(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_raw}.{payload_raw}.{_b64url(signature)}"


def get_headers(token: str) -> dict:
    """Get common headers including trace_id and auth."""
    return {
        "x-trace-id": str(uuid.uuid4()),
        "Authorization": f"Bearer {token}",
    }


def upload_pdf(pdf_path: str, token: str) -> dict:
    """Upload PDF to the API."""
    url = f"{API_BASE}/api/v1/documents/upload"

    with open(pdf_path, "rb") as f:
        files = {"file": (Path(pdf_path).name, f, "application/pdf")}
        data = {"tenant_id": TENANT_ID}

        print(f"Uploading {pdf_path}...")
        response = requests.post(url, files=files, data=data, headers=get_headers(token))

    if response.status_code != 200:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

    return response.json()


def trigger_parse(document_id: str, token: str) -> dict:
    """Trigger document parsing."""
    url = f"{API_BASE}/api/v1/documents/{document_id}/parse"

    print(f"Triggering parse for document {document_id}...")
    response = requests.post(url, json={"tenant_id": TENANT_ID}, headers=get_headers(token))

    if response.status_code not in (200, 202):
        raise Exception(f"Parse trigger failed: {response.status_code} - {response.text}")

    return response.json()


def check_job_status(job_id: str, token: str) -> dict:
    """Check job status."""
    url = f"{API_BASE}/api/v1/jobs/{job_id}"

    response = requests.get(url, params={"tenant_id": TENANT_ID}, headers=get_headers(token))

    if response.status_code != 200:
        raise Exception(f"Status check failed: {response.status_code} - {response.text}")

    return response.json()


def wait_for_completion(job_id: str, token: str, timeout: int = 600) -> dict:
    """Wait for job to complete."""
    print(f"Waiting for job {job_id} to complete (timeout: {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        status = check_job_status(job_id, token)
        state = status.get("status", "unknown")
        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed}s] Job status: {state}")

        if state in ("completed", "failed"):
            return status

        time.sleep(5)

    raise TimeoutError(f"Job did not complete within {timeout} seconds")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_real_pdf.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    # Generate JWT token
    token = _build_jwt_token(secret=JWT_SECRET, tenant_id=TENANT_ID)

    print(f"API Base: {API_BASE}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"PDF: {pdf_path}")
    print(f"Size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
    print("-" * 50)

    # Step 1: Upload
    upload_result = upload_pdf(pdf_path, token)
    document_id = upload_result.get("document_id")
    print(f"Document ID: {document_id}")
    print(f"Storage URI: {upload_result.get('storage_uri')}")

    # Step 2: Trigger parse
    parse_result = trigger_parse(document_id, token)
    job_id = parse_result.get("job_id")
    print(f"Job ID: {job_id}")

    # Step 3: Wait for completion
    final_status = wait_for_completion(job_id, token, timeout=600)

    print("-" * 50)
    print(f"Final status: {final_status.get('status')}")

    if final_status.get("status") == "completed":
        print("Document successfully imported and parsed!")
        print(f"  Document ID: {document_id}")
        print(f"  Job ID: {job_id}")

        # Get document details
        doc_url = f"{API_BASE}/api/v1/documents/{document_id}"
        doc_response = requests.get(doc_url, params={"tenant_id": TENANT_ID}, headers=get_headers(token))
        if doc_response.status_code == 200:
            doc_data = doc_response.json()
            print(f"  Chunks count: {doc_data.get('chunks_count', 'N/A')}")
    else:
        print(f"Parse failed: {final_status.get('error', 'Unknown error')}")

    return document_id, job_id


if __name__ == "__main__":
    main()
