# API 契约测试样例（Gate B-1）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 为 Gate B-1/B-2 提供“可执行的契约测试样例”基线。
2. 覆盖统一响应模型、幂等、异步任务、HITL 恢复、citation 返回。
3. 为后续自动化契约测试提供最小样例集合。

## 2. 样例范围

基于 `docs/design/2026-02-21-openapi-v1.yaml` 的核心接口子集：

1. `POST /api/v1/documents/upload`
2. `POST /api/v1/documents/{document_id}/parse`
3. `POST /api/v1/evaluations`
4. `POST /api/v1/evaluations/{evaluation_id}/resume`
5. `GET /api/v1/jobs/{job_id}`
6. `POST /api/v1/jobs/{job_id}/cancel`
7. `GET /api/v1/jobs?status=&type=&cursor=&limit=`
8. `GET /api/v1/citations/{chunk_id}/source`
9. `GET /api/v1/dlq/items`
10. `POST /api/v1/dlq/items/{item_id}/requeue`
11. `POST /api/v1/dlq/items/{item_id}/discard`
12. `POST /api/v1/retrieval/query`
13. `POST /api/v1/retrieval/preview`
14. `GET /api/v1/evaluations/{evaluation_id}/report`
15. `GET /api/v1/documents/{document_id}`
16. `GET /api/v1/documents/{document_id}/chunks`
17. `GET /api/v1/evaluations/{evaluation_id}/audit-logs`

## 3. 执行约定

1. 所有响应必须包含 `meta.trace_id`。
2. 所有写接口必须携带 `Idempotency-Key`。
3. 客户端不得传 `tenant_id`；租户从 JWT 注入。
4. 校验顺序：HTTP 状态 -> `success` 字段 -> `error.code`/`data` 字段。

## 4. 契约样例矩阵

