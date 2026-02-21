# 数据模型与存储规范

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 固化权威数据与索引数据边界。
2. 固化多租户强隔离（字段、索引、RLS）。
3. 固化工作流恢复、DLQ、审计、留存模型。
4. 支持可追溯与可回滚运维。

## 2. 存储职责

| 存储 | 职责 | 非职责 |
| --- | --- | --- |
| PostgreSQL | 业务真值、状态、审计、checkpoint、DLQ | 向量相似度检索 |
| Chroma/LightRAG | 向量检索与召回索引 | 业务权威状态 |
| Redis | 队列、幂等键、短时缓存、分布式锁 | 永久业务记录 |
| Object Storage(WORM) | 原始文件、解析产物、报告归档 | 在线事务查询 |

原则：业务真值只认 PostgreSQL。

## 3. 核心 ER（ASCII）

```text
tenants
  |-- users
  |-- projects --< project_suppliers >-- suppliers
  |-- documents --< document_parse_runs --< document_chunks --< chunk_positions
  |-- evaluation_sessions --< evaluation_items --< evaluation_results --< citations
  |-- jobs --< dlq_items
  |-- workflow_checkpoints
  |-- audit_logs
  |-- domain_events_outbox
  |-- legal_hold_objects
```

## 4. 主表定义（逻辑字段）

### 4.1 基础域

1. `tenants(tenant_id, tenant_code, name, status, created_at)`
2. `users(user_id, tenant_id, email, role, is_active, created_at)`
3. `projects(project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at)`
4. `suppliers(supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json)`
5. `project_suppliers(tenant_id, project_id, supplier_id, join_status, created_at)`

### 4.2 文档域

1. `documents(document_id, tenant_id, project_id, supplier_id, doc_type, filename, sha256, storage_uri, parse_status, created_at)`
2. `document_parse_runs(run_id, tenant_id, document_id, parser, parser_version, manifest_uri, status, error_code, started_at, ended_at)`
3. `document_chunks(chunk_id, tenant_id, project_id, document_id, supplier_id, chunk_index, content, chunk_type, section, heading_path_json, token_count, created_at)`
4. `chunk_positions(position_id, tenant_id, chunk_id, page_no, x0, y0, x1, y1, text_start, text_end)`

### 4.3 评估域

1. `evaluation_sessions(evaluation_id, tenant_id, project_id, supplier_id, status, total_score, confidence, risk_level, report_uri, created_by, created_at, updated_at)`
2. `evaluation_items(item_id, tenant_id, evaluation_id, criteria_id, hard_pass, score, max_score, reason, confidence)`
3. `evaluation_results(result_id, tenant_id, evaluation_id, score_json, summary, needs_human_review, approved_by, approved_at)`
4. `citations(citation_id, tenant_id, evaluation_id, item_id, chunk_id, page_no, bbox_json, quote, created_at)`

### 4.4 任务与恢复域

1. `jobs(job_id, tenant_id, job_type, resource_type, resource_id, status, retry_count, trace_id, idempotency_key, payload_json, error_code, created_at, updated_at)`
2. `workflow_checkpoints(checkpoint_id, tenant_id, thread_id, evaluation_id, state_json, status, created_at, updated_at)`
3. `dlq_items(dlq_id, tenant_id, job_id, error_class, error_code, payload_json, context_json, status, first_failed_at, created_at, updated_at)`

### 4.5 治理域

1. `audit_logs(audit_id, tenant_id, actor_id, actor_role, action, resource_type, resource_id, request_id, trace_id, reason, ip, user_agent, payload_json, created_at)`
2. `domain_events_outbox(event_id, tenant_id, event_type, aggregate_type, aggregate_id, payload_json, status, published_at, created_at)`
3. `legal_hold_objects(hold_id, tenant_id, object_type, object_id, reason, imposed_by, imposed_at, released_by, released_at, status)`

## 5. 索引与唯一约束

### 5.1 必备索引

1. `documents(tenant_id, project_id, supplier_id, created_at DESC)`
2. `document_chunks(tenant_id, document_id, chunk_index)`
3. `chunk_positions(tenant_id, chunk_id, page_no)`
4. `evaluation_sessions(tenant_id, project_id, status, created_at DESC)`
5. `jobs(tenant_id, status, created_at DESC)`
6. `dlq_items(tenant_id, status, created_at DESC)`
7. `workflow_checkpoints(tenant_id, thread_id, updated_at DESC)`
8. `audit_logs(tenant_id, action, created_at DESC)`

### 5.2 唯一约束

1. `projects(tenant_id, project_code)`
2. `suppliers(tenant_id, supplier_code)`
3. `project_suppliers(tenant_id, project_id, supplier_id)`
4. `jobs(tenant_id, idempotency_key)`（可空，空值不参与）

## 6. 多租户隔离（RLS）

### 6.1 策略要求

1. 核心业务表全部启用 RLS。
2. 连接会话必须先设置 `app.current_tenant`。
3. 无 tenant 上下文时拒绝查询。

### 6.2 策略模板

```text
USING (tenant_id = current_setting('app.current_tenant', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid)
```

## 7. 向量与缓存约束

### 7.1 向量 metadata 最小字段

1. `tenant_id`
2. `project_id`
3. `document_id`
4. `supplier_id`
5. `chunk_id`
6. `chunk_type`
7. `page_span`

### 7.2 Redis key 规范

```text
bea:{tenant_id}:job:{job_id}
bea:{tenant_id}:idem:{idempotency_key}
bea:{tenant_id}:lock:{resource_key}
bea:{tenant_id}:cache:{namespace}:{hash}
```

## 8. 留存、分区与备份

1. `audit_logs` 超大表按月分区。
2. 报告与原始证据进入 WORM 存储。
3. 常规对象 180 天留存，可按租户策略调整。
4. legal hold 对象不参与自动清理。
5. 每日增量 + 每周全量备份。

## 9. 演进策略

1. 新字段优先向后兼容，避免破坏性变更。
2. 迁移采用“双写+回填+切换”流程。
3. schema 变更必须附回滚 SQL。

## 10. 验收标准

1. 跨租户访问在 API 与 DB 层均被阻断。
2. 关键查询索引命中率达到目标。
3. checkpoint 恢复可定位到最新状态。
4. 审计与 legal hold 数据可完整追溯。

## 11. 参考来源（核验：2026-02-21）

1. PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
2. 历史融合提交：`beef3e9`, `7f05f7e`
