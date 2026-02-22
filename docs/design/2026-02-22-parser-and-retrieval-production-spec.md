# 解析与检索生产化规范

> 版本：v2026.02.22-r1  
> 状态：Draft  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 将解析链路从骨架替换为 MinerU/Docling/OCR 真实适配器。
2. 将检索链路从 stub 替换为 LightRAG + metadata 过滤真实链路。
3. 保证 citation 回跳字段完整、可复核。

## 2. 解析链路

### 2.1 适配器层

1. `ParserAdapter` 抽象统一 `parse(file) -> parse_artifacts`。
2. `MineruAdapter` 处理 `content_list/context_list/full.md` 兼容。
3. `DoclingAdapter` 处理 Office/HTML/常规 PDF。
4. `OcrFallbackAdapter` 作为最后兜底。

### 2.2 parse manifest

最低字段：

1. `run_id, document_id, tenant_id`
2. `selected_parser, fallback_chain`
3. `input_files[]`
4. `status, error_code, started_at, ended_at`

### 2.3 chunk 标准化

1. bbox 统一 `xyxy`（`[x0,y0,x1,y1]`）。
2. 元数据统一：`page,bbox,heading_path,chunk_type,parser,parser_version`。
3. chunk 去重基于 `document_id + chunk_hash`。

## 3. 检索链路

### 3.1 LightRAG 接入

1. 建立 tenant/project 维度索引命名规则。
2. local/global/hybrid/mix 模式由 selector 决策。
3. 检索入参与结果必须带租户约束字段。

### 3.2 查询改写与约束保持

1. 改写前提取 include/exclude 约束词。
2. 改写后输出 `constraints_preserved=true` 与 diff。
3. 改写失败时回退原 query 并记录原因。

### 3.3 rerank 与降级

1. rerank 超时/失败时自动降级。
2. 降级时 `degraded=true` 且按召回分排序。

## 4. 数据落点

1. chunk 真值写 PostgreSQL。
2. 向量索引写 LightRAG/Chroma。
3. parse artifacts 写对象存储。

## 5. 测试要求

1. 解析适配器单测：多格式输入、错误分类、bbox 归一化。
2. 检索集成测：模式选择、metadata 过滤、约束保持。
3. 回归测：citation 回跳率与字段完整性。

## 6. 验收标准

1. 上传后的真实文档可完成 parse/index 并被检索命中。
2. 无跨租户召回。
3. 检索结果 `items[*].metadata` 字段完整。

## 7. 关联文档

1. `docs/design/2026-02-21-mineru-ingestion-spec.md`
2. `docs/design/2026-02-21-retrieval-and-scoring-spec.md`
3. `docs/design/2026-02-21-rest-api-specification.md`
