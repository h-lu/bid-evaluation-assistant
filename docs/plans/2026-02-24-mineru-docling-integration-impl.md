# MinerU/Docling 集成实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补充解析器集成缺失功能，对齐 SSOT §3 (fallback 2跳限制) 和 §2.2 (trace_id)

**Architecture:** 复用现有 `parser_adapters.py` 架构，添加 2跳限制和 trace_id 支持。创建独立解析器服务。

**Tech Stack:** Python 3.11, FastAPI, httpx, pytest

**Design Doc:** `docs/plans/2026-02-24-mineru-docling-integration-design.md`

---

## Phase 1: 修改现有代码 (高优先级)

### Task 1.1: 添加 Fallback 2跳限制

**Files:**
- Modify: `app/parser_adapters.py`

**Step 1: 编写失败测试**

```python
# tests/test_parser_fallback_limit.py

def test_fallback_chain_respects_2_hop_limit():
    """SSOT §3: fallback 链最多 2 跳"""
    from app.parser_adapters import ParserAdapterRegistry, ParseRoute, StubParserAdapter

    # 创建 4 个解析器，只有最后一个能成功
    adapters = {
        "parser_a": FailingParserAdapter(name="parser_a"),
        "parser_b": FailingParserAdapter(name="parser_b"),
        "parser_c": FailingParserAdapter(name="parser_c"),
        "parser_d": SuccessParserAdapter(name="parser_d"),  # 这个能成功
    }
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="parser_a",
        fallback_chain=["parser_b", "parser_c", "parser_d"],  # 4 个候选
        parser_version="v1",
    )

    # SSOT 约束: 只尝试前 3 个 (selected + 2 fallbacks)
    # parser_d 不应该被尝试
    with pytest.raises(ApiError, match="PARSER_FALLBACK_EXHAUSTED"):
        registry.parse_with_route(
            route=route,
            document_id="doc_1",
            default_text="test",
        )
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_parser_fallback_limit.py -v`
Expected: FAIL - 当前没有 2 跳限制

**Step 3: 修改 parse_with_route 添加限制**

修改 `app/parser_adapters.py:234-265`:

```python
def parse_with_route(
    self,
    *,
    route: ParseRoute,
    document_id: str,
    default_text: str,
) -> dict[str, object]:
    candidates = [route.selected_parser, *route.fallback_chain]

    # SSOT §3 约束: fallback 链最多 2 跳
    # selected_parser + 最多 2 个 fallback = 最多 3 次尝试
    max_attempts = min(3, len(candidates))
    candidates = candidates[:max_attempts]

    last_error: ApiError | None = None
    for parser_name in candidates:
        adapter = self._adapters.get(parser_name)
        if adapter is None:
            continue
        try:
            return adapter.parse(
                document_id=document_id,
                default_text=default_text,
                parser_version=route.parser_version,
            )
        except ApiError as exc:
            last_error = exc
            continue

    raise ApiError(
        code="PARSER_FALLBACK_EXHAUSTED",
        message=(
            f"no parser adapter available after {len(candidates)} attempts: {last_error.code}"
            if last_error is not None
            else "no parser adapter available"
        ),
        error_class="transient",
        retryable=True,
        http_status=503,
    )
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_parser_fallback_limit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/parser_adapters.py tests/test_parser_fallback_limit.py
git commit -m "feat(parsers): add fallback 2-hop limit per SSOT §3

SSOT §3 约束: fallback 链最多 2 跳

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 1.2: 添加 trace_id 到解析流程

**Files:**
- Modify: `app/parser_adapters.py`
- Test: `tests/test_parser_trace_id.py`

**Step 1: 编写测试**

```python
# tests/test_parser_trace_id.py

def test_parse_with_route_accepts_trace_id():
    """SSOT §2.2: trace_id 贯穿所有操作"""
    from app.parser_adapters import ParserAdapterRegistry, ParseRoute, StubParserAdapter

    adapters = {"stub": StubParserAdapter(name="stub", section="test")}
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="stub",
        fallback_chain=[],
        parser_version="v1",
    )

    # trace_id 应该被接受（即使 stub adapter 不使用它）
    result = registry.parse_with_route(
        route=route,
        document_id="doc_1",
        default_text="test",
        trace_id="trace_123",  # 新增参数
    )

    assert result is not None
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_parser_trace_id.py -v`
Expected: FAIL - parse_with_route 不接受 trace_id

**Step 3: 修改 ParserAdapter Protocol**

```python
# app/parser_adapters.py

