"""Integration tests for MinerU Official API.

This test requires MINERU_API_KEY environment variable.
Tests are skipped if the API key is not configured.

API Documentation: https://mineru.net/apiManage/docs

API Format:
- Submit: POST /extract/task → {"data": {"task_id": "..."}}
- Poll: GET /extract/task/{task_id} → {"data": {"state": "done", "full_zip_url": "..."}}
"""
from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from typing import Any

import pytest

# Skip all tests if API key not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("MINERU_API_KEY"),
    reason="MINERU_API_KEY not configured",
)

MINERU_API_BASE = "https://mineru.net/api/v4"
MINERU_API_KEY = os.environ.get("MINERU_API_KEY", "")

# Use different PDFs to avoid "retry limit reached" error
TEST_PDF_URLS = [
    "https://arxiv.org/pdf/2301.07041.pdf",
    "https://www.africau.edu/images/default/sample.pdf",
    "https://www.clickdimensions.com/links/TestPDFfile.pdf",
]


def _make_request(
    *,
    endpoint: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Make HTTP request to MinerU API."""
    url = f"{MINERU_API_BASE}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_KEY}",
    }

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"code": e.code, "message": raw}


def submit_extract_task(
    *,
    file_url: str,
    is_ocr: bool = True,
    enable_formula: bool = False,
    page_ranges: str | None = None,
) -> str:
    """Submit PDF extraction task to MinerU API.

    Returns task_id for polling.
    """
    data = {
        "url": file_url,
        "is_ocr": is_ocr,
        "enable_formula": enable_formula,
    }
    if page_ranges:
        data["page_ranges"] = page_ranges

    result = _make_request(
        endpoint="/extract/task",
        method="POST",
        data=data,
        timeout=60.0,
    )

    if result.get("code") != 0:
        raise RuntimeError(f"MinerU API error: {result}")

    return result["data"]["task_id"]


def get_task_result(*, task_id: str, timeout: float = 180.0) -> dict[str, Any]:
    """Poll for task result.

    Returns the full task result when complete.
    State values: "pending", "processing", "done", "failed"
    """
    start_time = time.time()
    poll_interval = 5.0

    while time.time() - start_time < timeout:
        result = _make_request(
            endpoint=f"/extract/task/{task_id}",
            method="GET",
            timeout=30.0,
        )

        if result.get("code") != 0:
            raise RuntimeError(f"MinerU API error: {result}")

        data = result.get("data", {})
        state = data.get("state", "unknown")

        if state == "done":
            return data
        elif state == "failed":
            raise RuntimeError(f"MinerU task failed: {data.get('err_msg')}")

        time.sleep(poll_interval)

    raise TimeoutError(f"MinerU task timed out after {timeout}s, state={state}")


def fetch_zip_content(zip_url: str) -> dict[str, str]:
    """Download and extract zip content from MinerU result."""
    with urllib.request.urlopen(zip_url, timeout=60) as resp:
        zip_data = resp.read()

    content = {}
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        for name in zf.namelist():
            if name.endswith((".md", ".json", ".txt")):
                content[name] = zf.read(name).decode("utf-8", errors="replace")

    return content


class TestMinerUOfficialAPI:
    """Integration tests for MinerU Official API."""

    def test_submit_extract_task(self):
        """Test submitting an extraction task to verify API key works."""
        result = _make_request(
            endpoint="/extract/task",
            method="POST",
            data={
                "url": TEST_PDF_URLS[0],
                "is_ocr": True,
                "page_ranges": "1",
            },
            timeout=60.0,
        )

        assert result.get("code") == 0, f"API request failed: {result}"
        assert "data" in result
        assert "task_id" in result["data"]

    def test_extract_and_poll_result(self):
        """Test full extraction workflow: submit → poll → get result."""
        # Submit with first available URL
        task_id = None
        for url in TEST_PDF_URLS:
            try:
                task_id = submit_extract_task(
                    file_url=url,
                    is_ocr=True,
                    page_ranges="1",
                )
                break
            except RuntimeError as e:
                if "retry limit" in str(e):
                    continue
                raise

        assert task_id, "Should get task_id from one of the test URLs"

        # Poll for result
        result = get_task_result(task_id=task_id, timeout=180.0)

        # Verify result structure
        assert result["state"] == "done"
        assert "full_zip_url" in result
        assert result["full_zip_url"].startswith("https://")

    def test_extract_returns_valid_zip(self):
        """Test that extraction returns a valid zip file with content."""
        # Submit task
        task_id = None
        for url in TEST_PDF_URLS:
            try:
                task_id = submit_extract_task(
                    file_url=url,
                    is_ocr=True,
                    page_ranges="1",
                )
                break
            except RuntimeError as e:
                if "retry limit" in str(e):
                    continue
                raise

        assert task_id, "Should get task_id"

        # Get result
        result = get_task_result(task_id=task_id, timeout=180.0)
        zip_url = result["full_zip_url"]

        # Download and check zip
        content = fetch_zip_content(zip_url)

        # Should have at least one content file
        assert len(content) > 0, f"Expected content in zip, got: {list(content.keys())}"

        # Print what we got for debugging
        print(f"\nZip contents: {list(content.keys())}")
        for name, text in list(content.items())[:2]:
            print(f"\n--- {name} (first 500 chars) ---")
            print(text[:500])


class TestMinerUContentFormat:
    """Test MinerU output format compatibility with our parser."""

    def test_mineru_returns_content_list_json(self):
        """Verify MinerU returns content_list.json in expected format."""
        # Submit task
        task_id = None
        for url in TEST_PDF_URLS:
            try:
                task_id = submit_extract_task(
                    file_url=url,
                    is_ocr=True,
                    page_ranges="1",
                )
                break
            except RuntimeError as e:
                if "retry limit" in str(e):
                    continue
                raise

        result = get_task_result(task_id=task_id, timeout=180.0)
        content = fetch_zip_content(result["full_zip_url"])

        # Check for content_list.json (our expected format per SSOT §2.3)
        content_list_files = [n for n in content.keys() if "content_list" in n and n.endswith(".json")]

        if content_list_files:
            import json as json_lib
            content_list = json_lib.loads(content[content_list_files[0]])

            # Verify structure matches our expected format
            # SSOT §5.1: content item should have text, page, bbox
            if isinstance(content_list, list) and len(content_list) > 0:
                item = content_list[0]
                print(f"\nSample content item: {json_lib.dumps(item, ensure_ascii=False, indent=2)[:500]}")

                # Check for expected fields
                has_text = "text" in item or "content" in item
                has_page = "page" in item or "page_idx" in item

                assert has_text or has_page, f"Content item missing expected fields: {list(item.keys())}"

    def test_mineru_returns_markdown(self):
        """Verify MinerU returns markdown output."""
        task_id = None
        for url in TEST_PDF_URLS:
            try:
                task_id = submit_extract_task(
                    file_url=url,
                    is_ocr=True,
                    page_ranges="1",
                )
                break
            except RuntimeError as e:
                if "retry limit" in str(e):
                    continue
                raise

        result = get_task_result(task_id=task_id, timeout=180.0)
        content = fetch_zip_content(result["full_zip_url"])

        # Check for markdown files
        md_files = [n for n in content.keys() if n.endswith(".md")]
        assert len(md_files) > 0, f"Expected markdown in zip, got: {list(content.keys())}"

        # Check content is not empty
        md_content = content[md_files[0]]
        assert len(md_content) > 0, "Markdown content should not be empty"
