# 会话交接文档（Session Handoff）

> 日期：2026-02-24（更新）
> 基线：`v2026.02.21-r3`
> 分支：`feat/t7-t8-t9-quality-security-perf`
> 前序文档：`docs/status/2026-02-23-project-status-and-roadmap.md`

---

## 1. 本次会话完成的工作

### 1.1 全部任务完成状态

T1-T9 全部完成，从 Mock 到真实实现的端到端贯通。

| 任务 | 内容 | 完成度 | 核心文件 |
|------|------|--------|---------|
| T1 | Rerank 真实实现 | 100% | `app/reranker.py` (191行，TF-IDF + cross-encoder + 超时降级) |
| T2 | Token Budget 控制 | 100% | `app/token_budget.py` (157行，tiktoken + 冗余来源去重) |
| T3 | LangGraph 真实图 | 100% | `app/langgraph_runtime.py` (403行，7节点 StateGraph + interrupt) |
| T4 | 约束抽取器 | 100% | `app/constraint_extractor.py` (209行，5类约束 + 中文单位 + 近X年) |
| T5 | store.py 拆分 | 100% | `app/store.py` (449行核心) + 8 个 mixin |
| T6 | main.py 拆分 | 100% | `app/main.py` (231行核心) + 5 个路由模块 |
| T7 | RAGAS 评估 | 100% | `app/ragas_evaluator.py` (505行，ragas+deepeval 双后端) |
| T8 | 性能基准 | 100% | `app/performance_benchmark.py` (121行，P50/P95/P99) |
| T9 | 安全回归 | 100% | `tests/test_security_regression.py` (多维度安全测试套件) |

### 1.2 模块架构现状

#### store 模块（T5 拆分后）

| 文件 | 行数 | 职责 |
|------|------|------|
| `app/store.py` | 449 | 核心协调 + mixin 继承 |
| `app/store_parse.py` | 314 | 解析相关方法 |
| `app/store_eval.py` | 419 | 评估相关方法 |
| `app/store_retrieval.py` | 461 | 检索 + rerank + token budget |
| `app/store_release.py` | 535 | 发布管理 |
| `app/store_admin.py` | 834 | 管理操作 |
| `app/store_workflow.py` | 422 | 工作流编排 |
| `app/store_ops.py` | 537 | 运维指标 |
| `app/store_backends.py` | 1652 | Sqlite/Postgres 持久化实现 |

#### routes 模块（T6 拆分后）

| 文件 | 行数 | 职责 |
|------|------|------|
| `app/main.py` | 231 | 核心 (middleware + exception handlers + health) |
| `app/routes/documents.py` | 176 | 文档上传/解析/查看 |
| `app/routes/evaluations.py` | 152 | 评估/恢复/报告 |
| `app/routes/retrieval.py` | 63 | 检索/预览/引用 |
| `app/routes/admin.py` | 461 | 项目/供应商/规则/作业/DLQ |
| `app/routes/internal.py` | 959 | 内部调试接口 |
| `app/routes/_deps.py` | 147 | 共享依赖 (trace_id, audit, approval) |

### 1.3 关键集成点

#### 解析 -> 索引流程

```text
upload(file_bytes)
  -> create_upload_job (存储到 object_storage)
  -> create_parse_job
  -> run_job_once
    -> _parse_document_file
      -> LocalParserAdapter.parse_file -> document_parser.parse_file_bytes
    -> _persist_document_chunks
    -> register_citation_source (每个 chunk)
    -> _maybe_index_chunks_to_lightrag
      -> 有 LIGHTRAG_DSN: HTTP 调用外部服务
      -> 无 LIGHTRAG_DSN: 直接调用 lightrag_service.index_chunks_to_collection (Chroma)
```

#### 检索 -> 评分流程

```text
create_evaluation_job
  -> _retrieve_evidence_for_criteria (每个评分项)
    -> 优先: _query_lightrag -> Chroma 向量检索
    -> rerank: TF-IDF (默认) / cross-encoder (可选，含超时降级)
    -> token_budget: 冗余来源去重 -> 低相关裁剪 -> 预算控制
    -> 降级: mock_retrieve_evidence / stub 证据
  -> llm_score_criteria (每个评分项)
    -> 优先: 真实 LLM (primary model)
    -> 降级1: fallback model
    -> 降级2: mock_score_criteria
  -> node_quality_gate: 动态 model_stability + HITL 判定
  -> node_finalize_report: 合并 edited_scores (如有 HITL)
  -> 生成 evaluation_report
```

#### LangGraph 工作流

```text
StateGraph (7 nodes):
  load_context -> retrieve_evidence -> score_criteria
    -> quality_gate -> [pass] -> finalize_report -> persist
                    -> [hitl] -> interrupt -> resume -> finalize_report -> persist
```

### 1.4 测试状态

```
总测试数: 459
通过率:   100%
失败数:   0
Lint:     0 errors (ruff)
```

---

## 2. 当前环境变量配置体系

