# 项目状态报告与后续路线图

> 版本：v1.0
> 日期：2026-02-23
> 基线：`v2026.02.21-r3`
> 分支：`main`

---

## 1. 执行摘要

### 1.1 当前状态

**整体进度**: 框架层 100% 完成，业务逻辑层 30% 完成

| 层级 | 完成度 | 说明 |
|------|--------|------|
| API 路由 | 100% | 全部 REST 端点已实现 |
| 状态机 | 100% | LangGraph 模式完整 |
| DLQ 流程 | 100% | 死信队列完整 |
| 多租户隔离 | 100% | RLS + 租户上下文 |
| SSOT 对齐 | 100% | 代码与规范一致 |
| Mock LLM | 100% | 端到端可运行 |
| 真实 LLM | 0% | 待实现 |
| 向量检索 | 0% | 待实现 |
| 文档解析 | 0% | 待实现 |

### 1.2 测试覆盖

```
总测试数: 254
通过率: 100%
警告数: 186 (主要为 JWT 密钥长度警告)
```

测试分布：

| 模块 | 测试数 | 覆盖范围 |
|------|--------|----------|
| API 端点 | ~80 | 全部 REST 接口 |
| 工作流 | ~40 | 状态机、checkpoint |
| 租户隔离 | ~20 | RLS、权限 |
| Mock LLM | 14 | 检索、评分、HITL |
| 其他 | ~100 | 存储、DLQ、审计等 |

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

新增文件：

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/mock_llm.py` | 295 | Mock LLM 核心模块 |
| `tests/test_mock_llm.py` | 217 | 单元测试 |

功能清单：

| 函数 | 功能 | 确定性 |
|------|------|--------|
| `mock_retrieve_evidence()` | 基于关键词的证据检索 | ✅ |
| `mock_score_criteria()` | 确定性评分 | ✅ |
| `mock_generate_explanation()` | 解释生成 | ✅ |
| `mock_classify_intent()` | 意图分类 | ✅ |
| `mock_quality_gate_check()` | HITL 触发检查 | ✅ |

### 2.3 文档对齐（2026-02-23）

**Commit**: `docs(api): align citations format with retrieval-and-scoring-spec`

修复 `rest-api-specification.md` 与 `retrieval-and-scoring-spec.md` 的矛盾：

- `citations` 格式统一为对象数组
- 移除 `citations_count` 字段
- 添加对齐说明注释

---

## 3. 架构概览

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│  (FastAPI + JWT Auth + Trace ID + Tenant Context)               │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│   Documents   │      │  Evaluations  │      │    Report     │
│   上传/解析    │      │   评分工作流   │      │   生成/存储    │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      State Machine (LangGraph)                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  load_   │ → │ retrieve │ → │ evaluate │ → │  score_  │     │
│  │ context  │   │ evidence │   │  _rules  │   │with_llm  │     │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘     │
│        │                                           │            │
│        ▼                                           ▼            │
│  ┌──────────┐                              ┌──────────────┐     │
│  │ quality_ │ ── pass ──→ finalize_report  │    human_    │     │
│  │  gate    │                              │    review    │     │
│  └──────────┘ ── hitl ──→                  └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  InMemory   │  │  PostgreSQL │  │   Object    │              │
│  │   Store     │  │  (RLS)      │  │  Storage    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Upload  │ → │ Parse   │ → │ Retrieve│ → │ Score   │
│ Document│    │ Document│    │ Evidence│    │ Criteria│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                    Checkpoint Store                      │
│  (thread_id + checkpoint_id + node + payload)           │
└─────────────────────────────────────────────────────────┘
                                │
                                ▼
                        ┌─────────────┐
                        │   Report    │
                        │  Generation │
                        └─────────────┘
```

### 3.3 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 状态机 | LangGraph | 中断恢复、checkpoint 原生支持 |
| 存储 | InMemory + PostgreSQL | 开发灵活、生产可扩展 |
| 租户隔离 | RLS + 应用层 | 双重保障 |
| LLM 层 | Mock + 可替换 | 渐进式开发 |
| 测试策略 | 单元测试为主 | 快速反馈 |

---

## 4. 待完成工作

### 4.1 核心业务逻辑（P0）

| 任务 | 估时 | 依赖 | 说明 |
|------|------|------|------|
| 真实 LLM 集成 | 中 | - | Claude API 调用 |
| 向量检索 | 中 | pgvector | 证据召回 |
| 文档解析 | 高 | Unstructured | PDF/Word 解析 |
| Embedding 生成 | 低 | 向量检索 | 文本向量化 |

### 4.2 基础设施（P1）

| 任务 | 估时 | 依赖 | 说明 |
|------|------|------|------|
| PostgreSQL + pgvector | 低 | Docker | 向量存储 |
| Redis 缓存 | 低 | Docker | 热点数据 |
| 监控集成 | 低 | Prometheus | 指标暴露 |

