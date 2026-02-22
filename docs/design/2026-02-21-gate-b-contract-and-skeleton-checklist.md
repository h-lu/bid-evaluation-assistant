# Gate B 契约与骨架验收清单

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/design/2026-02-21-implementation-plan.md`

## 1. 目的

1. 将 Gate B（B-1~B-4）验收证据集中到单文档。
2. 区分“文档冻结完成”和“运行验证完成”。
3. 为进入 Gate C 提供明确前置检查项。

## 2. B-1 API 契约验收

| 检查项 | 证据文档 | 当前状态 |
| --- | --- | --- |
| 统一响应模型与错误对象 | `docs/design/2026-02-21-rest-api-specification.md` | 文档冻结完成 |
| 幂等策略（`Idempotency-Key`） | `docs/design/2026-02-21-rest-api-specification.md` | 文档冻结完成 |
| 异步契约（`202 + job_id`） | `docs/design/2026-02-21-openapi-v1.yaml` | 文档冻结完成 |
| `resume_token` 与 citation schema | `docs/design/2026-02-21-openapi-v1.yaml` | 文档冻结完成 |
| 契约测试样例 | `docs/design/2026-02-21-api-contract-test-samples.md` | 文档冻结完成 |

## 3. B-2 任务系统骨架验收

| 检查项 | 证据文档 | 当前状态 |
| --- | --- | --- |
| 任务状态机定义 | `docs/design/2026-02-21-job-system-and-retry-spec.md` | 文档冻结完成 |
| 重试策略（3 次 + 指数退避） | `docs/design/2026-02-21-job-system-and-retry-spec.md` | 文档冻结完成 |
| DLQ 子流程入口与时序 | `docs/design/2026-02-21-job-system-and-retry-spec.md` | 文档冻结完成 |
| 回放样例（RP-001~RP-005） | `docs/design/2026-02-21-job-system-and-retry-spec.md` | 文档冻结完成 |

## 4. B-3 数据模型骨架验收

| 检查项 | 证据文档 | 当前状态 |
| --- | --- | --- |
| `jobs/workflow_checkpoints/dlq_items/audit_logs` 建模 | `docs/design/2026-02-21-data-model-and-storage-spec.md` | 文档冻结完成 |
| RLS 与 `app.current_tenant` | `docs/design/2026-02-21-data-model-and-storage-spec.md` | 文档冻结完成 |
| outbox 与消费幂等键 | `docs/design/2026-02-21-data-model-and-storage-spec.md` | 文档冻结完成 |
| 跨租户阻断回归 | N/A（待代码阶段） | 运行验证待完成 |

## 5. B-4 解析与检索骨架验收

| 检查项 | 证据文档 | 当前状态 |
| --- | --- | --- |
| 解析器路由骨架（`mineru -> docling -> ocr`） | `docs/design/2026-02-21-mineru-ingestion-spec.md` | 文档冻结完成 |
| 检索模式选择器（`local/global/hybrid/mix`） | `docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 文档冻结完成 |
| 引用对象最小字段 | `docs/design/2026-02-21-rest-api-specification.md` | 文档冻结完成 |
| 示例文档入库与回跳验证 | N/A（待代码阶段） | 运行验证待完成 |

## 6. Gate C 准入前检查（最小）

1. OpenAPI 与契约样例同步一致。
2. 状态机与错误码字典一致（含 `dlq_pending/dlq_recorded/failed` 时序）。
3. B-3/B-4 的运行验证任务已进入开发待办并分配执行责任。

## 7. 结论

1. Gate B 的“文档契约与骨架冻结”已具备入 Gate C 条件。
2. Gate B 的“运行验证”需在代码仓库完成后补齐证据。

## 8. 运行验证证据（本分支）

说明：以下为 `codex/gate-c-api-skeleton` 分支的最小可运行证据。

1. 运行命令：`pytest -v`
2. 测试结果：`65 passed`
3. 覆盖范围：
   - B-1：统一响应包络、幂等、`202 + job_id`、`resume_token`、citation source、DLQ 运维接口、retrieval query/preview 契约、evaluation report 契约
   - B-1：HITL 恢复输入校验（`editor.reviewer_id`）、`resume_token` 单次有效与 `interrupt` 负载返回
   - B-2：任务初始状态、`jobs/{job_id}` 状态查询契约、状态机流转、`cancel` 语义、内部回放接口
   - B-4：`documents/{document_id}/parse` 异步受理契约、parse manifest 最小字段、解析失败错误码分类
   - B-4：`documents/{document_id}` 与 `documents/{document_id}/chunks` 读取契约、parse 成功后最小 chunk 产出
   - B-4：`content_list/context_list` 发现、bbox 归一化、`utf-8 -> gb18030` 编码回退
   - B-4：检索模式选择（`local/global/hybrid/mix`）与租户/项目过滤最小验证，支持 preview 最小证据返回
   - B-4：检索约束词过滤（`must_include_terms/must_exclude_terms`）与 rerank 降级开关（`enable_rerank=false`）
   - B-3：租户隔离最小验证（跨租户阻断）与内部调试端点访问控制
4. 证据测试文件：
   - `tests/test_response_envelope.py`
   - `tests/test_idempotency.py`
   - `tests/test_api_contract_core.py`
   - `tests/test_resume_and_citation.py`
   - `tests/test_job_state_machine.py`
   - `tests/test_parse_and_dlq_ops.py`
   - `tests/test_job_cancel.py`
   - `tests/test_jobs_list.py`
   - `tests/test_tenant_isolation.py`
   - `tests/test_internal_replay_api.py`
   - `tests/test_internal_job_run.py`
   - `tests/test_parse_manifest_and_error_classification.py`
   - `tests/test_parse_utils.py`
   - `tests/test_retrieval_query.py`
   - `tests/test_evaluation_report.py`
   - `tests/test_documents_read_endpoints.py`

更新结论：

1. B-1 运行验证：已在本分支完成最小闭环验证（含 retrieval/report 与 HITL resume 契约）。
2. B-2 运行验证：已在本分支完成核心状态查询、状态机和取消语义验证。
3. B-4 运行验证：已完成 parse 受理、文档分块读取、检索模式选择/过滤/降级和基础 DLQ 运维契约验证（内存实现）。
4. B-3 运行验证：已完成接口层跨租户阻断验证；真实存储层 RLS 验证待后续接入 DB 补齐。
