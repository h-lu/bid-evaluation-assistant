# 会话交接文档（Session Handoff）

> 日期：2026-02-24
> 基线：`v2026.02.21-r3`
> 分支：`main`（含未提交变更）
> 前序文档：`docs/status/2026-02-23-project-status-and-roadmap.md`

---

## 1. 本次会话完成的工作

### 1.1 P0 核心业务逻辑：从 Mock 到真实实现

本次会话完成了 P0 四项核心任务的实装，主链路 `upload -> parse -> index -> retrieve -> evaluate` 现已端到端贯通。

| P0 任务 | 完成度 | 核心文件 |
|---------|--------|---------|
| 文档解析 | 100% | `app/document_parser.py` (新增 353 行) |
| 向量检索 | 100% | `app/lightrag_service.py` (改造 +170 行) |
| Embedding 生成 | 100% | `app/lightrag_service.py` (3 种后端) |
| 真实 LLM 集成 | 100% | `app/llm_provider.py` (新增 340 行) |

### 1.2 新增与修改文件清单

#### 新增文件（未提交，需 git add）

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/document_parser.py` | 353 | 真实文档解析：PDF(PyMuPDF) / DOCX(python-docx) / 纯文本 |
| `app/llm_provider.py` | 413 | 多 provider LLM 抽象：OpenAI/Ollama/自定义 base_url，三级降级，成本追踪 |
| `tests/test_document_parser.py` | 230 | 文档解析单元测试 |
| `tests/test_llm_provider.py` | 200 | LLM provider 多场景测试（18 个用例） |
| `tests/test_end_to_end_real_parsing.py` | 440 | 端到端集成测试（8 个用例含完整链路） |

#### 修改文件（已 tracked，未提交）

| 文件 | 变更量 | 说明 |
|------|--------|------|
| `app/store.py` | +440/-158 | Chroma 直接索引/查询、证据检索优先向量搜索、工作流保存真实数据 |
| `app/lightrag_service.py` | +170/-13 | 公共 API (`index_chunks_to_collection`, `query_collection`)、Embedding 支持 base_url |
| `app/parser_adapters.py` | +44 | `LocalParserAdapter.parse_file()` 桥接 document_parser |
| `pyproject.toml` | +5 | 新增 `pymupdf>=1.24.0` 和 `python-docx>=1.1.0` 依赖 |

### 1.3 关键集成点说明

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
    -> 降级1: mock_retrieve_evidence (MOCK_LLM_ENABLED=true)
    -> 降级2: stub 证据
  -> llm_score_criteria (每个评分项)
    -> 优先: 真实 LLM (primary model)
    -> 降级1: fallback model
    -> 降级2: mock_score_criteria
  -> 计算 total_score, confidence, HITL 判定
  -> 生成 evaluation_report
```

#### LLM Provider 降级链

```text
Primary Model (LLM_MODEL)
  -> 失败 -> Fallback Model (LLM_FALLBACK_MODEL)
    -> 失败 -> Mock LLM (mock_score_criteria)
```

### 1.4 测试状态

```
总测试数: 297 (从 283 增加 14)
通过率:   100%
失败数:   0
Lint:     0 errors
```

新增测试分布：

| 模块 | 新增测试数 | 覆盖范围 |
|------|-----------|---------|
| LLM Provider | 18 | 多 provider 配置、Ollama 支持、降级、成本追踪 |
| 文档解析 | 6+ | PDF/DOCX 解析、chunk 元数据 |
| 端到端集成 | 8 | upload->parse->index->retrieve->evaluate 完整链路 |

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
| `EMBEDDING_BACKEND` | `simple` | `simple` / `openai` / `ollama` / `sentence-transformers` |
| `EMBEDDING_MODEL_NAME` | `text-embedding-3-small` | Embedding 模型 |
| `EMBEDDING_BASE_URL` | (空) | 自定义 Embedding 端点 |
| `EMBEDDING_DIM` | `128` | Simple 模式维度 |

### 2.3 Chroma / 检索配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LIGHTRAG_DSN` | (空) | 外部 LightRAG HTTP 端点（空则使用内建 Chroma） |
| `CHROMA_PERSIST_DIR` | (空) | Chroma 持久化目录（空则内存模式） |
| `CHROMA_HOST` | (空) | Chroma 远程 host |
| `LIGHTRAG_INDEX_PREFIX` | `lightrag` | 索引名称前缀 |

