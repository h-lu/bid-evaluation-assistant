# 系统当前状态文档

> **编写日期**: 2026-02-25
> **SSOT 基线**: v2026.02.21-r3
> **当前分支**: feat/vector-indexing
> **目标读者**: 其他 Coding Agent

---

## 1. 快速概览

### 1.1 系统定位

AI 辅助评标专家系统，主链路：`上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`

### 1.2 SSOT 实现进度

```
上传 ──────► 解析建库 ──────► 向量索引 ──────► 检索评分 ──────► HITL ──────► 报告归档
 ✅            ✅               ✅               ⚠️              ✅             ✅
```

- ✅ 完成
- ⚠️ 部分完成（详见下文）
- ❌ 未完成

---

## 2. 已完成的工作

### 2.1 上传流程

**状态**: 完成

| 组件 | 文件 | 说明 |
|------|------|------|
| 上传端点 | `app/routes/documents.py` | `POST /documents/upload`，返回 202 + job_id |
| 存储逻辑 | `app/store_ops.py` | `create_upload_job()` |
| 文档仓库 | `app/repositories/documents.py` | InMemory + Postgres 双后端 |
| 对象存储 | `app/object_storage.py` | Local + S3 后端，支持 WORM |
| 去重机制 | `app/store_admin.py` | SHA256 文件哈希去重 |

**关键特性**:
- Idempotency-Key 幂等
- 租户隔离
- SHA256 去重

### 2.2 解析建库流程

**状态**: 完成

| 组件 | 文件 | 说明 |
|------|------|------|
| 解析端点 | `app/routes/documents.py` | `POST /documents/{document_id}/parse` |
| 解析器适配 | `app/parser_adapters.py` | MinerU Official, Docling, OCR, Local |
| 解析服务 | `app/mineru_parse_service.py` | 完整的解析服务 |
| 分块逻辑 | `app/document_parser.py` | PyMuPDF, python-docx, 纯文本 |
| 持久化 | `app/store_parse.py` | chunks, parse_manifest 持久化 |

**关键特性**:
- Fallback 链: mineru -> docling -> ocr（最多 3 次尝试）
- Parse manifest 持久化
- Chunk 标准化（bbox, page, heading_path）
- SSOT §8 持久化顺序已修复

### 2.3 向量索引

**状态**: 完成（但不是真正的 LightRAG）

| 组件 | 文件 | 说明 |
|------|------|------|
| 索引服务 | `app/lightrag_service.py` | ChromaDB 后端 |
| 索引逻辑 | `app/store_retrieval.py` | `_maybe_index_chunks_to_lightrag()` |
| Embedding | `app/lightrag_service.py` | OpenAI/sentence-transformers/Simple |

**关键特性**:
- 多种 Embedding 后端
- 租户/项目/供应商隔离
- 本地和远程 LightRAG DSN 支持

**⚠️ 重要差距**: 当前 `lightrag_service.py` 只是 ChromaDB 的简单包装，不是真正的 LightRAG。详见 §4.1。

### 2.4 检索功能

**状态**: 部分完成

| 组件 | 文件 | 说明 |
|------|------|------|
| 检索端点 | `app/routes/retrieval.py` | `POST /retrieval/query` |
| 检索逻辑 | `app/store_retrieval.py` | `retrieval_query()` |
| Reranker | `app/reranker.py` | Cross-encoder 重排序 |
| 约束抽取 | `app/constraint_extractor.py` | 实体/数值/时间约束抽取 |

**已实现**:
- 基础向量检索
- Rerank 重排序
- 元数据过滤（tenant_id, project_id, supplier_id）
- Rerank 降级处理

**未实现**（需要真正的 LightRAG）:
- local/global/hybrid/mix 检索模式
- 实体检索 + 邻居
- 社区摘要检索
- `max_entity_tokens`, `max_relation_tokens` 参数

### 2.5 评分流程

**状态**: 完成

| 组件 | 文件 | 说明 |
|------|------|------|
| 评分端点 | `app/routes/evaluations.py` | `POST /evaluations` |
| 评分节点 | `app/evaluation_nodes.py` | 完整的节点链 |
| 评分逻辑 | `app/store_eval.py` | `StoreEvalMixin` |
| 规则引擎 | `app/repositories/rule_packs.py` | 规则包管理 |

