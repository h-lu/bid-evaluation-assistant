# REST API 规范

> 版本：v2026.02.21-r4  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 通用约定

1. 基础路径：`/api/v1`
2. 鉴权：JWT Bearer（租户从 token 注入）
3. 写接口：强制 `Idempotency-Key`
4. 长任务：返回 `202 Accepted + job_id`
5. 所有响应：包含 `trace_id`
6. 所有响应头：包含 `x-trace-id` 与 `x-request-id`

## 2. 统一响应模型

### 2.1 Success

```json
{
  "success": true,
  "data": {},
  "message": "ok",
  "meta": {
    "trace_id": "trace_xxx",
    "request_id": "req_xxx"
  }
}
```

### 2.2 Error

```json
{
  "success": false,
  "error": {
    "code": "REQ_VALIDATION_FAILED",
    "message": "invalid payload",
    "retryable": false,
    "class": "validation"
  },
  "meta": {
    "trace_id": "trace_xxx",
    "request_id": "req_xxx"
  }
}
```

## 3. 认证与会话接口（规划，未纳入当前 v1 契约子集）

1. `POST /auth/login`
2. `POST /auth/refresh`
3. `POST /auth/logout`
4. `GET /auth/me`

约束：

1. refresh token 走 HttpOnly Cookie。
2. refresh 接口启用 CSRF 校验。

## 4. 业务资源接口

### 4.1 Projects（规划，未纳入当前 v1 契约子集）

1. `GET /projects`
2. `POST /projects`
3. `GET /projects/{project_id}`
4. `PUT /projects/{project_id}`
5. `DELETE /projects/{project_id}`

### 4.2 Suppliers（规划，未纳入当前 v1 契约子集）

1. `GET /suppliers`
2. `POST /suppliers`
3. `GET /suppliers/{supplier_id}`
4. `PUT /suppliers/{supplier_id}`

### 4.3 Documents

1. `POST /documents/upload` -> `202 + parse job_id`（上传后自动投递 parse）
2. `POST /documents/{document_id}/parse` -> `202 + job_id`（手动重投/补投）
3. `GET /documents/{document_id}`
4. `GET /documents/{document_id}/chunks`

### 4.4 Retrieval

1. `POST /retrieval/query`
2. `POST /retrieval/preview`

### 4.5 Evaluations

1. `POST /evaluations` -> `202 + job_id`
2. `GET /evaluations/{evaluation_id}`（规划，未纳入当前 v1 契约子集）
3. `GET /evaluations/{evaluation_id}/report`
4. `POST /evaluations/{evaluation_id}/resume` -> `202 + job_id`

### 4.6 Jobs

1. `GET /jobs/{job_id}`
2. `GET /jobs`（支持查询参数：`status/type/cursor`）
3. `POST /jobs/{job_id}/cancel`

### 4.7 DLQ（受限）

1. `GET /dlq/items`
2. `POST /dlq/items/{item_id}/requeue`
3. `POST /dlq/items/{item_id}/discard`

### 4.8 Citations

1. `GET /citations/{chunk_id}/source`

返回最小字段：`document_id/page/bbox/text/context`。

### 4.9 Internal Gates（内部调试）

1. `POST /internal/quality-gates/evaluate`
2. `POST /internal/performance-gates/evaluate`
3. `POST /internal/security-gates/evaluate`
4. `POST /internal/cost-gates/evaluate`

说明：

1. 仅内部调试与门禁流水线使用，必须携带 `x-internal-debug: true`。
2. 质量门禁输入 RAGAS/DeepEval/citation 指标，返回通过/阻断结论。
3. 性能门禁输入 P95、队列稳定性与缓存命中率指标。
4. 安全门禁输入越权/绕过/审批/脱敏/密钥扫描结果。
5. 成本门禁输入成本 P95、模型降级可用性与预算告警覆盖率。
6. 当质量门禁不达标时，触发 `RAGChecker` 诊断流程标记。