class ParserAdapter(Protocol):
    name: str
    version: str

    def parse(
        self,
        *,
        document_id: str,
        default_text: str,
        parser_version: str,
        trace_id: str | None = None,  # 新增
    ) -> dict[str, object]: ...
```

**Step 4: 修改 parse_with_route**

```python
def parse_with_route(
    self,
    *,
    route: ParseRoute,
    document_id: str,
    default_text: str,
    trace_id: str | None = None,  # 新增
) -> dict[str, object]:
    ...
    for parser_name in candidates:
        adapter = self._adapters.get(parser_name)
        if adapter is None:
            continue
        try:
            return adapter.parse(
                document_id=document_id,
                default_text=default_text,
                parser_version=route.parser_version,
                trace_id=trace_id,  # 传递
            )
        except ApiError as exc:
            last_error = exc
            continue
```

**Step 5: 更新所有 Adapter 实现**

更新 `StubParserAdapter`, `HttpParserAdapter`, `LocalParserAdapter`:

```python
def parse(
    self,
    *,
    document_id: str,
    default_text: str,
    parser_version: str,
    trace_id: str | None = None,  # 新增
) -> dict[str, object]:
    # trace_id 可用于日志记录或传递给外部服务
    ...
```

**Step 6: 运行测试验证通过**

Run: `pytest tests/test_parser_trace_id.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add app/parser_adapters.py tests/test_parser_trace_id.py
git commit -m "feat(parsers): add trace_id to parse flow per SSOT §2.2

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: 创建 OCR Fallback 服务

### Task 2.1: 创建 OCR 服务目录

**Files:**
- Create: `services/ocr/`

**Step 1: 创建目录**

```bash
mkdir -p services/ocr
```

**Step 2: 验证**

Run: `ls -la services/ocr`
Expected: 目录存在

---

### Task 2.2: 创建 OCR 服务

**Files:**
- Create: `services/ocr/ocr_service.py`

**Step 1: 编写测试**

```python
# services/ocr/test_ocr_service.py

def test_health_endpoint():
    from ocr_service import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_parse_endpoint_returns_content():
    from ocr_service import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    files = {"file": ("test.txt", b"Hello World", "text/plain")}
    resp = client.post("/v1/parse", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "content_list" in data
    assert "full_md" in data
```

**Step 2: 运行测试验证失败**

Run: `cd services/ocr && python -m pytest test_ocr_service.py -v`
Expected: FAIL

**Step 3: 实现 OCR 服务**

```python
# services/ocr/ocr_service.py
"""OCR Fallback Service using PaddleOCR."""
from __future__ import annotations

import tempfile
from typing import Any

import uvicorn
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

app = FastAPI(title="OCR Parser Service", version="1.0.0")


class ContentItem(BaseModel):
    text: str
    type: str = "text"
    page_idx: int = 0
    bbox: list[float] = [0.0, 0.0, 1.0, 1.0]


class ParseResponse(BaseModel):
    content_list: list[ContentItem]
    full_md: str
    metadata: dict[str, Any]


@app.get("/health")
async def health():
    return {"status": "ok", "version": "ocr-1.0.0"}


@app.post("/v1/parse", response_model=ParseResponse)
async def parse_document(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "unknown"

    text_content = await _extract_text_with_ocr(content, filename)

    content_list = [
        ContentItem(text=text_content, type="text", page_idx=0)
    ]

    return ParseResponse(
        content_list=content_list,
        full_md=text_content,
        metadata={"filename": filename, "parser": "ocr"},
    )


async def _extract_text_with_ocr(content: bytes, filename: str) -> str:
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = ocr.ocr(tmp_path, cls=True)

        text_parts = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text_parts.append(line[1][0])

        return "\n".join(text_parts) if text_parts else f"[OCR] {filename}"
    except ImportError:
        return f"[OCR fallback] {filename}: {len(content)} bytes"
    except Exception as e:
        return f"[OCR error] {str(e)}"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 4: 运行测试验证通过**

Run: `cd services/ocr && python -m pytest test_ocr_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/ocr/
git commit -m "feat(ocr): add OCR fallback service

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2.3: 创建 OCR Dockerfile

**Files:**
- Create: `services/ocr/Dockerfile`
- Create: `services/ocr/requirements.txt`

**Step 1: 创建 requirements.txt**

```txt
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.0.0
paddleocr>=2.7.0
paddlepaddle>=2.5.0
python-multipart>=0.0.6
```

**Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ocr_service.py .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "ocr_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Commit**

