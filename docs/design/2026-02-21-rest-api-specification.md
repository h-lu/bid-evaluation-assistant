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

1. `POST /documents/upload` -> `202 + job_id`
2. `POST /documents/{document_id}/parse` -> `202 + job_id`
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

## 5. 长任务契约

### 5.1 提交返回

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

### 5.2 任务状态

`queued -> running -> retrying -> succeeded|failed`

附加状态：`needs_manual_decision`, `dlq_pending`, `dlq_recorded`。

## 6. 幂等策略

1. `Idempotency-Key` 有效期 24h。
2. 同 key + 同 body 返回同结果。
3. 同 key + 异 body 返回 `409 IDEMPOTENCY_CONFLICT`。

## 7. 分页与筛选

1. 列表接口统一 cursor 分页：`cursor/limit`。
2. 默认 `limit=20`，最大 `limit=100`。
3. 必须支持 `created_at` 倒序。

## 8. 错误码分组

1. `AUTH_*`：认证鉴权
2. `REQ_*`：请求验证
3. `TENANT_*`：租户隔离
4. `WF_*`：工作流与状态机
5. `DLQ_*`：死信与运维
6. `UPSTREAM_*`：上游依赖

## 9. 安全约束

1. 禁止客户端传 `tenant_id`。
2. 高风险接口强制二次确认信息。
3. 生产环境不返回堆栈。
4. 所有敏感接口写审计日志。

## 10. OpenAPI 与兼容性

1. 所有接口必须声明 request/response schema。
2. 破坏性变更必须升级 minor 版本并提供迁移说明。
3. 废弃接口保留至少一个发布周期。

## 11. 验收标准

1. 核心接口契约测试通过。
2. 异步接口状态流转正确。
3. 幂等冲突与重放行为符合规范。
4. 所有错误响应包含 `trace_id`。

## 12. 参考来源（核验：2026-02-21）

1. FastAPI docs: https://fastapi.tiangolo.com/
2. 历史融合提交：`beef3e9`, `7f05f7e`
