# 解析与检索生产化规范

> 版本：v2026.02.22-r8  
> 状态：Active  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 文档目标

1. 将解析链路替换为可运行的真实适配器能力（MinerU/Docling/OCR）。
2. 将检索链路替换为真实 LightRAG 索引与检索能力。
3. 保持 citation 字段与检索输出契约稳定。

## 2. 范围与非目标

### 2.1 纳入范围

1. 解析器路由与 fallback 执行。
2. parse manifest 与 chunk 元数据真落库。
3. LightRAG 索引构建、查询与 metadata 过滤。
4. query rewrite 约束保持与 rerank 降级。

### 2.2 非目标

1. 多模态图像理解增强。
2. 跨语言 OCR 质量优化专题。
3. 复杂知识图谱增量更新优化。

## 3. 当前基线（已完成）

1. `ParserAdapterRegistry` 与 fallback 链路已存在。
2. `BEA_DISABLED_PARSERS` 开关已支持故障注入回归。
3. 检索输出已有 `index_name` 和 `tenant_id/document_id` 元数据。

## 4. 目标架构

```text
Upload -> Parse Router -> Parser Adapter -> Parse Manifest + Chunks
      -> Vector Index Writer (LightRAG)
Query -> Rewrite (constraints-preserving) -> Selector -> LightRAG Query
      -> Rerank (or degrade) -> Citation-Ready Response
```

约束：

1. parse 失败必须给出稳定错误码，不允许裸异常透出。
2. 检索调用必须带 tenant/project 过滤，不允许全局召回。
3. rerank 失败只允许降级，不允许主链路中断。

## 5. 实施任务（执行顺序）

### 5.1 P2-S1：真实解析器接入

输入：当前 adapter 抽象。  
产出：`MineruAdapter/DoclingAdapter/OcrFallbackAdapter` 真实调用实现。  
验收：混合样本（PDF/Office/扫描件）可稳定产出 manifest + chunks。

最小交付：

1. MinerU：兼容 `content_list.json/context_list.json/full.md`。
2. Docling：Office/HTML/PDF 常规解析。
3. OCR：主解析失败时兜底。

### 5.2 P2-S2：manifest/chunk 标准化

输入：S1。  
产出：统一元数据与去重策略。  
验收：字段完整且可回跳定位。

最小字段：

1. manifest：`run_id,document_id,tenant_id,selected_parser,fallback_chain,status,error_code`。
2. chunk：`chunk_id,document_id,page,bbox,heading_path,chunk_type,parser,parser_version,text`。
3. 去重键：`document_id + chunk_hash`。

### 5.3 P2-S3：LightRAG 真索引与查询

输入：S2。  
产出：索引构建、查询、metadata 过滤链路。  
验收：租户/项目隔离召回通过，命中率达基线。

最小交付：

1. 索引名：`lightrag:{tenant_id}:{project_id}`。
2. 查询过滤：`tenant_id/project_id/doc_type`。
3. 查询模式：`local/global/hybrid/mix`。

### 5.4 P2-S4：改写与降级

输入：S3。  
产出：约束保持改写 + rerank 降级链路。  
验收：约束词不丢失，rerank 异常时响应仍成功。

最小交付：

1. `constraints_preserved=true/false` 与差异摘要。
2. rerank 失败时 `degraded=true`。
3. 降级排序按召回分。

### 5.5 P2-S5：可观测与回放

输入：S1-S4。  
产出：解析与检索关键指标埋点、回放证据。  
验收：可定位 parser 选择、fallback 原因、检索模式和降级次数。

## 6. 数据与契约约束

1. 不改 `GET /documents/{document_id}/chunks` 输出语义。
2. 不改 citation 最小字段：`document_id/page/bbox/text/context`。
3. 新增字段仅可追加，不可破坏老字段含义。

## 7. 配置清单