| Case ID | 接口 | 场景 | 输入要点 | 期望状态码 | 期望结果 |
| --- | --- | --- | --- | --- | --- |
| `CT-001` | `POST /documents/upload` | 正常上传受理 | 合法 JWT + `Idempotency-Key` + multipart 文件 | `202` | `data.document_id/job_id/status=queued/next` |
| `CT-002` | `POST /documents/upload` | 缺失幂等键 | 不带 `Idempotency-Key` | `400` | `error.code=IDEMPOTENCY_MISSING` |
| `CT-003` | `POST /documents/upload` | 幂等冲突 | 同 key 不同 body 重放 | `409` | `error.code=IDEMPOTENCY_CONFLICT` |
| `CT-004` | `POST /documents/upload` | 租户越权 | JWT 租户与资源归属不一致 | `403` | `error.code=TENANT_SCOPE_VIOLATION` |
| `CT-005` | `POST /evaluations` | 正常评估受理 | 合法 `project_id/supplier_id/rule_pack_version` | `202` | `data.evaluation_id/job_id/status=queued` |
| `CT-006` | `POST /evaluations` | 参数校验失败 | `top_k=0` 或缺失必填字段 | `400` | `error.code=REQ_VALIDATION_FAILED` |
| `CT-007` | `POST /documents/{document_id}/parse` | 正常解析受理 | 合法 `document_id` + `Idempotency-Key` | `202` | `data.document_id/job_id/status=queued` |
| `CT-008` | `POST /documents/{document_id}/parse` | 缺失幂等键 | 不带 `Idempotency-Key` | `400` | `error.code=IDEMPOTENCY_MISSING` |
| `CT-009` | `GET /jobs/{job_id}` | 查询运行中任务 | 已存在 `job_id` | `200` | `data.status` 在状态字典内 |
| `CT-010` | `GET /jobs/{job_id}` | 查询不存在任务 | 不存在 `job_id` | `404` | `success=false`，错误对象完整 |
| `CT-011` | `POST /jobs/{job_id}/cancel` | 正常取消 | 合法 `job_id` + `Idempotency-Key` | `202` | `data.status=failed,error_code=JOB_CANCELLED` |
| `CT-012` | `POST /jobs/{job_id}/cancel` | 终态冲突 | 任务已 `succeeded/failed` | `409` | `error.code=JOB_CANCEL_CONFLICT` |
| `CT-013` | `POST /evaluations/{evaluation_id}/resume` | 合法恢复 | 合法 `resume_token + decision + comment + editor.reviewer_id` | `202` | 返回新的 `job_id` |
| `CT-014` | `POST /evaluations/{evaluation_id}/resume` | token 非法/过期 | `resume_token` 无效 | `409` | `error.code=WF_INTERRUPT_RESUME_INVALID` |
| `CT-038` | `POST /evaluations/{evaluation_id}/resume` | 缺失 reviewer | 无 `editor.reviewer_id` | `400` | `error.code=WF_INTERRUPT_REVIEWER_REQUIRED` |
| `CT-039` | `POST /evaluations/{evaluation_id}/resume` | token 单次有效 | 同 `resume_token` 二次提交 | `409` | `error.code=WF_INTERRUPT_RESUME_INVALID` |
| `CT-015` | `GET /citations/{chunk_id}/source` | 引用回跳成功 | 合法 `chunk_id` | `200` | 返回 `document_id/page/bbox/text/context` |
| `CT-016` | `GET /citations/{chunk_id}/source` | 引用不存在 | 不存在 `chunk_id` | `404` | `success=false`，错误对象完整 |
| `CT-017` | `GET /dlq/items` | 查询 DLQ 列表 | 无 | `200` | 返回 `items[]/total` |
| `CT-018` | `POST /dlq/items/{item_id}/requeue` | 重放 DLQ 项 | item 状态 `open` | `202` | 返回新 `job_id` 且条目变 `requeued` |
| `CT-019` | `POST /dlq/items/{item_id}/discard` | 缺失审批字段 | `reason/reviewer_id` 为空 | `400` | `error.code=DLQ_DISCARD_REQUIRES_APPROVAL` |
| `CT-020` | `POST /dlq/items/{item_id}/discard` | 合法丢弃 | `reason + reviewer_id` | `200` | 条目状态 `discarded` |
| `CT-021` | `GET /jobs` | 列表查询 | 默认参数 | `200` | 返回 `items[]/total` |
| `CT-022` | `GET /jobs?type=evaluation` | 类型过滤 | `type=evaluation` | `200` | 全部 `job_type=evaluation` |
| `CT-023` | `GET /jobs?limit=1&cursor=...` | 游标分页 | 有效 `cursor/limit` | `200` | 返回 `next_cursor` 且可翻页 |
| `CT-024` | `GET /jobs/{job_id}` | 跨租户读取 | 资源租户与当前租户不一致 | `403` | `error.code=TENANT_SCOPE_VIOLATION` |
| `CT-025` | `POST /documents/{document_id}/parse` | 跨租户写入 | 文档租户与当前租户不一致 | `403` | `error.code=TENANT_SCOPE_VIOLATION` |
| `CT-026` | `GET /jobs?type=evaluation` | 租户级列表隔离 | 混合租户样本 | `200` | 仅返回当前租户任务 |
| `CT-027` | `POST /dlq/items/{item_id}/requeue` | 缺失幂等键 | 不带 `Idempotency-Key` | `400` | `error.code=IDEMPOTENCY_MISSING` |
| `CT-028` | `POST /dlq/items/{item_id}/discard` | 缺失幂等键 | 不带 `Idempotency-Key` | `400` | `error.code=IDEMPOTENCY_MISSING` |
| `CT-029` | `POST /dlq/items/{item_id}/requeue` | 幂等重放 | 同 key + 同 body | `202` | 返回相同 `job_id` |
| `CT-030` | `POST /retrieval/query` | 模式选择（relation） | `query_type=relation` | `200` | `data.selected_mode=global` |
| `CT-031` | `POST /retrieval/query` | 高风险强制 mix | `query_type=fact + high_risk=true` | `200` | `data.selected_mode=mix` |
| `CT-032` | `POST /retrieval/query` | 租户/项目过滤 | 混合租户与项目样本 | `200` | 仅返回当前租户且 `project_id` 命中项 |
| `CT-033` | `POST /retrieval/preview` | 预览返回最小证据 | 与 query 相同入参 | `200` | `data.items[*]` 含 `chunk_id/document_id/page/bbox/text` |
| `CT-034` | `POST /retrieval/preview` | 预览继承模式选择 | `query_type=summary` | `200` | `data.selected_mode=hybrid` |
| `CT-035` | `POST /retrieval/query` | 约束词过滤 | `must_include_terms + must_exclude_terms` | `200` | 仅返回满足约束词的候选 |
| `CT-036` | `POST /retrieval/query` | rerank 降级 | `enable_rerank=false` | `200` | `data.degraded=true` 且 `score_rerank=null` |
| `CT-046` | `POST /retrieval/query` | 约束保持改写输出 | 任意合法 query | `200` | `rewritten_query/rewrite_reason/constraints_preserved/constraint_diff` 字段存在 |
| `CT-037` | `GET /evaluations/{evaluation_id}/report` | 报告查询 | 合法 `evaluation_id` | `200` | 返回 `total_score/confidence/criteria_results/citations` |
| `CT-047` | `GET /evaluations/{evaluation_id}/report` | 引用覆盖率字段 | 合法 `evaluation_id` | `200` | 返回 `citation_coverage` 且 `criteria_results[*].citations` 非空 |
| `CT-040` | `GET /evaluations/{evaluation_id}/report` | HITL 中断负载 | `evaluation_scope.force_hitl=true` | `200` | `needs_human_review=true` 且 `interrupt.resume_token` 存在 |
| `CT-041` | `GET /documents/{document_id}` | 文档详情查询 | 合法 `document_id` | `200` | 返回文档元数据与状态 |
| `CT-042` | `GET /documents/{document_id}/chunks` | 解析分块查询 | parse 成功后查询 | `200` | 返回 `chunk_id/pages/positions/heading_path/chunk_type` |
| `CT-043` | `GET /documents/{document_id}/chunks` | 跨租户阻断 | 文档归属租户不一致 | `403` | `error.code=TENANT_SCOPE_VIOLATION` |
| `CT-044` | `GET /evaluations/{evaluation_id}/audit-logs` | 恢复审计查询 | 完成一次 resume 后查询 | `200` | 返回 `resume_submitted` 日志 |
| `CT-045` | `GET /evaluations/{evaluation_id}/audit-logs` | 跨租户阻断 | evaluation 租户不一致 | `403` | `error.code=TENANT_SCOPE_VIOLATION` |