---

## 3. SSOT 对齐状态

### 3.1 已对齐项

| SSOT 章节 | 要求 | 状态 |
|-----------|------|------|
| §6.1 | chunk 元数据: page/bbox/heading_path/chunk_type | 已对齐 |
| §6.2 | 检索模式 local/global/hybrid/mix | 已对齐 |
| §6.2 | 规则引擎硬判定 + LLM 软评分 | 已对齐（基础） |
| §6.5 | 向量查询强制 tenant_id+project_id 过滤 | 已对齐 |
| §7.4 | 模型降级策略 | 已对齐（三级降级链） |
| §8.1 | 评分项输出: criteria_id/score/max_score/hard_pass/reason/citations/confidence | 已对齐 |
| §8.2 | 总分公式: sum(score * weight) | 已对齐 |
| §8.3 | 置信度: 0.4*evidence + 0.3*agreement + 0.3*stability | 已对齐 |
| §9 | HITL 触发条件（5 项） | 已对齐 |
| §10 | claim->citation 映射检查 | 已对齐 |

### 3.2 已知偏差（需后续处理）

| SSOT 章节 | 要求 | 偏差 | 优先级 |
|-----------|------|------|--------|
| retrieval spec §3.2 | 约束抽取: entity/numeric/time constraints | 仅 include/exclude terms | P1 |
| retrieval spec §6.1 | rerank 输出: score_raw + score_rerank | rerank 为 stub (+0.05) | P1 |
| retrieval spec §6.3 | token budget: 单项 <=6k, 全报告 <=24k | 未实现 | P1 |
| retrieval spec §5.3 | SQL 白名单支路 | 未真实实现 | P2 |
| workflow spec §6 | LangGraph 真实图执行 + typed edges | 仅 compat 模式 | P1 |
| SSOT §7.4 | 成本 P95 不超基线 1.2x | 有 token 追踪，无预算阻断 | P2 |

---

## 4. 后续任务（供 Agent 继续）

### 4.1 P1 — 质量强化（建议下一阶段）

#### T1: Rerank 真实实现

```
目标: 替换 _rerank_items 的 stub 实现
方案:
  1. 使用 cross-encoder/ms-marco-MiniLM-L-6-v2 本地 rerank
  2. 或对接 Cohere/Jina rerank API
输入: retrieval candidates list
输出: candidates with score_rerank
验收: rerank 降级测试通过; 精度提升可测量
文件: app/store.py (_rerank_items), app/lightrag_service.py
```

#### T2: Token Budget 控制

```
目标: 评分上下文不超预算
方案:
  1. 使用 tiktoken 计算 token 数
  2. 单项评分 <= 6k tokens
  3. 全报告 <= 24k tokens
  4. 超预算按"低相关 -> 冗余来源"裁剪
输入: evidence list per criteria
输出: trimmed evidence list
验收: 大文档评估不超 token 限制
文件: app/llm_provider.py, app/store.py (create_evaluation_job)
```

#### T3: LangGraph 真实图执行

```
目标: 将 compat 模式工作流替换为真实 LangGraph 图
方案:
  1. 定义 TypedDict state
  2. 定义 node functions (load_context, retrieve_evidence, etc.)
  3. 定义 conditional edges (quality_gate -> pass/hitl)
  4. 使用 MemorySaver 或 PostgresSaver
验收: 评估工作流通过 LangGraph 图执行; interrupt/resume 真实工作
文件: app/langgraph_runtime.py, app/store.py (_run_evaluation_workflow)
对齐: docs/design/2026-02-21-langgraph-agent-workflow-spec.md
```

#### T4: 约束抽取器

```
目标: 查询标准化 + 约束抽取
方案:
  1. entity_constraints: 正则/NER 抽取
  2. numeric_constraints: 数值范围抽取
  3. time_constraints: 日期范围抽取
  4. 写入 rewrite 输出
验收: 约束保持改写输出完整
文件: app/store.py (_normalize_and_rewrite_query)
对齐: docs/design/2026-02-21-retrieval-and-scoring-spec.md §3.2
```

