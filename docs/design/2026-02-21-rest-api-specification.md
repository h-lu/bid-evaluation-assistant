# REST API 规范

> 版本：v3.0
> 日期：2026-02-21
> 架构基线：`docs/plans/2026-02-21-end-to-end-unified-design.md`

---

## 1. 通用规范

- 前缀：`/api/v1`
- 鉴权：JWT Bearer
- 多租户：`tenant_id` 从 JWT 提取，客户端不可指定
- 统一响应：`success/data/message/meta(trace_id)`
- 统一错误：`success=false + error.code + trace_id`

---

## 2. 角色与权限

- `admin`
- `agent`
- `evaluator`
- `viewer`

高风险动作：`DLQ discard`、终审发布，要求二次确认并审计。

---

## 3. 核心资源接口

### 3.1 Projects

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `PUT /api/v1/projects/{id}`
- `DELETE /api/v1/projects/{id}`

### 3.2 Suppliers

- `GET /api/v1/suppliers`
- `POST /api/v1/suppliers`
- `GET /api/v1/suppliers/{id}`
- `PUT /api/v1/suppliers/{id}`

### 3.3 Documents

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/chunks`
- `GET /api/v1/documents/{id}/download`

### 3.4 Retrieval

- `POST /api/v1/retrieval/query`
- `POST /api/v1/retrieval/index`

### 3.5 Evaluations

- `POST /api/v1/evaluations`
- `POST /api/v1/evaluations/{id}/start`
- `GET /api/v1/evaluations/{id}/results`
- `POST /api/v1/evaluations/{id}/review`
- `GET /api/v1/evaluations/{id}/report`

---

## 4. 异步任务接口

### 4.1 任务入口（统一 202）

- `POST /api/v1/documents/{id}/parse`
- `POST /api/v1/retrieval/index`
- `POST /api/v1/evaluations/{id}/start`

幂等规则：

1. 必须携带 `Idempotency-Key`（有效期 24h）。
2. 同 key + 同请求体：返回原 `job_id`（200）。
3. 同 key + 不同请求体：返回 `409 IDEMPOTENCY_CONFLICT`。

返回示例：

```json
{
  "success": true,
  "data": {
    "job_id": "job_xxx",
    "status": "queued",
    "status_url": "/api/v1/jobs/job_xxx"
  },
  "meta": {"trace_id": "..."}
}
```

### 4.2 任务查询与控制

- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `POST /api/v1/jobs/{job_id}/resume`（仅 `needs_manual_decision`）

任务状态：

- `queued`
- `running`
- `retrying`
- `needs_manual_decision`
- `succeeded`
- `failed`
- `cancelled`

失败任务附加字段：`dlq_id`、`failed_reason`。

### 4.3 状态转换约束

1. `queued -> running`
2. `running -> retrying`
3. `retrying -> running`
4. `running|retrying -> needs_manual_decision`
5. `running|retrying -> failed`（先写 DLQ）
6. `needs_manual_decision -> running`（resume）
7. `running|retrying -> succeeded|cancelled`

---

## 5. DLQ 运维接口

- `GET /api/v1/dlq`
- `GET /api/v1/dlq/{dlq_id}`
- `POST /api/v1/dlq/{dlq_id}/requeue`
- `POST /api/v1/dlq/{dlq_id}/discard`

权限边界（同租户内）：

- `admin`：查询/重放/废弃
- `agent`：查询/重放（废弃需 admin 复核）
- `evaluator`：仅查询
- `viewer`：无权限

所有 DLQ 操作必须写审计日志（操作者、原因、`trace_id`）。

---

## 6. 统一结果契约

检索与评估响应必须包含：

- `answer`
- `citations`
- `confidence`
- `mode_used`
- `trace_id`

---

## 7. 健康检查

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/live`

---

## 8. 常见错误码

- `UNAUTHORIZED`（401）
- `FORBIDDEN`（403）
- `NOT_FOUND`（404）
- `VALIDATION_ERROR`（422）
- `IDEMPOTENCY_CONFLICT`（409）
- `TENANT_SCOPE_VIOLATION`（403）
