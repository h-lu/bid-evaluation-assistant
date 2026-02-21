# Gate A 模块边界与副作用边界冻结表

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 冻结模块职责边界，避免后续实现阶段跨模块写入。
2. 固化副作用唯一归属，防止重复提交与状态错乱。
3. 给 Gate B-C 的实现与测试提供可执行边界表。

## 2. 模块边界冻结

| 模块 | 职责（必须） | 允许读 | 唯一可写（副作用） | 禁止越界 |
| --- | --- | --- | --- | --- |
| `frontend` | 发起请求、展示状态与证据回跳 | API 响应 | 无持久化写入 | 直接写 DB/队列/对象存储 |
| `api` | 鉴权、参数校验、受理任务、返回契约 | JWT、配置、业务只读 | `jobs` 初始任务受理记录 | 同步执行长任务、跨租户写入 |
| `ingestion` | 解析路由、分块、入库、建索引 | 原始文件、项目规则 | `document_parse_runs`、`document_chunks`、向量索引、文档索引状态 | 写评估结果、写终审状态 |
| `retrieval` | 约束抽取、召回、重排、证据打包 | 索引、结构化白名单字段 | 无持久化最终写入（仅返回内存结果） | 写评分结果、绕过租户过滤 |
| `evaluation` | 规则硬判定 + LLM 软评分计算 | 证据包、规则包 | 无最终持久化写入（输出计算结果） | 直接落库报告、绕过规则引擎红线 |
| `workflow` | 状态机编排、checkpoint、HITL、重试与 DLQ 时序 | 上述各模块输出 | `workflow_checkpoints`、`jobs.status`、`dlq_items`、`evaluation_results`、报告归档触发 | 跳过审批直接终审发布 |
| `governance` | 审批、审计、门禁、事故与变更流程 | 全链路审计与指标 | `audit_logs`、审批记录、门禁结果记录 | 直接改业务评分结果 |

边界规则：

1. 检索与评分模块只产出“计算结果”，不直接提交持久化副作用。
2. 终态提交必须经 `workflow` 的受控节点统一落库。
3. 任一模块发现租户上下文缺失，必须立即失败并上报错误码。

## 3. 副作用唯一归属表（冻结）

| 副作用动作 | 归属模块/节点 | 幂等键 | 前置条件 | 禁止重复归属 |
| --- | --- | --- | --- | --- |
| 创建异步任务 `jobs` | `api` 受理层 | `tenant_id + idempotency_key` | 鉴权成功 + 参数校验通过 | `workflow` 不得重复创建同语义任务 |
| 写解析 manifest | `ingestion` | `document_id + parser_version + input_hash` | 输入文件发现完成 | 其他模块不得写 `document_parse_runs` |
| 写 chunks 与 positions | `ingestion` | `document_id + chunk_version` | manifest 成功 | `retrieval/evaluation` 不得写 chunk |
| 写向量索引 | `ingestion` | `tenant_id + project_id + chunk_id + index_version` | chunks 已落库 | `retrieval` 不得直接写索引 |
| 写 checkpoint | `workflow` | `thread_id + node_name + checkpoint_seq` | 节点执行结束 | 业务模块不得直写 checkpoint |
| 写评分结果/报告 | `workflow.persist_result` | `evaluation_id + report_version` | 质量门已决策（pass 或合法 HITL 恢复） | `evaluation` 不得直写终态结果 |
| 写 DLQ 条目 | `workflow.retry_or_dlq` | `job_id + retry_count` | 重试耗尽或不可重试错误 | 其他模块不得直接写 `dlq_items` |
| 将任务置 `failed` | `workflow.retry_or_dlq` | `job_id + failed_transition_seq` | `dlq_recorded` 已成功 | 禁止先 `failed` 后写 DLQ |
| 写审计日志 | `governance` 中间件/审批流 | `trace_id + action + attempt` | 任一关键操作或高风险动作 | 业务模块不得绕过审计写路径 |

## 4. 时序冻结约束

### 4.1 主链路时序

```text
api accept(202 + job_id)
 -> ingestion parse/index
 -> retrieval/evaluation compute
 -> workflow quality_gate
 -> (hitl interrupt/resume)
 -> workflow persist_result
 -> governance audit
```

### 4.2 异常链路时序

```text
running
 -> retrying (<=3)
 -> dlq_pending
 -> dlq_recorded
 -> failed
```

强约束：

1. `failed` 必须晚于 `dlq_recorded`。
2. `discard`、终审发布、legal hold 解除必须走审批流并写审计。
3. `interrupt` 负载必须 JSON 可序列化，恢复必须校验最新 `resume_token`。

## 5. 跨模块通信边界

1. 模块内可同步调用；模块间优先 outbox 事件。
2. 事件最小字段：`event_id/tenant_id/aggregate_type/aggregate_id/trace_id/occurred_at`。
3. 禁止直接依赖下游内部表结构；跨模块只依赖契约对象。

## 6. Gate A-2 验收标准

1. 每个副作用动作都可定位到唯一模块和唯一节点。
2. 不存在“两个模块都可提交同一副作用”的定义。
3. 实施任务若违反本表边界，应在评审阶段阻断进入 Gate B-C。

## 7. 参考文档

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. `docs/design/2026-02-21-langgraph-agent-workflow-spec.md`
3. `docs/design/2026-02-21-data-model-and-storage-spec.md`
4. `docs/design/2026-02-21-agent-tool-governance.md`
5. `docs/design/2026-02-21-security-design.md`