**评分节点链**:
```
node_load_context
 -> node_retrieve_evidence
 -> node_evaluate_rules
 -> node_score_with_llm
 -> node_quality_gate
 -> node_finalize_report
 -> node_persist_result
```

### 2.6 HITL（人工复核）

**状态**: 完成

| 组件 | 文件 | 说明 |
|------|------|------|
| Resume Token | `app/store_workflow.py` | 注册、验证、消费 |
| HITL 触发 | `app/evaluation_nodes.py` | `node_quality_gate()` |
| Resume 端点 | `app/routes/evaluations.py` | `POST /evaluations/{evaluation_id}/resume` |

**HITL 触发条件**（SSOT §5.2）:
- `score_confidence < 0.65`
- `citation_coverage < 0.90`
- `score_deviation_pct > 20%`
- `redline_conflict`
- `force_hitl` 标志

### 2.7 报告归档

**状态**: 完成

| 组件 | 文件 | 说明 |
|------|------|------|
| 报告端点 | `app/routes/evaluations.py` | `GET /evaluations/{evaluation_id}/report` |
| 报告持久化 | `app/store.py` | `_persist_evaluation_report()` |
| 对象存储归档 | `app/store.py` | `_archive_report_to_object_storage()` |
| 报告仓库 | `app/repositories/evaluation_reports.py` | InMemory + Postgres |

**关键特性**:
- 报告归档到对象存储
- WORM 模式支持
- Legal hold 支持
- Citation 解析

---

## 3. 数据模型

### 3.1 仓库层

所有仓库都有 InMemory 和 Postgres 两种实现：

| 仓库 | 文件 | 说明 |
|------|------|------|
| Jobs | `app/repositories/jobs.py` | 任务管理 |
| Documents | `app/repositories/documents.py` | 文档管理 |
| Chunks | `app/repositories/documents.py` | 分块管理 |
| Parse Manifests | `app/repositories/parse_manifests.py` | 解析记录 |
| Evaluation Reports | `app/repositories/evaluation_reports.py` | 评分报告 |
| Projects | `app/repositories/projects.py` | 项目管理 |
| Suppliers | `app/repositories/suppliers.py` | 供应商管理 |
| Rule Packs | `app/repositories/rule_packs.py` | 规则包 |
| Audit Logs | `app/repositories/audit_logs.py` | 审计日志 |
| DLQ Items | `app/repositories/dlq_items.py` | 死信队列 |
| Workflow Checkpoints | `app/repositories/workflow_checkpoints.py` | 工作流检查点 |

### 3.2 数据库表

PostgreSQL 表结构在 `app/store_backends.py` 中创建：

```
jobs, documents, document_chunks, projects, suppliers, rule_packs,
evaluation_reports, parse_manifests, audit_logs, dlq_items, workflow_checkpoints
```

---

## 4. 关键差距与待办事项

### 4.1 LightRAG 集成（高优先级）

**现状**: `app/lightrag_service.py` 只是 ChromaDB 的简单包装

**SSOT 要求**（`retrieval-and-scoring-spec.md` §4）:

| 功能 | 真正的 LightRAG | 当前实现 |
|------|----------------|----------|
| 向量检索 | ✅ | ✅ |
| 实体抽取 | ✅ Knowledge Graph | ❌ |
| 关系抽取 | ✅ 三元组 | ❌ |
| local 模式 | ✅ 实体+邻居 | ❌ |
| global 模式 | ✅ 社区摘要 | ❌ |
| hybrid 模式 | ✅ local+global | ❌ |
| mix 模式 | ✅ 综合检索 | ❌ |
| 图数据库 | ✅ Neo4j/NetworkX | ❌ |