### 4.10 Internal Release（Gate E 内部发布控制）

1. `POST /internal/release/rollout/plan`
2. `POST /internal/release/rollout/decision`
3. `POST /internal/release/rollback/execute`
4. `POST /internal/release/replay/e2e`
5. `POST /internal/release/readiness/evaluate`
6. `POST /internal/release/pipeline/execute`

说明：

1. 仅灰度/回滚流水线使用，必须携带 `x-internal-debug: true`。
2. 灰度放量顺序固定为“租户白名单 -> 项目规模分层（small/medium/large）”。
3. `high_risk=true` 时强制 `force_hitl=true`，不可绕过。
4. 回滚触发条件为“任一门禁连续超阈值（默认阈值 2 次）”。
5. 回滚执行顺序固定为：`model_config -> retrieval_params -> workflow_version -> release_version`。
6. 回滚执行后必须触发一次 `replay verification`。
7. `replay/e2e` 会执行上传、解析、评估与（可选）自动恢复，产出 `passed`。
8. `readiness/evaluate` 汇总 Gate D/E/F 与 replay 结果，给出发布准入结论。
9. `pipeline/execute` 将 readiness 与 canary/rollback 配置收口为单次发布决策输出。

### 4.11 Internal Ops（Gate F 运行优化）

1. `GET /internal/ops/metrics/summary`
2. `POST /internal/ops/data-feedback/run`
3. `POST /internal/ops/strategy-tuning/apply`

说明：

1. 仅运维优化流水线使用，必须携带 `x-internal-debug: true`。
2. 数据回流会将 DLQ 样本写入反例集，并将人审改判样本写入黄金集候选。
3. 每次回流执行都必须产出新的评估数据集版本号。
4. 策略优化同步更新 selector 阈值、评分校准参数、工具权限审批策略。
5. metrics summary 按租户聚合 API/Worker/Quality/Cost/SLO 指标视图。

### 4.12 Internal Persistence & Queue（生产化调试）

1. `GET /internal/outbox/events`
2. `POST /internal/outbox/events/{event_id}/publish`
3. `POST /internal/outbox/relay`
4. `POST /internal/queue/{queue_name}/enqueue`
5. `POST /internal/queue/{queue_name}/dequeue`
6. `POST /internal/queue/{queue_name}/ack`
7. `POST /internal/queue/{queue_name}/nack`

说明：

1. 仅内部链路联调使用，必须携带 `x-internal-debug: true`。
2. `relay` 会将 `pending` outbox 事件转为队列消息，并标记为 `published`。
3. 队列消息最小字段：`event_id/job_id/tenant_id/trace_id/job_type/attempt`。
4. 队列消费保持租户隔离，跨租户不可见。

### 4.13 Internal Workflow（生产化调试）

1. `GET /internal/workflows/{thread_id}/checkpoints`
2. `POST /internal/worker/queues/{queue_name}/drain-once`

说明：

1. 仅内部联调使用，必须携带 `x-internal-debug: true`。
2. checkpoint 查询按 `thread_id + tenant_id` 过滤。
3. `thread_id` 由任务创建时分配，并在 resume 任务中复用。
4. `drain-once` 每次最多消费 `max_messages` 条消息并驱动对应 job 执行。
5. 当任务进入 `retrying` 时，worker 按指数退避结果执行延迟重投（`nack(delay_ms)`）。

## 5. 字段级契约（关键接口示例）

### 5.1 `POST /documents/upload`

请求头：

1. `Authorization: Bearer <access_token>`
2. `Idempotency-Key: idem_xxx`
3. `Content-Type: multipart/form-data`

请求字段：

1. `project_id`（string, required）
2. `supplier_id`（string, required）
3. `doc_type`（enum: `tender|bid|attachment`, required）
4. `file`（binary, required）

响应 `202`：