```bash
git add services/ocr/Dockerfile services/ocr/requirements.txt
git commit -m "feat(ocr): add Dockerfile for OCR service

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 3: 更新 Docker Compose

### Task 3.1: 更新 docker-compose.production.yml

**Files:**
- Modify: `docker-compose.production.yml`

**Step 1: 添加 OCR 服务定义**

在 `docker-compose.production.yml` 添加:

```yaml
  # OCR Fallback Service
  ocr:
    build:
      context: ./services/ocr
      dockerfile: Dockerfile
    ports:
      - "8102:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    profiles:
      - parsers
      - full
    networks:
      - bea-network
```

**Step 2: 验证 YAML 语法**

Run: `python -c "import yaml; yaml.safe_load(open('docker-compose.production.yml'))"`
Expected: 无错误

**Step 3: Commit**

```bash
git add docker-compose.production.yml
git commit -m "feat(docker): add OCR service to docker-compose

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 4: 集成测试

### Task 4.1: 创建 Fallback 链集成测试

**Files:**
- Create: `tests/test_parser_fallback_chain.py`

**Step 1: 编写测试**

```python
# tests/test_parser_fallback_chain.py
"""Integration tests for parser fallback chain."""
import pytest
from unittest.mock import patch, MagicMock

from app.parser_adapters import (
    ParserAdapterRegistry,
    ParseRoute,
    StubParserAdapter,
)
from app.errors import ApiError


class FailingAdapter(StubParserAdapter):
    def parse(self, **kwargs):
        raise ApiError(
            code="PARSE_FAILED",
            message="intentional failure",
            error_class="transient",
            retryable=True,
            http_status=503,
        )


def test_fallback_on_primary_failure():
    """Should fallback to secondary when primary fails."""
    registry = ParserAdapterRegistry({
        "primary": FailingAdapter(name="primary", section="p"),
        "secondary": StubParserAdapter(name="secondary", section="s"),
    })

    route = ParseRoute(
        selected_parser="primary",
        fallback_chain=["secondary"],
        parser_version="v1",
    )

    result = registry.parse_with_route(
        route=route,
        document_id="doc_1",
        default_text="test",
    )

    assert result["parser"] == "secondary"


def test_fallback_2_hop_limit():
    """SSOT §3: fallback chain limited to 2 hops."""
    registry = ParserAdapterRegistry({
        "a": FailingAdapter(name="a", section="a"),
        "b": FailingAdapter(name="b", section="b"),
        "c": FailingAdapter(name="c", section="c"),
        "d": StubParserAdapter(name="d", section="d"),  # This would succeed
    })

    route = ParseRoute(
        selected_parser="a",
        fallback_chain=["b", "c", "d"],  # 4 candidates
        parser_version="v1",
    )

    # Should fail after 3 attempts (a + b + c), d should not be tried
    with pytest.raises(ApiError, match="PARSER_FALLBACK_EXHAUSTED"):
        registry.parse_with_route(
            route=route,
            document_id="doc_1",
            default_text="test",
        )


def test_trace_id_propagation():
    """SSOT §2.2: trace_id should be accepted."""
    registry = ParserAdapterRegistry({
        "stub": StubParserAdapter(name="stub", section="test"),
    })

    route = ParseRoute(
        selected_parser="stub",
        fallback_chain=[],
        parser_version="v1",
    )

    result = registry.parse_with_route(
        route=route,
        document_id="doc_1",
        default_text="test",
        trace_id="trace_abc",
    )

    assert result is not None
```

**Step 2: 运行测试**

Run: `pytest tests/test_parser_fallback_chain.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_parser_fallback_chain.py
git commit -m "test(parsers): add fallback chain integration tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 5: 运行完整测试套件

### Task 5.1: 运行所有解析器测试

**Step 1: 运行测试**

Run: `pytest tests/test_parser*.py -v`
Expected: ALL PASS

**Step 2: 验证无回归**

Run: `pytest tests/ -v --tb=short`
Expected: 无新失败

---

## Verification Checklist

- [ ] Fallback 2跳限制已实现 (SSOT §3)
- [ ] trace_id 可传递到解析流程 (SSOT §2.2)
- [ ] OCR 服务可独立运行
- [ ] Docker Compose 包含 OCR 服务
- [ ] 所有测试通过

---

## SSOT Alignment Summary

| SSOT 约束 | 实现 |
|-----------|------|
| §3 fallback 最多 2 跳 | Task 1.1 |
| §2.2 trace_id 贯穿 | Task 1.2 |
| §3 解析器路由 | 现有实现 |
| §10 错误码 | 现有实现 |