## 5. 关键断言模板

### 5.1 Success 响应断言

1. `success == true`
2. `meta.trace_id` 非空
3. `data` 字段包含接口定义的最小集合

### 5.2 Error 响应断言

1. `success == false`
2. `error.code/message/retryable/class` 全存在
3. `meta.trace_id` 非空

### 5.3 Job 状态断言

`data.status` 必须属于：

1. `queued`
2. `running`
3. `retrying`
4. `succeeded`
5. `failed`
6. `needs_manual_decision`
7. `dlq_pending`
8. `dlq_recorded`

## 6. 样例执行记录（证据模板）

每个 Case 至少记录：

1. `case_id`
2. `request_id`
3. `trace_id`
4. `http_status`
5. `assertion_result`（pass/fail）
6. `captured_at`

## 7. Gate B-1 验收映射

1. 统一响应模型与错误对象：`CT-001/006/010/014/016/019/024/025`。
2. 幂等策略：`CT-002/003/027/028/029`。
3. 异步任务契约：`CT-001/005/007/009/011/013/018/021/023`。
4. `resume_token` 与 citation schema：`CT-013/014/015`。
5. B-2 状态机运维动作（cancel/DLQ）：`CT-011/012/017/018/019/020/022`。
6. 多租户隔离：`CT-024/025/026/032`。

## 8. 后续自动化建议

1. 将本样例映射为契约测试脚本（pytest/newman）。
2. 每次 API 字段变更必须同步更新样例矩阵。
3. Gate C 前至少完成一次全量样例回放并归档结果。