**待办**:
1. 集成真正的 [LightRAG](https://github.com/HKUDS/LightRAG) 库
2. 或重命名当前服务为 `chroma-service`

### 4.2 SQL 白名单支路（中优先级）

**SSOT 要求**（`retrieval-and-scoring-spec.md` §5.3）:

结构化字段检索应支持：
- `supplier_code`
- `qualification_level`
- `registered_capital`
- `bid_price`
- `delivery_period`
- `warranty_period`

**现状**: `app/sql_whitelist.py` 已实现，但未完全集成到检索流程

### 4.3 Embedding 配置（中优先级）

**现状**: 默认使用 `SimpleEmbeddingFunction`（SHA256 哈希）

**问题**: 不适合生产环境，语义相似度不准确

**待办**:
- 配置 `EMBEDDING_BACKEND=openai` 或 `sentence-transformers`
- 或部署本地 Ollama embedding

### 4.4 测试覆盖率

**现状**: 84 个测试文件

**待补充**:
- 真正的 LightRAG 集成测试
- 多租户隔离边界测试
- 性能压测

---

## 5. 环境配置

### 5.1 关键环境变量

```bash
# 存储后端
BEA_STORE_BACKEND=postgres          # 或 memory
POSTGRES_DSN=postgresql://bea:bea_pass@postgres:5432/bea

# 队列后端
BEA_QUEUE_BACKEND=redis             # 或 memory
REDIS_DSN=redis://redis:6379/0

# LightRAG
LIGHTRAG_DSN=http://lightrag:8081   # 或留空使用本地
LIGHTRAG_INDEX_PREFIX=lightrag

# Embedding
EMBEDDING_BACKEND=auto              # auto/openai/ollama/sentence-transformers/simple
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-xxx               # 如使用 OpenAI

# 对象存储
BEA_OBJECT_STORAGE_BACKEND=s3       # 或 local
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=bea

# JWT 认证
JWT_ISSUER=http://jwks:8000
JWT_AUDIENCE=bea-api
JWKS_URL=http://jwks:8000/jwks.json
```

### 5.2 Docker Compose 服务

```yaml
# docker-compose.production.yml
services:
  postgres:    # PostgreSQL 16
  redis:       # Redis 7
  minio:       # S3 兼容对象存储
  lightrag:    # 向量检索服务
  api:         # FastAPI
  worker:      # 后台任务
  frontend:    # Vue3
  jwks:        # JWT 密钥服务
  prometheus:  # 指标
  grafana:     # 仪表板
```

---

## 6. 验证命令

### 6.1 检查文档状态

```bash
docker exec -i bid-evaluation-assistant-postgres-1 psql -U bea -d bea \
  -c "SELECT document_id, filename, status FROM documents LIMIT 5;"
```

### 6.2 检查向量索引

```bash
docker exec -i bid-evaluation-assistant-lightrag-1 curl -s -X POST \
  localhost:8081/query \
  -H "Content-Type: application/json" \
  -d '{"query":"test","index_name":"lightrag_test_tenant_default","top_k":1,"filters":{"tenant_id":"test_tenant","project_id":"default","supplier_id":""}}'
```

### 6.3 运行测试

```bash
python3 -m pytest tests/ -v --tb=short
```

### 6.4 检查 Git 状态

```bash
git status
git log --oneline -10
```

---

## 7. 下一步工作建议

### 7.1 短期（本周）

1. **集成真正的 LightRAG**
   - 安装 `lightrag-hku` 包
   - 实现实体抽取和图谱构建
   - 实现 local/global/hybrid/mix 模式

2. **配置生产级 Embedding**
   - 部署 Ollama 或配置 OpenAI API
   - 更新环境变量

### 7.2 中期（本月）

1. **完善 SQL 白名单支路**
2. **增加测试覆盖率**
3. **性能优化**

### 7.3 长期

1. **Neo4j 图数据库集成**（如需要）
2. **GraphRAG 增强**（SSOT 明确不在 MVP）

---

## 8. 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| SSOT 主文档 | `docs/plans/2026-02-21-end-to-end-unified-design.md` | 端到端统一方案 |
| MinerU 规范 | `docs/design/2026-02-21-mineru-ingestion-spec.md` | 解析入库规范 |
| 检索评分规范 | `docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 检索与评分 |
| REST API 规范 | `docs/design/2026-02-21-rest-api-specification.md` | API 契约 |
| 数据模型 | `docs/design/2026-02-21-data-model-and-storage-spec.md` | 存储规范 |
| LangGraph 规范 | `docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 工作流规范 |

---

## 9. 联系与协作

- **代码仓库**: `https://github.com/h-lu/bid-evaluation-assistant`
- **当前分支**: `feat/vector-indexing`
- **主分支**: `main`

如有问题，请先阅读 `CLAUDE.md` 中的项目上下文和工程约束。
