# 生产级实现准备包（方案 + 配置模板 + 验收清单）

> 日期：2026-02-23
> 目标：为“生产级真实实现”提供可直接执行的环境准备方案、配置模板、验收脚本与证据模板。
> 对齐：SSOT + 生产级规范（2026-02-22*）

## 1. 范围与前提

覆盖：
1. JWT/IdP 可信来源接入。
2. PostgreSQL/Redis 真栈与 RLS。
3. 向量库与缓存（Chroma/Milvus/Redis）。
4. 对象存储（S3/MinIO）+ WORM。
5. 监控/告警（Prometheus/Grafana/OpenTelemetry）。
6. 灰度/回滚/回放演练与证据归档。

前提：
1. 你提供真实环境的接入凭证或已有环境。
2. 你批准使用的云平台或部署形态（Docker Compose / K8s / 云托管）。

## 2. 生产级环境架构（ASCII）

```text
+------------------+     +------------------+
|  Users/Clients   | --> |  API Gateway     |
+------------------+     +--------+---------+
                                  |
                                  v
                           +------+-------+        +-----------------+
                           |  FastAPI API | <----> | JWT / IdP (JWKS) |
                           +------+-------+        +-----------------+
                                  |
                                  v
                           +------+-------+        +-----------------+
                           |  Redis Queue | <----> |  Worker Pool    |
                           +------+-------+        +-----------------+
                                  |
                                  v
+---------------+   +--------------------+   +-------------------------+
| ObjectStorage |<->| PostgreSQL (RLS)   |<->| Vector DB / Cache       |
| (S3/MinIO)    |   | jobs/audit/dlq/... |   | Chroma/Milvus/Redis     |
+---------------+   +--------------------+   +-------------------------+

+-----------------+     +--------------------------+
| Prometheus      |<----| OpenTelemetry Collector  |
+-----------------+     +--------------------------+
            |                       |
            v                       v
      +-----------+           +-----------+
      | Grafana   |           | Alerting  |
      +-----------+           +-----------+
```

## 3. 关键配置模板（生产）

### 3.1 `.env.production.template`

```bash
# --- Core ---
BEA_STORE_BACKEND=postgres
BEA_QUEUE_BACKEND=redis
BEA_REQUIRE_TRUESTACK=true
TRACE_ID_STRICT_REQUIRED=true

# --- JWT / IdP ---
JWT_ISSUER=https://your-idp.example.com/
JWT_AUDIENCE=your-audience
JWT_JWKS_URL=https://your-idp.example.com/.well-known/jwks.json
JWT_ALG=RS256

# --- PostgreSQL ---
POSTGRES_DSN=postgresql://user:pass@host:5432/bid_eval
POSTGRES_POOL_MIN=2
POSTGRES_POOL_MAX=10
POSTGRES_APPLY_RLS=true

# --- Redis ---
REDIS_DSN=redis://:pass@host:6379/0
REDIS_QUEUE_VISIBILITY_TIMEOUT_S=60

# --- Object Storage (S3/MinIO) ---
BEA_OBJECT_STORAGE_BACKEND=s3
OBJECT_STORAGE_ENDPOINT=https://s3.your-cloud.com
OBJECT_STORAGE_BUCKET=bea-prod
OBJECT_STORAGE_REGION=your-region
OBJECT_STORAGE_ACCESS_KEY=***
OBJECT_STORAGE_SECRET_KEY=***
OBJECT_STORAGE_FORCE_PATH_STYLE=false
OBJECT_STORAGE_WORM_MODE=GOVERNANCE
WORM_RETENTION_DAYS=30

# --- Vector DB ---
VECTOR_BACKEND=chroma
CHROMA_PERSIST_DIR=/data/chroma

# --- Observability ---
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OBS_ALERT_WEBHOOK=https://your-alert-webhook
OBS_METRICS_NAMESPACE=bea

# --- Worker ---
WORKER_CONCURRENCY=4
WORKER_MAX_RETRIES=3
WORKER_RETRY_BACKOFF_BASE_MS=1000
WORKER_RETRY_BACKOFF_MAX_MS=30000
```

