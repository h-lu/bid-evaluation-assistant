# 辅助评标专家系统（Bid Evaluation Assistant）

> 文档基线：v2026.02.21-r3  
> 状态：Active  
> 仓库类型：设计与实施规范仓库（当前不含业务代码）

## 1. 这套文档解决什么问题

本仓库给出一套可直接执行的端到端方案，用于实现“AI 辅助评标 + 专家终审裁量”系统。

核心目标：

1. 打通 `上传 -> 解析 -> 检索 -> 评分 -> 人审 -> 报告归档` 主链路。
2. 全链路可追溯：所有结论可回跳到原文 `chunk_id/page/bbox`。
3. 真正多租户隔离：API、数据库、向量索引、缓存、队列统一隔离。
4. 失败可恢复：`interrupt/resume` 与 `DLQ` 子流程具备可操作规范。

## 2. 一页架构（ASCII）

```text
+--------------------+        +----------------------+        +----------------------+
| 评标专家/业务人员    | -----> | Frontend (Vue3)      | -----> | FastAPI API           |
+--------------------+        +----------------------+        +----------+-----------+
                                                                     |
                                                                     | enqueue
                                                                     v
                                                            +--------+--------+
                                                            | Redis Queue      |
                                                            +--------+--------+
                                                                     |
                                                                     v
                                                            +--------+--------+
                                                            | Worker Pool      |
                                                            +--+----------+---+
                                                               |          |
                                                     parse/index|          |evaluate
                                                               v          v
                                             +----------------------+  +----------------------+
                                             | MinerU/Docling Router |  | LangGraph Workflow  |
                                             +----------+-----------+  +----------+-----------+
                                                        |                         |
                                                        +------------+------------+
                                                                     |
                                                                     v
                                     +--------------------------------------------------------------+
                                     | PostgreSQL (truth + audit + checkpoint + dlq + outbox)      |
                                     | Chroma/LightRAG (retrieval index)                            |
                                     | Redis (cache + idempotency)                                  |
                                     | Object Storage (WORM evidence/report)                        |
                                     +--------------------------------------------------------------+
```

## 3. 强约束（必须遵守）

1. 不允许全自动终审发布。
2. 长任务统一异步：写接口返回 `202 + job_id`。
3. `failed` 状态必须在 DLQ 入列之后。
4. 评分输出必须携带引用证据；无证据不得形成最终结论。
5. 高风险动作（终审发布、DLQ 丢弃、legal hold 解除）必须双人复核。
6. 前端不得在 `localStorage/sessionStorage` 存高敏 token。

## 4. 文档地图（按阅读顺序）

`SSOT（先读）`

- `docs/plans/2026-02-21-end-to-end-unified-design.md`

`核心实施规范`

1. `docs/design/2026-02-21-implementation-plan.md`
2. `docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md`
3. `docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md`
4. `docs/design/2026-02-21-legacy-detail-triage.md`
5. `docs/design/2026-02-21-mineru-ingestion-spec.md`
6. `docs/design/2026-02-21-retrieval-and-scoring-spec.md`
7. `docs/design/2026-02-21-langgraph-agent-workflow-spec.md`
8. `docs/design/2026-02-21-rest-api-specification.md`
9. `docs/design/2026-02-21-openapi-v1.yaml`
10. `docs/design/2026-02-21-api-contract-test-samples.md`
11. `docs/design/2026-02-21-job-system-and-retry-spec.md`
12. `docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md`
13. `docs/design/2026-02-21-data-model-and-storage-spec.md`
14. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`
15. `docs/design/2026-02-21-security-design.md`
16. `docs/design/2026-02-21-frontend-interaction-spec.md`
17. `docs/design/2026-02-21-testing-strategy.md`
18. `docs/design/2026-02-21-deployment-config.md`

`Agent 开发治理`

- `docs/design/2026-02-21-agent-development-lifecycle.md`
- `docs/design/2026-02-21-agent-tool-governance.md`
- `docs/design/2026-02-21-agent-evals-observability.md`
- `docs/datasets/eval-dataset-governance.md`
- `docs/ops/agent-change-management.md`
- `docs/ops/agent-incident-runbook.md`

`Agent 协作入口（仓库根目录）`

- `AGENTS.md`（通用 Agent 执行规范）
- `CLAUDE.md`（Claude Code 项目记忆与执行约束）

## 5. 外部项目参考策略（已固化）

直接采用：

1. MinerU：复杂 PDF 解析主路径。
2. Docling：Office/HTML/常规 PDF 解析补充路径。
3. LightRAG：检索模式与图增强检索能力。
4. LangGraph：状态机、checkpoint、interrupt/resume。

借鉴但不直接依赖：

1. RAGFlow：解析器注册表、工程化分块与位置追踪思路。
2. Agentic-Procure-Audit-AI：RGSG 工作流拆解思想与可解释评分组织方式。
3. ProposalLLM：点对点应答表结构。
4. kotaemon：引用回跳与 PDF 高亮交互模式。

当前不进入 MVP：

1. Neo4j / Milvus 主栈。
2. RAPTOR / GraphRAG 直接上线。
3. 完整微服务拆分。

## 6. 开发推进方式（Agent-first）

不按“周计划”推进，按 Gate + 证据推进：

```text
Gate A 设计冻结
 -> Gate B 契约与骨架
 -> Gate C 主链路打通
 -> Gate D 四门禁强化（质量/性能/安全/成本）
 -> Gate E 灰度与回滚
 -> Gate F 运行优化
```

每个 Gate 都必须有可复核证据：测试报告、评估报告、压测报告、安全检查、回滚演练记录。

## 7. 版本管理要求

1. SSOT 变更优先级最高，其他文档必须与 SSOT 对齐。
2. 任何新增实现细节，必须同步落到对应专项文档，不允许只写在临时说明。
3. 合并前必须跑一次全量一致性检查：术语、状态机、错误码、接口字段、门禁阈值。

## 8. 最小 API 骨架（Gate C 分支）

`codex/gate-c-api-skeleton` 分支包含最小可运行 FastAPI 骨架，用于承接 Gate B 契约并推进 Gate C。

本地运行：

```bash
python3 -m pip install -e '.[dev]'
pytest -v
uvicorn app.main:app --reload
```

当前已覆盖最小接口：

1. `POST /api/v1/documents/upload`
2. `POST /api/v1/evaluations`
3. `GET /api/v1/jobs/{job_id}`
4. `POST /api/v1/evaluations/{evaluation_id}/resume`
5. `GET /api/v1/citations/{chunk_id}/source`
