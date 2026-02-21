# LangGraph Agent 工作流规范

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 将评标流程固化为可执行状态机。
2. 保证中断恢复、幂等与副作用边界可控。
3. 异常路径可追踪、可重试、可落 DLQ。
4. 保持与 LangGraph 官方 checkpoint/interrupt 模式一致。

## 2. 状态对象（最小字段）

```text
identity:
  tenant_id, project_id, evaluation_id, supplier_id
trace:
  trace_id, thread_id, checkpoint_id
inputs:
  query_bundle, rule_pack_version
retrieval:
  retrieved_chunks[], evidence_bundle
scoring:
  criteria_scores, total_score, confidence, citation_coverage
review:
  requires_human_review, human_review_payload, human_decision, resume_token
output:
  report_payload, status
runtime:
  retry_count, errors[]
```

不可变字段：

1. `tenant_id`
2. `evaluation_id`
3. `thread_id`

## 3. 图结构（ASCII）

```text
START
 -> load_context
 -> retrieve_evidence
 -> evaluate_rules
 -> score_with_llm
 -> quality_gate
    -> pass  -> finalize_report
    -> hitl  -> human_review_interrupt
 -> persist_result
 -> END

any_error
 -> classify_error
 -> retry_or_dlq
 -> END
```

## 4. 节点职责与副作用

| 节点 | 职责 | 是否副作用 |
| --- | --- | --- |
| load_context | 加载项目、规则、租户上下文 | 否 |
| retrieve_evidence | 召回与证据打包 | 否 |
| evaluate_rules | 硬约束判定 | 否 |
| score_with_llm | 软评分与解释生成 | 否 |
| quality_gate | 判断是否进入 HITL | 否 |
| human_review_interrupt | 暂停并等待人工输入 | 否 |
| finalize_report | 组装报告内容 | 否 |
| persist_result | 写 DB/对象存储/审计 | 是 |
| retry_or_dlq | 写任务状态与 DLQ | 是 |

规则：副作用节点必须在流程末端，且具备幂等键。

## 5. 路由规则

### 5.1 正常路由

1. `quality_gate == pass` -> `finalize_report`。
2. `quality_gate == hitl` -> `human_review_interrupt`。

### 5.2 异常路由

1. `retryable=true && retry_count<3` -> `retry`。
2. 否则 -> `dlq_pending -> dlq_recorded -> failed`。

### 5.3 HITL 恢复路由

1. 收到合法 `resume_token` -> `finalize_report`。
2. token 过期/不匹配 -> `WF_INTERRUPT_RESUME_INVALID`。

## 6. checkpoint 与 durable execution

1. 启用持久化 checkpointer（PostgreSQL 后端）。
2. 每次 `invoke` 必须传 `configurable.thread_id`。
3. 相同 `thread_id` 表示恢复同一工作流；新 `thread_id` 表示新线程。
4. `interrupt` payload 必须 JSON 可序列化。
5. 中断信息统一通过 `__interrupt__` 返回给 API 层。

## 7. interrupt/resume 契约

### 7.1 interrupt 输出

```json
{
  "type": "human_review",
  "evaluation_id": "ev_xxx",
  "reasons": ["low_confidence", "citation_coverage_low"],
  "suggested_actions": ["approve", "reject", "edit_scores"],
  "resume_token": "rt_xxx"
}
```

### 7.2 resume 输入

```json
{
  "resume_token": "rt_xxx",
  "decision": "approve",
  "comment": "证据充分，允许继续",
  "editor": {
    "reviewer_id": "u_xxx"
  }
}
```

约束：

1. `resume_token` 单次有效。
2. 恢复请求必须带操作者身份。
3. 恢复行为写入 `audit_logs`。

## 8. 幂等与一致性

1. `persist_result` 幂等键：`evaluation_id + report_version`。
2. `retry_or_dlq` 幂等键：`job_id + retry_count`。
3. 副作用失败时只重试当前节点，不回放已成功副作用。
4. 并发恢复请求以 `resume_token` 乐观锁处理。

## 9. 错误处理集成

1. 节点抛错先分类：`validation/business/transient/permanent/security`。
2. transient 可重试，其他直接进入 DLQ 子流程。
3. 所有错误落 `errors[]`，并带 `trace_id`。

## 10. 观测字段

每次节点执行必须记录：

1. `trace_id`
2. `thread_id`
3. `node_name`
4. `started_at/ended_at`
5. `latency_ms`
6. `input_size/output_size`
7. `error_code`（若有）

## 11. 验收标准

1. interrupt 后可在 24h 内恢复。
2. checkpoint 恢复后不重复执行已完成节点。
3. 非法状态流转被 100% 拦截。
4. failed 状态都可关联到 DLQ 记录。

## 12. 参考来源（核验：2026-02-21）

1. LangGraph interrupts/persistence/durable execution:  
   https://docs.langchain.com/oss/python/langgraph/
2. 历史融合提交：`7f05f7e`, `72a64da`