说明：
1. 不在仓库中保存真实密钥。
2. `POSTGRES_APPLY_RLS=true` 需具备策略下发权限。

## 4. JWT/IdP 接入步骤

1. 获取 JWKS URL、issuer、audience。
2. 配置 `JWT_ISSUER/JWT_AUDIENCE/JWT_JWKS_URL`。
3. 启用接口层 JWT 校验（需后端改造，当前用 header 注入）。
4. 验收：
   - 伪造 token -> 401
   - issuer/aud mismatch -> 401
   - tenant_id 来自 token, 不能从 header 注入

## 5. PostgreSQL 真栈 + RLS

### 5.1 初始化

1. 启动 PostgreSQL 实例（托管或自建）。
2. 设置 `POSTGRES_DSN`。
3. 执行 RLS 下发脚本：

```bash
python3 scripts/apply_postgres_rls.py --dsn "$POSTGRES_DSN" --tables jobs,workflow_checkpoints,dlq_items,audit_logs,evaluation_reports,documents
```

### 5.2 验收

```bash
pytest -q tests/test_store_persistence_backend.py
```

证据：执行日志 + 通过输出。

## 6. Redis 真栈队列

1. 启动 Redis。
2. 设置 `REDIS_DSN`。
3. 验收：

```bash
pytest -q tests/test_queue_backend.py tests/test_internal_outbox_queue_api.py
```

## 7. 对象存储 WORM

1. S3/MinIO 配置 Object Lock。
2. 设置 `BEA_OBJECT_STORAGE_BACKEND=s3` 与相应密钥。
3. 验收：

```bash
pytest -q tests/test_object_storage_worm.py tests/test_legal_hold_api.py
```

证据：对象锁定与删除阻断日志。

## 8. 向量库与缓存

1. 选择 Chroma/Milvus。
2. 设置 `VECTOR_BACKEND`。
3. 验收：检索请求带 tenant_id/project_id 过滤。

## 9. 观测与告警

1. 部署 OpenTelemetry Collector + Prometheus + Grafana。
2. 配置 `OTEL_EXPORTER_OTLP_ENDPOINT`。
3. 执行 SLO 探针：

```bash
python3 scripts/run_slo_probe.py --url http://<api-host>/healthz --requests 100 --concurrency 10
```

4. 安全演练：

```bash
python3 scripts/security_compliance_drill.py --audit-json artifacts/audit_logs_release_window.json
```

## 10. 灰度与回滚

1. 灰度比例与回滚策略通过 runbook 走。
2. 回滚演练：

```bash
python3 scripts/rollback_to_sqlite.py --env .env.production
```

3. 回放验证：

```bash
pytest -q tests/test_gate_d_other_gates.py tests/test_gate_e_rollout_and_rollback.py tests/test_gate_f_ops_optimization.py
```

## 11. 端到端验收（真栈）

1. API 运行于真实 PG/Redis。
2. 前端 E2E（连接真实 API）：

```bash
cd frontend
VITE_API_BASE_URL=http://<api-host> npm run dev -- --host 0.0.0.0 --port 5173
E2E_API_BASE_URL=http://<api-host> npm run test:e2e
```

3. 完整证据记录（日志 + 截图 + 测试输出）。

## 12. 证据模板

建议保存到 `docs/ops/`：
1. `production-stack-evidence.md`
2. `jwt-idp-evidence.md`
3. `vector-cache-evidence.md`
4. `slo-load-evidence.md`
5. `rollback-replay-evidence.md`

每份模板至少包含：
1. 环境与配置摘要（去敏）。
2. 执行命令。
3. 输出或关键日志。
4. 结论与风险。

## 13. 下一步清单（你提供后我可执行）

1. 提供 JWT/IdP 信息（issuer/audience/JWKS）。
2. 提供 PostgreSQL/Redis/对象存储/向量库的 DSN 或访问方式。
3. 指定部署平台（Compose/K8s/云托管）。
4. 允许执行真实压测与演练。

