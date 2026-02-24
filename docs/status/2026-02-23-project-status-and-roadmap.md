# 项目状态报告与后续路线图

> 版本：v2.0
> 日期：2026-02-24（更新）
> 基线：`v2026.02.21-r3`
> 分支：`main`

---

## 1. 执行摘要

### 1.1 当前状态

**整体进度**: 框架层 100% 完成，业务逻辑层 70% 完成

| 层级 | 完成度 | 说明 |
|------|--------|------|
| API 路由 | 100% | 全部 REST 端点已实现 |
| 状态机 | 100% | LangGraph compat 模式完整 |
| DLQ 流程 | 100% | 死信队列完整 |
| 多租户隔离 | 100% | RLS + 租户上下文 |
| SSOT 对齐 | 100% | 代码与规范一致 |
| Mock LLM | 100% | 端到端可运行 |
| 真实 LLM | 100% | 多 provider 支持 + 降级链 |
| 向量检索 | 100% | Chroma 内建 + HTTP 双模式 |
| 文档解析 | 100% | PDF / DOCX / 纯文本 |
| Embedding | 100% | Simple / OpenAI / Ollama / SentenceTransformers |
| Rerank | 20% | stub 实现，待真实模型 |
| LangGraph 真图 | 30% | compat 模式，非真实图执行 |

### 1.2 测试覆盖

```
总测试数: 297
通过率: 100%
Lint: 0 errors
```

测试分布：

| 模块 | 测试数 | 覆盖范围 |
|------|--------|----------|
| API 端点 | ~80 | 全部 REST 接口 |
| 工作流 | ~40 | 状态机、checkpoint |
| 租户隔离 | ~20 | RLS、权限 |
| Mock LLM | 14 | 检索、评分、HITL |
| LLM Provider | 18 | 多 provider、降级、成本追踪 |
| 文档解析 | 12 | PDF/DOCX 解析、分块、元数据 |
| 端到端集成 | 8 | upload->parse->index->retrieve->evaluate |
| 其他 | ~105 | 存储、DLQ、审计、Gate D/E/F 等 |

---

## 2. 已完成工作

### 2.1 SSOT 对齐（2026-02-23）

**PR #2**: `feat(ssot): align codebase with Single Source of Truth specifications`

| 模块 | 变更 | 文件 |
|------|------|------|
| API 响应 | `citations` 从 `list[str]` 改为 `list[dict]` | `app/store.py` |
| 计算逻辑 | 实现真实 `retrieval_agreement` | `app/store.py` |
| 工作流状态 | 新增 `get_workflow_state()` | `app/store.py` |
| 存储层 | 移除 `weight`/`citations_count` | `app/store.py` |
| HITL 原因 | 准确记录触发条件 | `app/store.py` |

### 2.2 Mock LLM 实现（2026-02-23）

**PR #3**: `feat(llm): add Mock LLM module for end-to-end flow validation`

| 函数 | 功能 | 确定性 |
|------|------|--------|
| `mock_retrieve_evidence()` | 基于关键词的证据检索 | 是 |
| `mock_score_criteria()` | 确定性评分 | 是 |
| `mock_generate_explanation()` | 解释生成 | 是 |
| `mock_classify_intent()` | 意图分类 | 是 |
| `mock_quality_gate_check()` | HITL 触发检查 | 是 |

### 2.3 P0 核心业务逻辑（2026-02-24）

#### 2.3.1 文档解析

| 文件 | 说明 |
|------|------|
| `app/document_parser.py` | PDF(PyMuPDF)/DOCX(python-docx)/纯文本解析 |
| `app/parser_adapters.py` | LocalParserAdapter 桥接真实解析 |

能力：
1. PDF 解析：逐页提取文本块，bbox 归一化，heading 提取
2. DOCX 解析：段落提取，heading 识别，虚拟分页
3. 分块：可配置 chunk_size/overlap，重叠窗口，小块合并
4. 元数据：page, bbox, heading_path, chunk_type, chunk_hash

#### 2.3.2 向量检索