### 2.1 LLM 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` | `openai` / `ollama` / `custom` |
| `LLM_MODEL` | `gpt-4o-mini` | 主模型 |
| `LLM_FALLBACK_MODEL` | (空) | 备用模型（降级用） |
| `LLM_TEMPERATURE` | `0.1` | 温度参数 |
| `OPENAI_API_KEY` | (空) | API 密钥（Ollama 不需要） |
| `OPENAI_BASE_URL` | (空) | 自定义 API 端点 |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 端点 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama 默认模型 |
| `MOCK_LLM_ENABLED` | `true` | 强制使用 Mock |

### 2.2 Embedding 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_BACKEND` | `auto` | `auto` / `simple` / `openai` / `ollama` / `sentence-transformers` |
| `EMBEDDING_MODEL_NAME` | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_BASE_URL` | (空) | 自定义 Embedding 端点 |
| `EMBEDDING_DIM` | `128` | Simple 模式维度 |

auto 降级链：sentence-transformers -> OpenAI (需 API key) -> simple (带警告)

### 2.3 Rerank 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RERANK_BACKEND` | `simple` | `simple` (TF-IDF) / `cross-encoder` / `cohere` / `jina` |
| `RERANK_MODEL_NAME` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder 模型 |
| `RERANK_TOP_K` | `0` | 重排后截取数（0=不截取） |
| `RERANK_TIMEOUT_MS` | `2000` | Cross-encoder 超时（ms），超时降级到 TF-IDF |

### 2.4 Chroma / 检索配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LIGHTRAG_DSN` | (空) | 外部 LightRAG HTTP 端点（空则使用内建 Chroma） |
| `CHROMA_PERSIST_DIR` | (空) | Chroma 持久化目录（空则内存模式） |
| `CHROMA_HOST` | (空) | Chroma 远程 host |
| `LIGHTRAG_INDEX_PREFIX` | `lightrag` | 索引名称前缀 |

### 2.5 Token Budget 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EVIDENCE_SINGLE_BUDGET` | `6000` | 单项评分 token 上限 |
| `EVIDENCE_TOTAL_BUDGET` | `24000` | 全报告 token 上限 |

---

## 3. SSOT 对齐状态

### 3.1 已对齐项

| SSOT 章节 | 要求 | 状态 |
|-----------|------|------|
| §6.1 | chunk 元数据: page/bbox/heading_path/chunk_type | 已对齐 |
| §6.2 | 检索模式 local/global/hybrid/mix | 已对齐 |
| §6.2 | 规则引擎硬判定 + LLM 软评分 | 已对齐 |
| §6.2 | 查询约束保持改写 (5类约束) | 已对齐 |
| §6.3 | 工作流 LangGraph interrupt/resume | 已对齐 |
| §6.5 | 向量查询强制 tenant_id+project_id 过滤 | 已对齐 |
| §7.1 | 性能基准 P95 阈值 | 已对齐（T8 框架） |
| §7.2 | RAGAS precision/recall/faithfulness + DeepEval 幻觉率 | 已对齐（T7 双后端） |
| §7.3 | 跨租户=0, 审计=100%, legal hold 违规=0 | 已对齐（T9 回归测试） |
| §7.4 | 模型降级策略 | 已对齐（三级降级链） |
| §8.1 | 评分项输出: criteria_id/score/max_score/hard_pass/reason/citations/confidence | 已对齐 |
| §8.2 | 总分公式: sum(score * weight) | 已对齐 |
| §8.3 | 置信度: 0.4*evidence + 0.3*agreement + 0.3*stability (动态) | 已对齐 |
| §9 | HITL 触发条件（5 项）+ edited_scores 合并 | 已对齐 |
| §10 | claim->citation 映射检查 | 已对齐 |
| retrieval spec §6.1 | rerank: score_raw + score_rerank (TF-IDF + cross-encoder) | 已对齐 |
| retrieval spec §6.3 | token budget: 单项 <=6k, 全报告 <=24k, 冗余来源去重 | 已对齐 |
| retrieval spec §3.2 | 约束抽取: entity/numeric/time/must_include/must_exclude | 已对齐 |

### 3.2 剩余偏差

| SSOT 章节 | 要求 | 偏差 | 优先级 |
|-----------|------|------|--------|
| §6.2 (retrieval spec §5.3) | SQL 白名单支路 | 未真实实现 | P2 |
| §7.4 | 成本 P95 不超基线 1.2x | 有 token 追踪，无预算阻断 | P2 |

---

## 4. 后续任务（供 Agent 继续）

### 4.1 P2 — 剩余偏差修复

#### T11: SQL 白名单支路

```
目标: 实现检索时的 SQL 白名单查询支路
SSOT: §6.2 "SQL 支路只允许白名单字段，禁止自由 SQL"
方案:
  1. 定义白名单字段集合（tenant_id, project_id, supplier_id, doc_type, etc.）
  2. 验证传入 SQL/filter 条件仅含白名单字段
  3. 拒绝非白名单查询并记录审计日志
文件: app/store_retrieval.py, app/lightrag_service.py
验收: 白名单外字段查询被拒; 白名单内查询正常返回
```