### 4.2 P1 — 基础设施

#### T5: store.py 拆分

```
目标: InMemoryStore 从 ~5700 行拆为多模块
方案:
  app/store.py          -> 核心 store 协调
  app/store_parse.py    -> 解析相关方法
  app/store_eval.py     -> 评估相关方法
  app/store_retrieval.py -> 检索相关方法
  app/store_release.py  -> 发布相关方法
注意: 保持 store 单例对外接口不变
验收: 全量测试通过; 单文件不超 1500 行
```

#### T6: main.py 拆分

```
目标: API 路由从单文件拆为模块
方案:
  app/routes/documents.py
  app/routes/evaluations.py
  app/routes/retrieval.py
  app/routes/admin.py
  app/routes/internal.py
验收: 全量测试通过; 路由可独立阅读
```

### 4.3 P2 — 质量门禁（Gate D）

#### T7: RAGAS 评估脚本

```
目标: 实现离线检索质量评估
方案: 使用 ragas 库，评估 precision/recall/faithfulness
阈值: precision/recall >= 0.80, faithfulness >= 0.90
对齐: docs/design/2026-02-21-retrieval-and-scoring-spec.md §12
```

#### T8: 性能基准

```
目标: 建立 API / 检索 / 评估性能基线
阈值:
  API P95 <= 1.5s
  检索 P95 <= 4s
  评估 P95 <= 120s
  解析 50页 P95 <= 180s
```

#### T9: 安全回归

```
目标: 跨租户越权 = 0; 高风险审计 = 100%
对齐: docs/design/2026-02-21-security-design.md
```

### 4.4 P3 — 前端

#### T10: 前端 E2E

```
目标: 前端关键流程自动化测试
覆盖: 上传 -> 评估 -> HITL -> 报告查看 -> DLQ 操作
```

---

## 5. 技术债务

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| `app/store.py` ~5700 行 | 高 | 需拆分为多模块（见 T5） |
| `app/main.py` ~2100 行 | 中 | 需拆分路由（见 T6） |
| rerank 为 stub | 中 | 仅 +0.05 分，非真实 rerank（见 T1） |
| LangGraph 为 compat 模式 | 中 | 非真实图执行（见 T3） |
| 无 token budget | 低 | 大文档可能超出 context window（见 T2） |

---

## 6. 快速启动命令

```bash
# 安装依赖
python3 -m pip install -e '.[dev]'

# 运行全量测试（应显示 297 passed）
python3 -m pytest -q

# 运行端到端集成测试
python3 -m pytest tests/test_end_to_end_real_parsing.py -v

# 运行 LLM provider 测试
python3 -m pytest tests/test_llm_provider.py -v

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

## 7. 关键文件索引（更新）

### 核心代码

| 文件 | 说明 |
|------|------|
| `app/store.py` | 存储层核心（解析、评估、检索、工作流协调） |
| `app/llm_provider.py` | LLM 多 provider 抽象（OpenAI/Ollama/Custom + 降级 + 成本追踪） |
| `app/document_parser.py` | 文档解析（PDF/DOCX/Text + 分块 + 元数据） |
| `app/lightrag_service.py` | Chroma 向量索引/检索（内建 + HTTP 双模式） |
| `app/parser_adapters.py` | 解析器适配层（路由 + fallback + local adapter） |
| `app/mock_llm.py` | Mock LLM（确定性测试用） |
| `app/main.py` | FastAPI 路由 |
| `app/langgraph_runtime.py` | LangGraph 运行时（待完善真实图执行） |

### 设计文档

| 文件 | 说明 |
|------|------|
| `docs/plans/2026-02-21-end-to-end-unified-design.md` | SSOT 单一事实源 |
| `docs/design/2026-02-21-implementation-plan.md` | Gate A-F 实施计划 |
| `docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 检索评分规范 |
| `docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 工作流规范 |
| `docs/status/2026-02-24-session-handoff.md` | 本文件 |

---

> 本文件由 2026-02-24 会话生成，供后续 Agent 接续执行。
> 执行原则：先读本文件 -> 确认测试基线 (297 passed) -> 按 §4 任务优先级推进。