| 文件 | 说明 |
|------|------|
| `app/lightrag_service.py` | Chroma 索引/查询（内建 + HTTP 双模式） |
| `app/store.py` | 集成点：_maybe_index_chunks_to_lightrag, _query_lightrag |

能力：
1. Parse 后自动索引到 Chroma（无需外部服务）
2. 评估时优先向量检索证据
3. 租户/项目/供应商过滤强制执行
4. Embedding 支持 4 种后端（simple/openai/ollama/sentence-transformers）
5. 所有后端支持 base_url 自定义

#### 2.3.3 真实 LLM 集成

| 文件 | 说明 |
|------|------|
| `app/llm_provider.py` | 多 provider LLM 抽象 |

能力：
1. 三种 provider：OpenAI、Ollama、自定义 OpenAI 兼容 API
2. 三级降级链：Primary Model -> Fallback Model -> Mock
3. 每次调用追踪 token 计数和延迟
4. 结构化 JSON 输出（评分）
5. 所有配置通过环境变量，无需改代码

---

## 3. 架构概览

### 3.1 系统架构

```
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
                                       | Document Parser       |  | Evaluation Workflow  |
                                       | PyMuPDF / python-docx |  | LLM Provider + Rules |
                                       +----------+-----------+  +----------+-----------+
                                                  |                         |
                                                  +------------+------------+
                                                               |
                                                               v
                     +--------------------------------------------------------------+
                     | Chroma (vector index) + Citation Sources (in-memory/PG)     |
                     | PostgreSQL (truth + audit + checkpoint + dlq + outbox)      |
                     | Object Storage (WORM evidence/report)                       |
                     +--------------------------------------------------------------+
```

### 3.2 LLM 调用架构

```
+---------------------+
| llm_provider.py     |
|                     |
| Environment Config  |
| LLM_PROVIDER=...    |
| LLM_MODEL=...       |
| OPENAI_BASE_URL=... |
+--------+------------+
         |
         v
+--------+------------+
| _call_with_degradation |
|                        |
| 1. Primary Model ------+---> OpenAI API
|    (LLM_MODEL)         |     (api.openai.com)
|                        |
| 2. Fallback Model -----+---> Custom API
|    (LLM_FALLBACK_MODEL)|     (base_url)
|                        |
| 3. Mock LLM -----------+---> mock_llm.py
|    (final fallback)    |     (deterministic)
+------------------------+
         |
         v
+--------+------------+
| LLMUsage tracking   |
| prompt_tokens        |
| completion_tokens    |
| latency_ms           |
| degraded flag        |
+---------------------+
```

### 3.3 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 状态机 | LangGraph (compat) | 中断恢复、checkpoint 原生支持 |
| 存储 | InMemory + PostgreSQL | 开发灵活、生产可扩展 |
| 租户隔离 | RLS + 应用层 | 双重保障 |
| LLM 层 | 多 Provider + 降级链 | 灵活切换本地/远程模型 |
| 向量索引 | Chroma (内建) | 零配置可用，支持远程部署 |
| 文档解析 | PyMuPDF + python-docx | 无外部服务依赖 |
| 测试策略 | 单元 + 集成 E2E | 快速反馈 + 链路验证 |

---

## 4. 待完成工作

### 4.1 P1 — 质量强化

| 任务 | 估时 | 说明 | SSOT 对齐 |
|------|------|------|-----------|
| Rerank 真实实现 | 中 | cross-encoder 或 Cohere/Jina API | retrieval spec §6.1 |
| Token budget 控制 | 低 | tiktoken 计数 + 裁剪 | retrieval spec §6.3 |
| LangGraph 真实图执行 | 高 | typed state + conditional edges | workflow spec §3 |
| 约束抽取器 | 中 | entity/numeric/time constraints | retrieval spec §3.2 |

### 4.2 P1 — 基础设施

| 任务 | 估时 | 说明 |
|------|------|------|
| store.py 拆分 (~5700行) | 中 | 拆为 parse/eval/retrieval/release |
| main.py 拆分 (~2100行) | 中 | 拆为 routes 模块 |
| PostgreSQL + pgvector | 低 | 替换 InMemory 后端 |
| Redis 缓存 | 低 | 热点数据 |