#### T12: 成本预算阻断

```
目标: 单任务成本超基线 1.2x 时阻断或降级
SSOT: §7.4 "单任务成本 P95 不高于基线 1.2x"
方案:
  1. 在 llm_provider 累计 token 成本
  2. 超过阈值时触发模型降级（primary -> fallback -> mock）
  3. 超过硬上限时中断评估并标记 cost_exceeded
文件: app/llm_provider.py, app/evaluation_nodes.py
验收: 超基线任务自动降级; 成本追踪可查询
```

### 4.2 P3 — 前端

#### T10: 前端 E2E

```
目标: 前端关键流程自动化测试
覆盖: 上传 -> 评估 -> HITL -> 报告查看 -> DLQ 操作
```

### 4.3 Gate D — 四门禁证据报告

```
目标: 收集 Gate D 所需的四门禁通过证据
内容:
  D-1 质量: RAGAS 评估结果 (precision/recall >= 0.80, faithfulness >= 0.90)
  D-2 性能: API/检索/评估/解析 P95 基准数据
  D-3 安全: 安全回归测试 100% 通过
  D-4 成本: 单任务成本 P95 <= 1.2x 基线
输出: docs/reports/gate-d-evidence.md
```

---

## 5. 技术债务

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| `app/store_backends.py` 1652 行 | 中 | Sqlite/Postgres 后端，可考虑进一步拆分 |
| `app/routes/internal.py` 959 行 | 低 | 内部调试接口，功能密集但低风险 |
| Cohere/Jina rerank API | 低 | placeholder，降级到 TF-IDF |
| HttpParserAdapter 默认 stub | 低 | 外部解析服务端点未配置时为 stub |

---

## 6. 快速启动命令

```bash
# 安装依赖
python3 -m pip install -e '.[dev]'

# 运行全量测试（应显示 459 passed）
python3 -m pytest -q

# 运行安全回归测试
python3 -m pytest tests/test_security_regression.py -v

# 运行 RAGAS 评估（lightweight 模式，无需 API key）
python3 scripts/eval_ragas.py --backend lightweight --dataset samples/eval_dataset.json

# 运行性能基准
python3 scripts/benchmark_performance.py

# 代码检查
ruff check app/

# 启动 API 服务（Mock 模式）
MOCK_LLM_ENABLED=true uvicorn app.main:create_app --factory --reload

# 启动 API 服务（Ollama 本地模型）
MOCK_LLM_ENABLED=false LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b \
  EMBEDDING_BACKEND=ollama EMBEDDING_MODEL_NAME=nomic-embed-text \
  uvicorn app.main:create_app --factory --reload
```

---

## 7. 关键文件索引

### 核心业务

| 文件 | 说明 |
|------|------|
| `app/store.py` + `app/store_*.py` | 存储层（核心 + 8 个 mixin + backends） |
| `app/main.py` + `app/routes/*.py` | API 层（核心 + 5 个路由模块） |
| `app/langgraph_runtime.py` | LangGraph 7 节点 StateGraph |
| `app/evaluation_nodes.py` | 评估节点（LLM 评分 + 质量门 + 报告生成） |
| `app/llm_provider.py` | LLM 多 provider 抽象 + 三级降级 + 成本追踪 |
| `app/document_parser.py` | 文档解析（PDF/DOCX/Text + 分块 + 元数据） |
| `app/lightrag_service.py` | Chroma 向量索引/检索（auto embedding 降级） |
| `app/reranker.py` | 重排器（TF-IDF + cross-encoder + 超时降级） |
| `app/token_budget.py` | Token 预算（冗余去重 + 低相关裁剪 + 预算控制） |
| `app/constraint_extractor.py` | 约束抽取（5 类：entity/numeric/time/include/exclude） |
| `app/ragas_evaluator.py` | RAGAS + DeepEval 双后端离线评估 |
| `app/performance_benchmark.py` | 性能基准工具（P50/P95/P99） |

### 设计文档

| 文件 | 说明 |
|------|------|
| `docs/plans/2026-02-21-end-to-end-unified-design.md` | SSOT 单一事实源 |
| `docs/design/2026-02-21-implementation-plan.md` | Gate A-F 实施计划 |
| `docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 检索评分规范 |
| `docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 工作流规范 |
| `docs/design/2026-02-21-security-design.md` | 安全设计 |
| `docs/design/2026-02-22-gate-d-four-gates-checklist.md` | Gate D 检查清单 |
| `docs/status/2026-02-24-session-handoff.md` | 本文件 |

---

> 本文件由 2026-02-24 会话更新，供后续 Agent 接续执行。
> 执行原则：先读本文件 -> 确认测试基线 (459 passed) -> 按 §4 任务优先级推进。
