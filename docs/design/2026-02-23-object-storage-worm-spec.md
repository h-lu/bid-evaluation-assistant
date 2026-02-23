# 对象存储与 WORM 保全规范

> 版本：v2026.02.23-r1  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 将原始文档与评估报告落入对象存储，形成可审计的证据归档链路。
2. 提供最小 WORM 语义：写入后不可覆盖，legal hold/retention 生效时不可删除。
3. 与现有 API 契约（`legal-hold/*`、`storage/cleanup`）一致，不新增破坏性字段。

## 2. 范围与非目标

### 2.1 纳入范围

1. 原始上传文档写入对象存储。
2. 评估报告写入对象存储（JSON 归档）。
3. `legal hold` 影响对象存储删除行为。
4. `storage/cleanup` 触发对象存储删除。

### 2.2 非目标

1. 跨区域复制与多活。
2. 自动归档与生命周期策略编排（可在后续运维策略补充）。
3. 对象存储权限细粒度策略平台化。

## 3. 对象存储抽象

### 3.1 接口最小集合

1. `put_object(tenant_id, object_type, object_id, filename, content_bytes, content_type) -> storage_uri`
2. `get_object(storage_uri) -> bytes`
3. `delete_object(storage_uri) -> deleted(bool)`
4. `apply_legal_hold(storage_uri) -> bool`
5. `release_legal_hold(storage_uri) -> bool`
6. `is_legal_hold_active(storage_uri) -> bool`
7. `set_retention(storage_uri, mode, retain_until) -> bool`
8. `get_retention(storage_uri) -> {mode, retain_until} | None`
9. `is_retention_active(storage_uri, now) -> bool`

### 3.2 URI 规范

统一使用内部 URI：

```text
object://{backend}/{bucket}/{key}
```

示例：

```text
object://local/bea/tenants/tenant_a/documents/doc_x/raw/bid.pdf
object://local/bea/tenants/tenant_a/reports/ev_x/report.json
```

## 4. Key 规范

1. 原始文档：
   - `tenants/{tenant_id}/documents/{document_id}/raw/{filename}`
2. 评估报告：
   - `tenants/{tenant_id}/reports/{evaluation_id}/report.json`

约束：key 必须可重复生成（仅依赖业务 ID），避免幂等冲突。

## 5. WORM 行为

1. `OBJECT_STORAGE_WORM_MODE=true` 时：
   - `put_object` 不允许覆盖既有对象。
   - `delete_object` 仅在 legal hold/retention 释放后允许。
2. `OBJECT_STORAGE_WORM_MODE=false` 时：
   - 允许覆盖（用于本地调试或回放）。
   - legal hold/retention 仍阻断删除。

## 6. legal hold 语义

1. `legal hold` 对象以 `storage_uri` 为粒度。
2. `impose` 后必须标记对象为 `hold=true`，并在 cleanup 删除时阻断。
3. `release` 必须双人复核，释放后才允许删除。

## 6.1 retention 语义

1. retention 为“时间窗保全”，在 `retain_until` 之前禁止删除。
2. retention 模式支持 `GOVERNANCE/COMPLIANCE`（由配置决定）。
3. retention 与 legal hold 可同时存在，删除需二者都解除。

## 7. API 行为补充

1. `POST /internal/legal-hold/impose`：
   - 如果对象已存在，标记 hold；否则仅记录 hold（待对象生成后补标）。
2. `POST /internal/storage/cleanup`：
   - 对有 hold 的对象返回 `409 LEGAL_HOLD_ACTIVE`。
   - 对有 retention 的对象返回 `409 RETENTION_ACTIVE`。
   - 成功删除后写入审计日志 `storage_cleanup_executed`。

## 8. 配置项

1. `BEA_OBJECT_STORAGE_BACKEND=local|s3`
2. `OBJECT_STORAGE_BUCKET`（默认 `bea`）
3. `OBJECT_STORAGE_ROOT`（local backend 使用）
4. `OBJECT_STORAGE_PREFIX`（可选）
5. `OBJECT_STORAGE_WORM_MODE`（默认 `true`）
6. `OBJECT_STORAGE_ENDPOINT`（s3 兼容）
7. `OBJECT_STORAGE_REGION`
8. `OBJECT_STORAGE_ACCESS_KEY`
9. `OBJECT_STORAGE_SECRET_KEY`
10. `OBJECT_STORAGE_FORCE_PATH_STYLE`（默认 `true`）
11. `OBJECT_STORAGE_RETENTION_DAYS`（默认 `0`，关闭）
12. `OBJECT_STORAGE_RETENTION_MODE`（默认 `GOVERNANCE`）

## 9. 验收标准

1. 上传文档后对象存储存在原始文件。
2. 评估报告生成后对象存储存在 report.json。
3. legal hold 生效后 cleanup 失败并返回 `LEGAL_HOLD_ACTIVE`。
4. retention 生效后 cleanup 失败并返回 `RETENTION_ACTIVE`。
5. legal hold 释放后 cleanup 删除成功并写审计日志。

## 10. 关联文档

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. `docs/design/2026-02-21-data-model-and-storage-spec.md`
3. `docs/design/2026-02-21-rest-api-specification.md`
4. `docs/design/2026-02-22-persistence-and-queue-production-spec.md`
