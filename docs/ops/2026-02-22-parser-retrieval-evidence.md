# P2 解析与检索验收证据

> 日期：2026-02-22
> 阶段：P2（Parser & Retrieval Productionization）

## 1. 执行命令

```bash
pytest -q tests/test_parser_adapters.py tests/test_retrieval_query.py tests/test_parse_manifest_and_error_classification.py
pytest -q tests/test_documents_repository.py tests/test_documents_read_endpoints.py tests/test_observability_metrics_api.py
pytest -q
```

## 2. 结果摘要

1. parser adapter 回归通过（含 endpoint 调用与 fallback）。
2. retrieval 回归通过（含 LightRAG index prefix、metadata 过滤、rerank 异常降级）。
3. manifest/chunk 字段回归通过（含 `chunk_hash/page/bbox`）。
4. 观测回归通过（`parse_retrieval` 指标可见）。
5. 全量测试通过。

## 3. 关键实现点

1. `HttpParserAdapter` 支持 `MINERU_ENDPOINT/DOCLING_ENDPOINT/OCR_ENDPOINT`，无 endpoint 时自动降级 stub。
2. parse fallback 可观测：`parse_fallback_used_total`。
3. chunk 去重键：`document_id + chunk_hash`。
4. LightRAG 查询/索引采用 `LIGHTRAG_DSN` 可选接入，失败不阻断主链路。
5. rerank 异常降级：`degraded=true`，`degrade_reason=rerank_failed`。

## 4. 契约对齐

1. 保持 `GET /api/v1/documents/{document_id}/chunks` 既有字段语义，新增 `chunk_hash/page/bbox` 为向后兼容追加字段。
2. 保持 `POST /api/v1/retrieval/query` 主要字段不变，新增 `degrade_reason`。
3. `POST /api/v1/retrieval/preview` 新增 `degraded` 字段，便于前端一致处理降级态。
