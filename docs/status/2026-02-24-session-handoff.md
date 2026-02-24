# 会话交接文档（Session Handoff）

> 日期：2026-02-24（第三次更新）
> 基线：`v2026.02.21-r3`
> 分支：`feat/gate-f-and-real-llm-pipeline`（从 `main` 创建）
> 前序文档：`docs/status/2026-02-23-project-status-and-roadmap.md`

---

## 1. 本次会话完成的工作

### 1.1 Gate F 运营优化证据报告

| 任务 | 完成度 | 说明 |
|------|--------|------|
| F-1 数据回流 | 100% | DLQ 反例 + 人审改判候选 + 版本递增，4 测试通过 |
| F-2 策略优化 | 100% | selector/calibration/tool_policy 可调 + 审批流程 |
| Gate F 证据报告 | 100% | `docs/reports/gate-f-evidence.md` |

### 1.2 真实 LLM E2E 评估链路打通

| 任务 | 完成度 | 说明 |
|------|--------|------|
| Embedding auto 优先级修复 | 100% | API key 存在时优先 OpenAI API 而非 sentence-transformers |
| RAGAS 遥测阻塞修复 | 100% | `RAGAS_DO_NOT_TRACK=true` + 脚本 import 前设置 |
| E2E 评估跑通 | 100% | `--demo --e2e --backend ragas` Quality Gate PASSED |
| D-1 质量门禁（真实 LLM） | 100% | gpt-5-mini via OpenRouter，faithfulness=1.0 |

### 1.3 Rerank API 真实实现

| 任务 | 完成度 | 说明 |
|------|--------|------|
| Cohere Rerank v2 | 100% | `POST api.cohere.com/v2/rerank` + 超时回退 |
| Jina Reranker v1 | 100% | `POST api.jina.ai/v1/rerank` + 超时回退 |
| Backend 专属模型配置 | 100% | `COHERE_RERANK_MODEL` / `JINA_RERANK_MODEL` 环境变量 |
| 新增 6 个测试 | 100% | 成功/失败/无 key/自定义模型/dispatcher |

### 1.4 测试状态

```
总测试数: 544 (较前序 +6)
通过率:   100%
失败数:   0
Lint:     0 errors (ruff)
```

### 1.5 Gate A-F 全链路闭环

| Gate | 状态 | 证据文件 |
|------|------|---------|
| Gate A 设计冻结 | PASS | `docs/design/2026-02-21-gate-a-*` |
| Gate B 契约与骨架 | PASS | `docs/design/2026-02-21-gate-b-*` |
| Gate C 端到端打通 | PASS | E2E 测试 + 主链路可运行 |
| Gate D 四门禁 | PASS | `docs/reports/gate-d-evidence.md` |
| Gate E 灰度与回滚 | PASS | `docs/reports/gate-e-evidence.md` |
| Gate F 运营优化 | PASS | `docs/reports/gate-f-evidence.md` |

**所有 Gate (A-F) 已全部通过。**

---

## 2. 当前分支状态

### 2.1 分支关系

```text
main (含前序所有合并)
  -> feat/gate-f-and-real-llm-pipeline (Gate F 证据 + E2E 真实 LLM + Rerank API)
```

### 2.2 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `app/lightrag_service.py` | 修改 | auto embedding 优先级：API key > sentence-transformers |
| `app/reranker.py` | 修改 | Cohere v2 + Jina v1 API rerank 实现 |
| `scripts/eval_ragas.py` | 修改 | RAGAS_DO_NOT_TRACK 在 import 前设置 |
| `tests/test_reranker.py` | 修改 | +6 API rerank 测试 |
| `docs/reports/gate-f-evidence.md` | 新增 | Gate F 运营优化证据报告 |
| `.env` | 修改 | 新增 RAGAS_DO_NOT_TRACK=true |
| `docs/status/2026-02-24-session-handoff.md` | 更新 | 本文件 |

---

## 3. 后续任务（供 Agent 继续）

### 3.1 立即可执行（无外部依赖）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 合并到 main | P0 | 合并本分支，推送远程 |
| 观测统一平台集成 | P1 | OpenTelemetry 指标/日志/Trace 统一 |
| 告警与回滚自动化联动 | P1 | 门禁 breach 自动触发回滚 |

### 3.2 需要外部配置

| 任务 | 前提 | 说明 |
|------|------|------|
| D-2 性能最终数值 | 生产环境 | `python scripts/benchmark_performance.py` (预热后) |
| PostgreSQL 真栈验证 | `POSTGRES_DSN` | `BEA_STORE_BACKEND=postgres pytest -q` |
| Redis 队列验证 | `REDIS_DSN` | `BEA_QUEUE_BACKEND=redis pytest -q` |
| Cohere/Jina 真实验证 | `COHERE_API_KEY` 或 `JINA_API_KEY` | `RERANK_BACKEND=cohere python -c ...` |

### 3.3 Production Capability 剩余优化

