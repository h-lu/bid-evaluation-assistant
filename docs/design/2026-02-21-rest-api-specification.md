# REST API 规范

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 通用约定

1. 基础路径：`/api/v1`
2. 鉴权：JWT Bearer（租户从 token 注入）
3. 写接口：强制 `Idempotency-Key`
4. 长任务：返回 `202 Accepted + job_id`
5. 所有响应：包含 `trace_id`

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

## 3. 认证与会话接口

1. `POST /auth/login`
2. `POST /auth/refresh`
3. `POST /auth/logout`
4. `GET /auth/me`

约束：

1. refresh token 走 HttpOnly Cookie。
2. refresh 接口启用 CSRF 校验。

## 4. 业务资源接口

### 4.1 Projects

1. `GET /projects`
2. `POST /projects`
3. `GET /projects/{project_id}`
4. `PUT /projects/{project_id}`
5. `DELETE /projects/{project_id}`

### 4.2 Suppliers

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
2. `GET /evaluations/{evaluation_id}`
3. `GET /evaluations/{evaluation_id}/report`
4. `POST /evaluations/{evaluation_id}/resume` -> `202 + job_id`

### 4.6 Jobs

1. `GET /jobs/{job_id}`
2. `GET /jobs?status=&type=&cursor=`
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
    "degraded": false,
    "items": [
      {
        "chunk_id": "ck_xxx",
        "score_raw": 0.82,
        "score_rerank": 0.89,
        "reason": "matched relation intent",
        "metadata": {
          "project_id": "prj_xxx",
          "supplier_id": "sup_xxx",
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

### 5.11 `POST /retrieval/preview`

请求体：与 `POST /retrieval/query` 相同。

响应 `200`：

```json
{
  "success": true,
  "data": {
    "query": "投标文件中与交付周期相关的承诺",
    "selected_mode": "global",
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