1. `BEA_DISABLED_PARSERS`
2. `MINERU_ENDPOINT` / `MINERU_TIMEOUT_S`
3. `DOCLING_ENDPOINT` / `DOCLING_TIMEOUT_S`
4. `OCR_ENDPOINT` / `OCR_TIMEOUT_S`
5. `LIGHTRAG_DSN`
6. `LIGHTRAG_INDEX_PREFIX`
7. `RERANK_TIMEOUT_MS`

## 8. 测试与验证命令

1. 解析单测：路由、fallback、错误分类、编码回退。
2. 检索集成：模式选择、metadata 过滤、降级。
3. 回放：上传->解析->检索->评估链路样本集。

建议命令：

```bash
pytest -q tests/test_parse_manifest_and_error_classification.py
pytest -q tests/test_parser_adapters.py tests/test_retrieval_query.py
pytest -q
```

## 9. 验收证据模板

1. 解析成功率与 fallback 占比报表。
2. 召回隔离证明（跨租户命中 0）。
3. citation 完整率报告。
4. rerank 降级触发率与稳定性报告。

## 10. 退出条件（P2 完成定义）

1. 真实文档可稳定完成 parse/index/query。
2. 检索输出元数据字段完整且可追溯。
3. 无跨租户召回。
4. rerank 异常不影响主链路成功返回。

## 11. 风险与回退

1. 风险：外部解析服务抖动导致延迟飙升。
2. 风险：索引写入失败导致检索空结果。
3. 回退：临时切回稳定 parser 顺序与本地检索降级策略，保障可用性优先。

## 12. 实施检查清单

1. [x] 真实 adapter 已接入并可回归。
2. [x] manifest/chunk 字段全量对齐。
3. [x] LightRAG 查询隔离已验证。
4. [x] rewrite/rerank 降级策略已验证。
5. [x] 回放证据与指标报表齐全。

## 13. 本轮实现更新（P2 完整）

1. `app/parser_adapters.py` 新增 `HttpParserAdapter`，支持 `MINERU/DOCLING/OCR` endpoint + timeout 配置；未配置 endpoint 时保持 stub 行为。
2. parser 返回兼容 `chunks/content_list/full_md(full.md)` 三类载荷，统一映射为 chunk 契约字段。
3. `ParserAdapterRegistry.parse_with_route` 支持解析失败自动回退到 fallback parser，不再因首选 parser 异常直接中断。
4. 新增回归：`tests/test_parser_adapters.py::test_registry_uses_http_parser_payload_when_endpoint_configured`。
5. 新增回归：`tests/test_parser_adapters.py::test_registry_fallbacks_when_selected_http_parser_fails`。
6. `app/store.py` 新增 chunk 标准化与去重：`chunk_hash = sha256(document_id+page+bbox+heading_path+text)`，并补齐 `page/bbox/chunk_id`。
7. `app/repositories/documents.py` 与 `document_chunks` 表新增 `chunk_hash` 持久化字段；读取结果补齐 `page/bbox`。
8. 解析成功路径新增 LightRAG 索引写入钩子（`LIGHTRAG_DSN` 可选）；索引失败不阻断主链路并记录指标。
9. 检索查询新增 LightRAG 查询路径（`LIGHTRAG_DSN` 可选）+ 二次 tenant/project/supplier/doc_scope 过滤，保证隔离。
10. 改写约束保持新增 `constraint_diff` 真实计算；rerank 异常时降级返回 `degraded=true` 与 `degrade_reason`。
11. `summarize_ops_metrics` 新增 `parse_retrieval` 观测字段：解析次数、fallback 次数、索引调用/失败、查询次数、降级次数。
12. 新增回归：`tests/test_retrieval_query.py::test_retrieval_query_degrades_when_rerank_raises`。
13. 新增回归：`tests/test_retrieval_query.py::test_retrieval_query_uses_lightrag_index_prefix_and_filters_metadata`。
14. 新增回归：`tests/test_parse_manifest_and_error_classification.py::test_parse_success_updates_manifest_status`（补充 chunk_hash/page/bbox 断言）。
15. 新增观测回归：`tests/test_observability_metrics_api.py` 覆盖 `parse_retrieval` 指标字段。
