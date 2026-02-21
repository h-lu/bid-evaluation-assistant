# Gate A 术语与状态冻结字典

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标与范围

1. 冻结 Gate A 的核心术语：状态、错误码、角色、引用对象。
2. 消除同义混用，给出跨文档统一命名规则。
3. 为 Gate B 契约实现提供唯一字段基线。

适用范围：`README.md`、`docs/design/*.md`、`docs/ops/*.md`、`AGENTS.md`、`CLAUDE.md`。

## 2. 核心字段命名冻结

### 2.1 身份与追踪字段

1. `tenant_id`
2. `project_id`
3. `supplier_id`
4. `document_id`
5. `evaluation_id`
6. `job_id`
7. `trace_id`
8. `thread_id`
9. `resume_token`

### 2.2 评分与复核字段

1. `confidence`
2. `citation_coverage`
3. `needs_manual_decision`（状态）
4. `needs_human_review`（布尔字段，仅用于结果对象）

规则：状态与布尔字段不可互换使用。

## 3. 状态字典（冻结）

### 3.1 任务状态（`jobs.status`）

```text
queued -> running -> retrying -> succeeded
running/retrying -> dlq_pending -> dlq_recorded -> failed
```

状态集合：

1. `queued`
2. `running`
3. `retrying`
4. `succeeded`
5. `dlq_pending`
6. `dlq_recorded`
7. `failed`

约束：

1. `failed` 只能在 `dlq_recorded` 之后出现。
2. `needs_manual_decision` 不是 `jobs.status` 值。

### 3.2 评估流程状态（`evaluation/workflow`）

```text
upload_received -> parse_queued -> parsing -> parsed -> indexing -> indexed
-> evaluating -> needs_manual_decision(optional) -> approved -> report_generated -> archived
```

状态集合：

1. `upload_received`
2. `parse_queued`
3. `parsing`
4. `parsed`
5. `indexing`
6. `indexed`
7. `evaluating`
8. `needs_manual_decision`
9. `approved`
10. `report_generated`
11. `archived`

约束：

1. `needs_manual_decision` 仅由质量门触发。
2. `resume` 成功后恢复到 `finalize_report` 路径，不回跳任意节点。

### 3.3 DLQ 条目状态（`dlq_items.status`）

1. `open`
2. `requeued`
3. `discarded`

约束：`discarded` 必须满足双人复核。

## 4. 错误码字典（冻结）

### 4.1 认证与权限

1. `AUTH_UNAUTHORIZED`
2. `AUTH_FORBIDDEN`
3. `TENANT_SCOPE_VIOLATION`

### 4.2 请求与幂等

1. `REQ_VALIDATION_FAILED`
2. `IDEMPOTENCY_CONFLICT`
3. `IDEMPOTENCY_MISSING`

### 4.3 解析与检索

1. `DOC_PARSE_OUTPUT_NOT_FOUND`
2. `DOC_PARSE_SCHEMA_INVALID`
3. `MINERU_BBOX_FORMAT_INVALID`
4. `TEXT_ENCODING_UNSUPPORTED`
5. `PARSER_FALLBACK_EXHAUSTED`
6. `RAG_RETRIEVAL_TIMEOUT`
7. `RAG_UPSTREAM_UNAVAILABLE`

### 4.4 工作流与恢复

1. `WF_STATE_TRANSITION_INVALID`
2. `WF_INTERRUPT_RESUME_INVALID`
3. `WF_CHECKPOINT_NOT_FOUND`

### 4.5 DLQ 与运维

1. `DLQ_ITEM_NOT_FOUND`
2. `DLQ_REQUEUE_CONFLICT`
3. `DLQ_DISCARD_REQUIRES_APPROVAL`

规则：

1. 错误码命名统一使用 `UPPER_SNAKE_CASE`。
2. 新错误码必须先更新 `docs/design/2026-02-21-error-handling-and-dlq-spec.md` 再更新调用文档。

## 5. 角色字典（冻结）

角色集合：`admin/agent/evaluator/viewer`。

| 角色 | 核心职责 | 高风险动作权限 |
| --- | --- | --- |
| `admin` | 租户内全局治理、审计、运维处置 | 可发起，需审批链 |
| `agent` | 发起上传/评估、处理一般任务 | 可执行 `requeue`，不可单独 `discard`/终审发布 |
| `evaluator` | 业务评审、人工复核意见 | 可提交复核决策，不具备治理类高风险提交权 |
| `viewer` | 只读查询 | 无 |

约束：

1. 高风险动作（终审发布、DLQ discard、legal hold 解除、外部正式提交）必须双人复核。
2. 操作人与复核人必须不同。

## 6. 引用对象字典（冻结）

### 6.1 Citation 最小对象（API/前端）

```json
{
  "chunk_id": "ck_xxx",
  "document_id": "doc_xxx",
  "page": 8,
  "bbox": [120.2, 310.0, 520.8, 365.4],
  "quote": "原文片段...",
  "context": "上下文..."
}
```

### 6.2 存储层位置对象（解析/检索）

```json
{
  "page_no": 8,
  "bbox": [120.2, 310.0, 520.8, 365.4]
}
```

映射规则：

1. 存储层 `page_no` 对外转换为 `page`。
2. `bbox` 统一 `[x0,y0,x1,y1]`，禁止返回 `xywh`。
3. 至少返回一条可回跳位置；多位置时提供 `primary_position`。

## 7. 同义词与禁用词映射

| 非规范写法 | 规范写法 | 说明 |
| --- | --- | --- |
| `context_list.json`（作为标准名） | `content_list.json` | `context_list` 仅兼容读取，不是 canonical 命名 |
| `needs_human_review`（作为流程状态） | `needs_manual_decision` | 前者是布尔字段，不是状态机节点 |
| `xywh` 直接透传 | 归一化为 `[x0,y0,x1,y1]` | 坐标格式必须统一 |

## 8. Gate A-1 验收标准

1. 状态、错误码、角色、引用对象四类术语均有唯一定义。
2. 文档中不存在同一语义的多种 canonical 命名。
3. 所有新增术语先更新本字典，再扩散到专项文档。

## 9. 参考文档

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. `docs/design/2026-02-21-rest-api-specification.md`
3. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`
4. `docs/design/2026-02-21-langgraph-agent-workflow-spec.md`
5. `docs/design/2026-02-21-security-design.md`