| 任务 | 轨道 | 说明 |
|------|------|------|
| 观测统一平台集成 | P5 | OpenTelemetry 指标/日志/Trace 统一 |
| 告警与回滚自动化联动 | P5 | 门禁 breach 自动触发回滚 |
| 多样化评估数据集 | D-1 | 扩充 golden_qa.json 覆盖更多场景 |

---

## 4. 环境变量配置体系

### 4.1 核心 API

| 变量 | 用途 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | OpenRouter/OpenAI API key | `sk-or-v1-...` |
| `OPENAI_BASE_URL` | API 基础 URL | `https://openrouter.ai/api/v1` |

### 4.2 模型配置

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `LLM_MODEL` | 评分/解释 LLM | `openai/gpt-5-mini` |
| `LLM_FALLBACK_MODEL` | 降级 LLM | `openai/gpt-5-mini` |
| `RAGAS_MODEL` | RAGAS 评估 LLM | `openai/gpt-5-mini` |
| `DEEPEVAL_MODEL` | DeepEval 评估 LLM | `openai/gpt-5-mini` |
| `EMBEDDING_MODEL` | 嵌入模型 | `openai/text-embedding-3-small` |
| `RERANK_BACKEND` | 重排序后端 | `simple` |
| `RERANK_MODEL_NAME` | cross-encoder 模型 | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `COHERE_RERANK_MODEL` | Cohere 重排序模型 | `rerank-v3.5` |
| `JINA_RERANK_MODEL` | Jina 重排序模型 | `jina-reranker-v2-base-multilingual` |

### 4.3 API Key（外部服务）

| 变量 | 用途 |
|------|------|
| `COHERE_API_KEY` | Cohere Rerank API |
| `JINA_API_KEY` | Jina Reranker API |

### 4.4 运行控制

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `MOCK_LLM_ENABLED` | Mock 模式开关 | `false` |
| `RAGAS_DO_NOT_TRACK` | 禁用 RAGAS 遥测 | `true` |
| `TASK_TOKEN_BUDGET` | 单任务 token 预算 | `50000` |

---

## 5. 快速启动命令

```bash
# 安装依赖
python3 -m pip install -e '.[dev]'

# 运行全量测试（应显示 544 passed）
python3 -m pytest -q

# 运行 Gate F 测试
python3 -m pytest tests/test_gate_f_ops_optimization.py -v

# 运行 Rerank 测试
python3 -m pytest tests/test_reranker.py -v

# 运行 RAGAS E2E 评估（需 OPENAI_API_KEY）
python3 scripts/eval_ragas.py --demo --e2e --backend ragas

# 运行 RAGAS 评估（lightweight 模式，无需 API key）
python3 scripts/eval_ragas.py --demo --backend lightweight

# 运行性能基准
python3 scripts/benchmark_performance.py --iterations 10

# 代码检查
ruff check app/

# 启动 API 服务（Mock 模式）
MOCK_LLM_ENABLED=true uvicorn app.main:create_app --factory --reload
```

---

## 6. 关键文件索引

### 本次新增/修改

| 文件 | 说明 |
|------|------|
| `docs/reports/gate-f-evidence.md` | Gate F 运营优化证据报告 |
| `app/lightrag_service.py` | Embedding auto 优先级修复 |
| `app/reranker.py` | Cohere/Jina API rerank 真实实现 |
| `scripts/eval_ragas.py` | RAGAS 遥测阻塞修复 |
| `tests/test_reranker.py` | +6 API rerank 测试 |

### 核心业务（同前序）

| 文件 | 说明 |
|------|------|
| `app/store.py` + `app/store_*.py` | 存储层（核心 + 8 个 mixin + backends） |
| `app/main.py` + `app/routes/*.py` | API 层（核心 + 5 个路由模块） |
| `app/langgraph_runtime.py` | LangGraph 7 节点 StateGraph |
| `app/object_storage.py` | 对象存储（Local + S3 + WORM + legal hold） |
| `app/repositories/*.py` | 仓储层（11 个，InMemory + Postgres 双实现） |
| `app/ragas_evaluator.py` | RAGAS/DeepEval 评估器（已适配 v0.4.3） |
| `app/llm_provider.py` | LLM 提供者抽象（OpenRouter/Ollama） |

### 设计文档

| 文件 | 说明 |
|------|------|
| `docs/plans/2026-02-21-end-to-end-unified-design.md` | SSOT 单一事实源 |
| `docs/design/2026-02-21-implementation-plan.md` | Gate A-F 实施计划 |
| `docs/reports/gate-d-evidence.md` | Gate D 四门禁证据报告 |
| `docs/reports/gate-e-evidence.md` | Gate E 灰度回滚证据报告 |
| `docs/reports/gate-f-evidence.md` | Gate F 运营优化证据报告 |

---

> 本文件由 2026-02-24 第三次会话更新，供后续 Agent 接续执行。
> 执行原则：先读本文件 -> 确认测试基线 (544 passed) -> 按 §3 后续任务推进。
> **Gate A-F 全部通过，项目进入生产准备阶段。**