```json
{
  "success": true,
  "data": {
    "document_id": "doc_xxx",
    "job_id": "job_xxx",
    "status": "queued",
    "next": "/api/v1/jobs/job_xxx"
  },
  "meta": {
    "trace_id": "trace_xxx",
    "request_id": "req_xxx"
  }
}
```

说明：

1. `data.job_id` 对应自动投递的 parse 任务，可直接用于 `GET /jobs/{job_id}` 查询。
2. 上传受理后文档状态进入 `parse_queued`。

错误：

1. `REQ_VALIDATION_FAILED`
2. `IDEMPOTENCY_CONFLICT`
3. `TENANT_SCOPE_VIOLATION`

### 5.2 `POST /evaluations`

请求头：

1. `Authorization: Bearer <access_token>`
2. `Idempotency-Key: idem_xxx`
3. `Content-Type: application/json`

请求体：

```json
{
  "project_id": "prj_xxx",
  "supplier_id": "sup_xxx",
  "rule_pack_version": "v1.3.0",
  "evaluation_scope": {
    "include_doc_types": ["bid", "attachment"],
    "force_hitl": false
  },
  "query_options": {
    "mode_hint": "hybrid",
    "top_k": 60
  }
}
```

响应 `202`：

```json
{
  "success": true,
  "data": {
    "evaluation_id": "ev_xxx",
    "job_id": "job_xxx",
    "status": "queued"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 评分流程先执行规则引擎硬约束判定。
2. 当硬约束不通过时，报告返回 `criteria_results[*].hard_pass=false`，并阻断软评分（总分为 `0`，风险等级提升）。

### 5.3 `GET /jobs/{job_id}`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "job_id": "job_xxx",
    "job_type": "evaluation",
    "status": "running",
    "progress_pct": 65,
    "retry_count": 1,
    "thread_id": "thr_eval_xxx",
    "trace_id": "trace_xxx",
    "resource": {
      "type": "evaluation",
      "id": "ev_xxx"
    },
    "last_error": null
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.4 `POST /evaluations/{evaluation_id}/resume`

请求体：

```json
{
  "resume_token": "rt_xxx",
  "decision": "approve",
  "comment": "证据充分，允许继续",
  "editor": {
    "reviewer_id": "u_xxx"
  },
  "edited_scores": []
}
```

响应 `202`：

```json
{
  "success": true,
  "data": {
    "evaluation_id": "ev_xxx",
    "job_id": "job_resume_xxx",
    "status": "queued"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

错误：

1. `WF_INTERRUPT_RESUME_INVALID`
2. `REQ_VALIDATION_FAILED`
3. `WF_INTERRUPT_REVIEWER_REQUIRED`

约束：

1. `resume_token` 单次有效。
2. `resume_token` 自签发起 24 小时内有效，超时后返回 `WF_INTERRUPT_RESUME_INVALID`。

### 5.5 `GET /citations/{chunk_id}/source`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "chunk_id": "ck_xxx",
    "document_id": "doc_xxx",
    "filename": "投标文件-A.pdf",
    "page": 8,
    "bbox": [120.2, 310.0, 520.8, 365.4],
    "text": "原文片段...",
    "context": "上下文...",
    "viewport_hint": {
      "scale": 1.0,
      "unit": "pdf_point"
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.6 `POST /internal/quality-gates/evaluate`

请求体：

```json
{
  "dataset_id": "ds_gate_d_smoke",
  "metrics": {
    "ragas": {
      "context_precision": 0.82,
      "context_recall": 0.81,
      "faithfulness": 0.91,
      "response_relevancy": 0.87
    },
    "deepeval": {
      "hallucination_rate": 0.03
    },
    "citation": {
      "resolvable_rate": 0.99
    }
  }
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "gate": "quality",
    "passed": true,
    "failed_checks": [],
    "thresholds": {
      "ragas_context_precision_min": 0.8,
      "ragas_context_recall_min": 0.8,
      "ragas_faithfulness_min": 0.9,
      "ragas_response_relevancy_min": 0.85,
      "deepeval_hallucination_rate_max": 0.05,
      "citation_resolvable_rate_min": 0.98
    },
    "values": {
      "context_precision": 0.82,
      "context_recall": 0.81,
      "faithfulness": 0.91,
      "response_relevancy": 0.87,
      "hallucination_rate": 0.03,
      "citation_resolvable_rate": 0.99
    },
    "ragchecker": {
      "triggered": false,
      "reason_codes": []
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.7 `POST /internal/performance-gates/evaluate`

请求体：

```json
{
  "dataset_id": "ds_perf_smoke",
  "metrics": {
    "api_p95_s": 1.2,
    "retrieval_p95_s": 3.5,
    "parse_50p_p95_s": 170.0,
    "evaluation_p95_s": 100.0,
    "queue_dlq_rate": 0.006,
    "cache_hit_rate": 0.75
  }
}
```

响应 `200`：返回 `gate=performance`、`passed`、`failed_checks`、阈值与观测值。

### 5.8 `POST /internal/security-gates/evaluate`

请求体：

```json
{
  "dataset_id": "ds_security_smoke",
  "metrics": {
    "tenant_scope_violations": 0,
    "auth_bypass_findings": 0,
    "high_risk_approval_coverage": 1.0,
    "log_redaction_failures": 0,
    "secret_scan_findings": 0
  }
}
```

响应 `200`：返回 `gate=security`、`passed`、`failed_checks`、阈值与观测值。

### 5.9 `POST /internal/cost-gates/evaluate`

请求体：

```json
{
  "dataset_id": "ds_cost_smoke",
  "metrics": {
    "task_cost_p95": 1.08,
    "baseline_task_cost_p95": 1.0,
    "routing_degrade_passed": true,
    "degrade_availability": 0.997,
    "budget_alert_coverage": 1.0
  }
}
```

响应 `200`：返回 `gate=cost`、`passed`、`failed_checks`、阈值与观测值。

### 5.10 `POST /retrieval/query`

请求体：

```json
{
  "project_id": "prj_xxx",
  "supplier_id": "sup_xxx",
  "query": "投标文件中与交付周期相关的承诺",
  "query_type": "relation",
  "must_include_terms": ["交付", "周期"],
  "must_exclude_terms": ["质保"],
  "enable_rerank": true,
  "top_k": 20,
  "doc_scope": ["bid"]
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "query": "投标文件中与交付周期相关的承诺",
    "rewritten_query": "投标文件 与 交付周期 相关承诺",
    "rewrite_reason": "normalize_whitespace_and_terms",
    "constraints_preserved": true,
    "constraint_diff": [],
    "query_type": "relation",
    "selected_mode": "global",
    "index_name": "lightrag:tenant_a:prj_xxx",
    "degraded": false,
    "degrade_reason": null,
    "items": [
      {
        "chunk_id": "ck_xxx",
        "score_raw": 0.82,
        "score_rerank": 0.89,
        "reason": "matched relation intent",
        "metadata": {
          "tenant_id": "tenant_a",
          "project_id": "prj_xxx",
          "supplier_id": "sup_xxx",
          "document_id": "doc_xxx",
          "doc_type": "bid",
          "page": 8,
          "bbox": [120.2, 310.0, 520.8, 365.4]
        }
      }
    ],
    "total": 1
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

错误：

1. `REQ_VALIDATION_FAILED`
2. `TENANT_SCOPE_VIOLATION`
3. rerank 降级时 `data.degraded=true`，并回退到原召回分排序
4. rerank 降级原因通过 `data.degrade_reason` 返回（例如 `rerank_failed`/`rerank_disabled`）

### 5.11 `POST /retrieval/preview`

请求体：与 `POST /retrieval/query` 相同。

响应 `200`：

```json
{
  "success": true,
  "data": {
    "query": "投标文件中与交付周期相关的承诺",
    "selected_mode": "global",
    "index_name": "lightrag:tenant_a:prj_xxx",
    "degraded": false,
    "items": [
      {
        "chunk_id": "ck_xxx",
        "document_id": "doc_xxx",
        "page": 8,
        "bbox": [120.2, 310.0, 520.8, 365.4],
        "text": "原文片段..."
      }
    ],
    "total": 1
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.12 `GET /evaluations/{evaluation_id}/report`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "evaluation_id": "ev_xxx",
    "supplier_id": "sup_xxx",
    "total_score": 88.5,
    "confidence": 0.78,
    "citation_coverage": 1.0,
    "risk_level": "medium",
    "criteria_results": [
      {
        "criteria_id": "delivery",
        "score": 18.0,
        "max_score": 20.0,
        "hard_pass": true,
        "reason": "交付周期满足要求",
        "citations": ["ck_xxx"],
        "confidence": 0.81
      }
    ],
    "citations": ["ck_xxx"],
    "needs_human_review": false,
    "trace_id": "trace_xxx",
    "interrupt": null
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.13 `GET /documents/{document_id}`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "document_id": "doc_xxx",
    "project_id": "prj_xxx",
    "supplier_id": "sup_xxx",
    "doc_type": "bid",
    "filename": "bid.pdf",
    "status": "indexed"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.14 `GET /documents/{document_id}/chunks`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "document_id": "doc_xxx",
    "items": [
      {
        "chunk_id": "ck_xxx",
        "document_id": "doc_xxx",
        "pages": [1],
        "positions": [
          {
            "page": 1,
            "bbox": [100, 120, 520, 380],
            "start": 0,
            "end": 128
          }
        ],
        "section": "投标响应",
        "heading_path": ["第一章", "响应说明"],
        "chunk_type": "text",
        "parser": "mineru",
        "parser_version": "v0",
        "text": "原文片段..."
      }
    ],
    "total": 1
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.15 `POST /internal/release/rollout/decision`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "tenant_id": "tenant_a",
  "project_size": "small",
  "high_risk": true
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "release_id": "rel_20260222_01",
    "admitted": true,
    "stage": "tenant_whitelist+project_size",
    "matched_whitelist": true,
    "force_hitl": true,
    "reasons": []
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 若租户不在白名单，`admitted=false` 且 `reasons` 含 `TENANT_NOT_IN_WHITELIST`。
2. 若项目规模未放量，`admitted=false` 且 `reasons` 含 `PROJECT_SIZE_NOT_ENABLED`。
3. 若 `high_risk=true`，无条件返回 `force_hitl=true`。

### 5.16 `POST /internal/release/rollback/execute`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "consecutive_threshold": 2,
  "breaches": [
    {
      "gate": "quality",
      "metric_code": "DEEPEVAL_HALLUCINATION_RATE_HIGH",
      "consecutive_failures": 2
    }
  ]
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "release_id": "rel_20260222_01",
    "triggered": true,
    "trigger_gate": "quality",
    "rollback_order": [
      "model_config",
      "retrieval_params",
      "workflow_version",
      "release_version"
    ],
    "replay_verification": {
      "job_id": "job_xxx",
      "status": "succeeded"
    },
    "elapsed_minutes": 8,
    "rollback_completed_within_30m": true,
    "service_restored": true
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 当且仅当存在 `consecutive_failures >= consecutive_threshold` 的 breach 时触发回滚。
2. 回滚完成后必须创建并执行一次回放验证任务。
3. `rollback_completed_within_30m=false` 视为 Gate E 验收失败。

### 5.16A `POST /internal/release/replay/e2e`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "project_id": "prj_release",
  "supplier_id": "sup_release",
  "doc_type": "bid",
  "force_hitl": true,
  "decision": "approve"
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "replay_run_id": "rpy_xxx",
    "release_id": "rel_20260222_01",
    "tenant_id": "tenant_a",
    "parse": {
      "job_id": "job_parse_xxx",
      "status": "succeeded"
    },
    "evaluation": {
      "evaluation_id": "ev_xxx",
      "job_id": "job_eval_xxx",
      "resume_job_id": "job_resume_xxx",
      "needs_human_review": false
    },
    "passed": true
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 仅内部发布准入验证使用，必须携带 `x-internal-debug: true`。
2. `force_hitl=true` 时会尝试按 `decision` 自动提交恢复动作。
3. `passed` 仅在 parse 成功且评估链路满足通过条件时为 `true`。

### 5.16B `POST /internal/release/readiness/evaluate`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "replay_passed": true,
  "gate_results": {
    "quality": true,
    "performance": true,
    "security": true,
    "cost": true,
    "rollout": true,
    "rollback": true,
    "ops": true
  }
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "assessment_id": "ra_xxx",
    "release_id": "rel_20260222_01",
    "tenant_id": "tenant_a",
    "admitted": true,
    "failed_checks": [],
    "replay_passed": true,
    "gate_results": {
      "quality": true,
      "performance": true,
      "security": true,
      "cost": true,
      "rollout": true,
      "rollback": true,
      "ops": true
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 仅内部发布准入流水线使用，必须携带 `x-internal-debug: true`。
2. 任一门禁为 `false` 或 `replay_passed=false`，都必须阻断发布（`admitted=false`）。
3. `failed_checks` 必须给出可审计的失败原因列表。

### 5.16C `POST /internal/release/pipeline/execute`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "replay_passed": true,
  "gate_results": {
    "quality": true,
    "performance": true,
    "security": true,
    "cost": true,
    "rollout": true,
    "rollback": true,
    "ops": true
  }
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "pipeline_id": "pl_xxx",
    "release_id": "rel_20260222_01",
    "tenant_id": "tenant_a",
    "stage": "release_ready",
    "admitted": true,
    "failed_checks": [],
    "readiness_assessment_id": "ra_xxx",
    "canary": {
      "ratio": 0.1,
      "duration_min": 30
    },
    "rollback": {
      "max_minutes": 30
    },
    "readiness_required": true
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 仅内部发布流水线使用，必须携带 `x-internal-debug: true`。
2. 当 `readiness_required=true` 时，会先执行 readiness 判定；不通过则 `stage=release_blocked`。
3. 输出中的 canary/rollback 字段来自运行时配置，用于后续自动化步骤执行。

### 5.17 `POST /internal/ops/data-feedback/run`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "dlq_ids": ["dlq_xxx"],
  "version_bump": "patch",
  "include_manual_override_candidates": true
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "release_id": "rel_20260222_01",
    "counterexample_added": 1,
    "gold_candidates_added": 1,
    "dataset_version_before": "v1.0.0",
    "dataset_version_after": "v1.0.1"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. `dlq_ids` 为空时按当前租户全量 DLQ 样本回流。
2. 仅 `resume_submitted` 且 `decision in {reject, edit_scores}` 的审计样本计入黄金集候选。
3. `dataset_version_after` 必须不同于 `dataset_version_before`。

### 5.18 `POST /internal/ops/strategy-tuning/apply`

请求体：

```json
{
  "release_id": "rel_20260222_01",
  "selector": {
    "risk_mix_threshold": 0.72,
    "relation_mode": "global"
  },
  "score_calibration": {
    "confidence_scale": 1.05,
    "score_bias": -0.5
  },
  "tool_policy": {
    "require_double_approval_actions": ["dlq_discard"],
    "allowed_tools": ["retrieval", "evaluation", "dlq"]
  }
}
```

响应 `200`：

```json
{
  "success": true,
  "data": {
    "release_id": "rel_20260222_01",
    "strategy_version": "stg_v2",
    "selector": {
      "risk_mix_threshold": 0.72,
      "relation_mode": "global"
    },
    "score_calibration": {
      "confidence_scale": 1.05,
      "score_bias": -0.5
    },
    "tool_policy": {
      "require_double_approval_actions": ["dlq_discard"],
      "allowed_tools": ["retrieval", "evaluation", "dlq"]
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 每次策略变更必须生成新 `strategy_version`。
2. 高风险动作审批策略变更必须体现在 `tool_policy` 字段返回值中。

### 5.19 `POST /internal/outbox/relay`

请求参数：

1. `queue_name`（query，可选，默认 `jobs`）
2. `consumer_name`（query，可选，默认 `default`）
3. `limit`（query，可选，默认 `100`，范围 `1..1000`）

响应 `200`：

```json
{
  "success": true,
  "data": {
    "published_count": 1,
    "queued_count": 1,
    "message_ids": ["msg_xxx"],
    "consumer_name": "worker-a"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

规则说明：

1. 仅消费当前租户 `status=pending` 的 outbox 事件。
2. 成功入队后事件必须原子标记为 `published`。
3. 同一 `consumer_name` 对同一 `event_id` 重复 relay 不得重复入队（幂等键：`event_id + consumer_name`）。
4. 不同 `consumer_name` 可对同一事件各消费一次。

### 5.20 Internal Queue 接口族

`enqueue` 请求体示例：

```json
{
  "job_id": "job_xxx",
  "tenant_id": "tenant_a",
  "trace_id": "trace_xxx",
  "job_type": "evaluation",
  "attempt": 0
}
```

`dequeue` 响应 `200`：

```json
{
  "success": true,
  "data": {
    "message": {
      "message_id": "msg_xxx",
      "tenant_id": "tenant_a",
      "queue_name": "jobs",
      "attempt": 0,
      "payload": {
        "job_id": "job_xxx"
      }
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

`ack` 请求体示例：

```json
{
  "message_id": "msg_xxx"
}
```

`nack` 请求体示例：

```json
{
  "message_id": "msg_xxx",
  "requeue": true
}
```

约束：

1. `ack/nack` 仅允许操作本租户 inflight 消息。
2. 跨租户操作返回 `403 + TENANT_SCOPE_VIOLATION`。

### 5.21 `GET /internal/workflows/{thread_id}/checkpoints`

请求参数：

1. `thread_id`（path，必填）
2. `limit`（query，可选，默认 `100`，范围 `1..1000`）

响应 `200`：

```json
{
  "success": true,
  "data": {
    "thread_id": "thr_eval_xxx",
    "items": [
      {
        "checkpoint_id": "cp_xxx",
        "thread_id": "thr_eval_xxx",
        "job_id": "job_xxx",
        "seq": 1,
        "node": "job_started",
        "status": "running",
        "payload": {
          "job_type": "parse"
        },
        "tenant_id": "tenant_a",
        "created_at": "2026-02-22T10:00:00Z"
      }
    ],
    "total": 1
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.22 `GET /internal/ops/metrics/summary`

请求参数：

1. `queue_name`（query，可选，默认 `jobs`）

响应 `200`：

```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant_a",
    "api": {
      "total_jobs": 12,
      "succeeded_jobs": 9,
      "failed_jobs": 2,
      "error_rate": 0.1667
    },
    "worker": {
      "retrying_jobs": 1,
      "dlq_open": 1,
      "outbox_pending": 0,
      "max_retries": 3,
      "retry_backoff_base_ms": 1000,
      "retry_backoff_max_ms": 30000,
      "resume_token_ttl_hours": 24,
      "checkpoint_backend": "postgres",
      "queue_name": "jobs",
      "queue_pending": 0
    },
    "quality": {
      "report_count": 3,
      "citation_coverage_avg": 1.0
    },
    "cost": {
      "dataset_version": "v1.0.1",
      "strategy_version": "stg_v2"
    },
    "slo": {
      "success_rate": 0.75
    }
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.23 `POST /internal/worker/queues/{queue_name}/drain-once`

请求参数：

1. `queue_name`（path，必填）
2. `max_messages`（query，可选，默认 `1`，范围 `1..100`）
3. `force_fail`（query，可选，默认 `false`）
4. `transient_fail`（query，可选，默认 `false`）
5. `error_code`（query，可选）

响应 `200`：

```json
{
  "success": true,
  "data": {
    "queue_name": "jobs",
    "processed": 1,
    "succeeded": 1,
    "retrying": 0,
    "failed": 0,
    "acked": 1,
    "requeued": 0,
    "message_ids": ["msg_xxx"]
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 5.11 `GET /evaluations/{evaluation_id}/audit-logs`

响应 `200`：

```json
{
  "success": true,
  "data": {
    "evaluation_id": "ev_xxx",
    "items": [
      {
        "audit_id": "audit_xxx",
        "action": "resume_submitted",
        "reviewer_id": "u_xxx",
        "decision": "approve",
        "comment": "证据充分，允许继续",
        "trace_id": "trace_xxx",
        "occurred_at": "2026-02-21T09:30:00Z"
      }
    ],
    "total": 1
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

当命中 HITL 条件（例如 `force_hitl=true`）时，`data.interrupt` 返回：

```json
{
  "type": "human_review",
  "evaluation_id": "ev_xxx",
  "reasons": ["force_hitl"],
  "suggested_actions": ["approve", "reject", "edit_scores"],
  "resume_token": "rt_xxx"
}
```

## 6. 长任务契约

### 6.1 提交返回

```json
{
  "success": true,
  "data": {
    "job_id": "job_xxx",
    "status": "queued"
  },
  "meta": {
    "trace_id": "trace_xxx"
  }
}
```

### 6.2 任务状态

`queued -> running -> retrying -> succeeded|failed`

### 5.15 DLQ 运维动作接口

约束：

1. `requeue/discard` 成功后必须写审计日志。
2. 审计动作分别为 `dlq_requeue_submitted`、`dlq_discard_submitted`。

附加状态：`needs_manual_decision`, `dlq_pending`, `dlq_recorded`。

## 7. 幂等策略

1. `Idempotency-Key` 有效期 24h。
2. 同 key + 同 body 返回同结果。
3. 同 key + 异 body 返回 `409 IDEMPOTENCY_CONFLICT`。

## 8. 分页与筛选

1. 列表接口统一 cursor 分页：`cursor/limit`。
2. 默认 `limit=20`，最大 `limit=100`。
3. 必须支持 `created_at` 倒序。

## 9. 错误码分组

1. `AUTH_*`：认证鉴权
2. `REQ_*`：请求验证
3. `TENANT_*`：租户隔离
4. `WF_*`：工作流与状态机
5. `DLQ_*`：死信与运维
6. `UPSTREAM_*`：上游依赖

## 10. 安全约束

1. 禁止客户端传 `tenant_id`。
2. 高风险接口强制二次确认信息。
3. 生产环境不返回堆栈。
4. 所有敏感接口写审计日志。

## 11. OpenAPI 与兼容性

1. 所有接口必须声明 request/response schema。
2. 破坏性变更必须升级 minor 版本并提供迁移说明。
3. 废弃接口保留至少一个发布周期。
4. OpenAPI 基线文件：`docs/design/2026-02-21-openapi-v1.yaml`。
5. 契约测试样例：`docs/design/2026-02-21-api-contract-test-samples.md`。
6. 任何接口字段变更必须同步更新上述两个文件。

## 12. 验收标准

1. 核心接口契约测试通过。
2. 异步接口状态流转正确。
3. 幂等冲突与重放行为符合规范。
4. 所有错误响应包含 `trace_id`。

## 13. 参考来源（核验：2026-02-21）

1. FastAPI docs: https://fastapi.tiangolo.com/
2. 历史融合提交：`beef3e9`, `7f05f7e`