### 4.3 质量保证（P2）

| 任务 | 估时 | 依赖 | 说明 |
|------|------|------|------|
| 集成测试 | 中 | 核心逻辑 | E2E 测试 |
| 性能测试 | 低 | 集成测试 | 压力测试 |
| 安全审计 | 中 | 完整功能 | 渗透测试 |

---

## 5. 技术债务

### 5.1 已知问题

| 问题 | 严重程度 | 状态 | 说明 |
|------|----------|------|------|
| JWT 密钥长度不足 | 低 | 警告 | 仅测试环境 |
| Object Storage 存根 | 中 | 已知 | 需实现真实后端 |
| Parser 存根 | 高 | 已知 | 需实现真实解析 |

### 5.2 代码质量

```
代码行数统计:
  app/        ~5,000 行
  tests/      ~3,500 行
  docs/       ~2,000 行

测试/代码比: 0.7:1 (良好)
```

---

## 6. 后续路线图

### 6.1 第一阶段：核心业务逻辑（预计 2-3 周）

```
Week 1: 文档解析
├── 集成 Unstructured/PyMuPDF
├── 实现解析器适配器
└── 生成 chunks + citation_sources

Week 2: 向量检索
├── 配置 PostgreSQL + pgvector
├── 实现 embedding 生成
└── 实现相似度检索

Week 3: 真实 LLM
├── 集成 Claude API
├── 实现 prompt 模板
└── 实现结构化输出
```

### 6.2 第二阶段：端到端验证（预计 1 周）

```
├── 集成测试套件
├── 端到端场景测试
├── HITL 流程验证
└── 性能基准测试
```

### 6.3 第三阶段：生产就绪（预计 1 周）

```
├── 监控与告警
├── 日志聚合
├── 安全加固
└── 部署文档
```

---

## 7. 关键文件索引

### 7.1 设计文档

| 文件 | 说明 |
|------|------|
| `docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 工作流规范 |
| `docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 检索评分规范 |
| `docs/design/2026-02-21-rest-api-specification.md` | REST API 规范 |
| `docs/design/2026-02-21-data-model-and-storage-spec.md` | 数据模型规范 |

### 7.2 实现文档

| 文件 | 说明 |
|------|------|
| `docs/plans/2026-02-23-ssot-alignment-module1-api-response.md` | API 响应对齐 |
| `docs/plans/2026-02-23-ssot-alignment-module2-calculation-logic.md` | 计算逻辑对齐 |
| `docs/plans/2026-02-23-ssot-alignment-module3-workflow-state.md` | 工作流状态对齐 |
| `docs/plans/2026-02-23-mock-llm-implementation.md` | Mock LLM 实现 |

### 7.3 核心代码

| 文件 | 行数 | 说明 |
|------|------|------|
| `app/store.py` | ~5,400 | 存储层核心 |
| `app/main.py` | ~1,200 | API 路由 |
| `app/mock_llm.py` | ~295 | Mock LLM |
| `app/security.py` | ~200 | JWT 认证 |
| `app/tools_registry.py` | ~300 | 工具治理 |

---

## 8. 建议的下一步行动

### 8.1 立即行动（本周）

1. **创建功能分支** `codex/real-llm-integration`
2. **配置 Claude API** 凭证和调用逻辑
3. **实现 Prompt 模板** 结构化评分

### 8.2 短期目标（2 周内）

1. 完成真实 LLM 集成
2. 完成向量检索基础
3. 端到端流程可用

### 8.3 中期目标（1 月内）

1. 文档解析完整实现
2. 集成测试覆盖
3. 性能基准建立

---

## 9. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| LLM API 限流 | 中 | 高 | 实现重试 + 降级 |
| 向量检索精度 | 中 | 中 | 多路召回 + 重排序 |
| 文档解析失败 | 低 | 中 | 多解析器 fallback |
| 性能瓶颈 | 中 | 中 | 异步处理 + 缓存 |

---

## 10. 附录

### 10.1 环境变量清单

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MOCK_LLM_ENABLED` | `true` | Mock LLM 开关 |
| `MOCK_LLM_SCORE_BASELINE` | `0.7` | 基础分数 |
| `MOCK_LLM_CONFIDENCE` | `0.85` | 默认置信度 |
| `JWT_SHARED_SECRET` | - | JWT 密钥 |
| `BEA_OBJECT_STORAGE_BACKEND` | `local` | 存储后端 |
| `DATABASE_URL` | - | PostgreSQL 连接 |

### 10.2 快速命令

```bash
# 运行测试
python3 -m pytest

# 运行特定测试
python3 -m pytest tests/test_mock_llm.py -v

# 检查代码风格
ruff check app/

# 启动开发服务器
uvicorn app.main:create_app --factory --reload
```

---

> 文档维护：每次合并 PR 后更新此文件
> 下次更新：真实 LLM 集成完成后