### 4.3 P2 — 质量门禁（Gate D）

| 任务 | 估时 | 说明 |
|------|------|------|
| RAGAS 评估脚本 | 中 | precision/recall >= 0.80, faithfulness >= 0.90 |
| 性能基准 | 低 | API P95 / 检索 P95 / 评估 P95 |
| 安全回归 | 中 | 跨租户越权 = 0 |

### 4.4 P3 — 前端

| 任务 | 估时 | 说明 |
|------|------|------|
| 前端 E2E 测试 | 中 | 上传 -> 评估 -> HITL -> 报告 |
| PDF bbox 高亮 | 中 | 真实坐标回跳 |

---

## 5. 技术债务

| 问题 | 严重程度 | 状态 | 说明 |
|------|----------|------|------|
| store.py ~5700 行 | 高 | 已知 | 需拆分为多模块 |
| main.py ~2100 行 | 中 | 已知 | 需拆分路由 |
| rerank stub | 中 | 已知 | 仅 +0.05 分 |
| LangGraph compat | 中 | 已知 | 非真实图执行 |
| 无 token budget | 低 | 已知 | 大文档可能超 context |

---

## 6. 环境变量配置

### 6.1 LLM 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` | `openai` / `ollama` / `custom` |
| `LLM_MODEL` | `gpt-4o-mini` | 主模型 |
| `LLM_FALLBACK_MODEL` | (空) | 备用模型 |
| `LLM_TEMPERATURE` | `0.1` | 温度 |
| `OPENAI_API_KEY` | (空) | API 密钥 |
| `OPENAI_BASE_URL` | (空) | 自定义端点 |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 端点 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama 模型 |
| `MOCK_LLM_ENABLED` | `true` | Mock 开关 |

### 6.2 Embedding 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_BACKEND` | `simple` | `simple`/`openai`/`ollama`/`sentence-transformers` |
| `EMBEDDING_MODEL_NAME` | `text-embedding-3-small` | 模型名 |
| `EMBEDDING_BASE_URL` | (空) | 自定义端点 |

### 6.3 其他

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `JWT_SHARED_SECRET` | (空) | JWT 密钥 |
| `BEA_OBJECT_STORAGE_BACKEND` | `local` | 存储后端 |
| `DATABASE_URL` | (空) | PostgreSQL 连接 |
| `CHROMA_PERSIST_DIR` | (空) | Chroma 持久化 |

---

## 7. 快速命令

```bash
# 运行全量测试
python3 -m pytest -q

# 运行端到端集成测试
python3 -m pytest tests/test_end_to_end_real_parsing.py -v

# 运行 LLM provider 测试
python3 -m pytest tests/test_llm_provider.py -v

# 代码检查
ruff check app/

# Mock 模式启动
uvicorn app.main:create_app --factory --reload

# Ollama 本地模型启动
MOCK_LLM_ENABLED=false LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b \
  EMBEDDING_BACKEND=ollama EMBEDDING_MODEL_NAME=nomic-embed-text \
  uvicorn app.main:create_app --factory --reload
```

---

## 8. 关键文件索引

### 8.1 核心代码

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/store.py` | ~5,700 | 存储层核心 |
| `app/main.py` | ~2,100 | API 路由 |
| `app/llm_provider.py` | ~413 | 多 provider LLM |
| `app/document_parser.py` | ~352 | 文档解析 |
| `app/lightrag_service.py` | ~316 | 向量索引/检索 |
| `app/mock_llm.py` | ~300 | Mock LLM |
| `app/parser_adapters.py` | ~365 | 解析器适配 |
| `app/security.py` | ~200 | JWT 认证 |

### 8.2 交接文档

| 文件 | 说明 |
|------|------|
| `docs/status/2026-02-24-session-handoff.md` | 会话交接（详细集成点说明） |
| `docs/status/2026-02-23-project-status-and-roadmap.md` | 本文件 |

---

> 文档维护：每次合并 PR 后更新此文件
> 下次更新：P1 任务完成后
