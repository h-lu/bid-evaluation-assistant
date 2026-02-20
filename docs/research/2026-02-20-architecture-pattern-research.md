# 架构模式选型研究：分层单体 vs 模块化单体

> 研究日期：2026-02-20
> 研究范围：架构模式对比、Python/FastAPI 最佳实践、AI/RAG 应用架构
> 数据来源：GitHub、Context7、Web Search

---

## 一、架构模式对比

### 1.1 分层单体（Layered Monolith）

**结构示意：**
```
app/
├── controllers/          # API 层
│   ├── bid_controller.py
│   └── doc_controller.py
├── services/             # 业务逻辑层
│   ├── bid_service.py
│   └── rag_service.py
├── models/               # 数据模型层
│   ├── bid.py
│   └── document.py
├── repositories/         # 数据访问层
└── main.py
```

**特点：**
| 优点 | 缺点 |
|------|------|
| ✅ 结构简单，快速上手 | ❌ 代码容易紧密耦合 |
| ✅ 部署简单（单一单元） | ❌ 模块边界模糊 |
| ✅ 共享内存，调用高效 | ❌ 改一处可能影响全局 |
| ✅ 适合小型团队 | ❌ 难以独立测试/扩展 |

### 1.2 模块化单体（Modular Monolith）

**结构示意：**
```
src/
├── modules/                      # 业务模块（按领域划分）
│   ├── evaluation/               # 评标模块（限界上下文）
│   │   ├── domain/               # 领域层
│   │   │   ├── entities.py
│   │   │   ├── value_objects.py
│   │   │   └── events.py
│   │   ├── application/          # 应用层
│   │   │   ├── services.py
│   │   │   ├── commands.py
│   │   │   └── queries.py
│   │   ├── infrastructure/       # 基础设施层
│   │   │   ├── repositories.py
│   │   │   └── adapters.py
│   │   └── api/                  # 接口层
│   │       ├── router.py
│   │       └── schemas.py
│   ├── documents/                # 文档解析模块
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   ├── retrieval/                # RAG 检索模块
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/
│   └── compliance/               # 合规审查模块
│       └── ...
├── core/                         # 共享核心
│   ├── config.py
│   ├── database.py
│   ├── events.py                 # 事件总线
│   └── exceptions.py
└── main.py
```

**特点：**
| 优点 | 缺点 |
|------|------|
| ✅ 清晰的模块边界（DDD 限界上下文） | ⚠️ 需要更多设计工作 |
| ✅ 模块可独立测试 | ⚠️ 团队需要理解 DDD |
| ✅ 单一部署单元（运维简单） | ⚠️ 仍需约束模块间依赖 |
| ✅ 可演进到微服务 | |
| ✅ 便于团队分工（模块所有权） | |

---

## 二、2025-2026 行业趋势

### 2.1 为什么模块化单体正在回归

| 因素 | 说明 |
|------|------|
| **微服务不是银弹** | 引入分布式复杂性、运维开销、网络延迟 |
| **成本控制** | 原 4核8G 能跑的应用，拆微服务后需要 10 台机器 |
| **调试简化** | 一个请求报错不需要跨越 5 个服务查 10 个日志 |
| **性能优势** | 内存函数调用 vs RPC 网络调用 |

**核心观点：** 2026 年架构理念是"**单体优先**"（Monolithic-First）

### 2.2 适用场景对比

| 场景 | 推荐架构 |
|------|----------|
| 团队 < 5 人 | 分层单体 |
| 团队 5-20 人 | **模块化单体** |
| 团队 > 20 人 + 独立部署需求 | 微服务 |
| 代码量 < 10 万行 | 分层单体 |
| 代码量 10-50 万行 | **模块化单体** |
| 代码量 > 50 万行 | 考虑微服务 |

### 2.3 AI/RAG 应用架构最佳实践

```
┌─────────────────────────────────────────┐
│        应用层（业务逻辑）                  │  ← 评标流程编排
├─────────────────────────────────────────┤
│        AI 能力层                         │  ← 意图识别、RAG、推理
├─────────────────────────────────────────┤
│        数据层                            │  ← 知识库、向量库、图谱
├─────────────────────────────────────────┤
│        基础设施层                         │  ← 高并发、部署、监控
└─────────────────────────────────────────┘
```

**关键发现：**
- AI 团队使用模块化架构，模型部署频率提升 **3-5 倍**
- 恢复时间减少 **70%+**
- 不同组件可按需扩展（推理用 CPU，训练用 GPU）

---

## 三、GitHub 高星项目参考

### 3.1 FastAPI 企业级模板

| 项目 | Stars | 架构模式 | 适用场景 |
|------|-------|----------|----------|
| [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | 36k+ | 分层架构 | 全栈项目、快速启动 |
| [FastAPI-boilerplate](https://github.com/teamhide/fastapi-boilerplate) | 3k+ | 分层 + CRUD | 后端 API 服务 |
| [FastAPI-Template](https://github.com/JiayuXu0/FastAPI-Template) | 1k+ | 三层架构 + RBAC | 企业级后端 |

### 3.2 模块化单体参考

| 项目 | 描述 |
|------|------|
| [python-ddd](https://gitcode.com/gh_mirrors/py/python-ddd) | 完整的在线拍卖系统，模块化单体 DDD 实现 |
| [modular-monolith-with-ddd](https://gitcode.com/GitHub_Trending/mo/modular-monolith-with-ddd) | C# 实现，架构思想可借鉴 |

### 3.3 推荐的模块结构

```python
# 每个模块自包含
src/modules/evaluation/
├── domain/                  # 领域层（纯 Python，无框架依赖）
│   ├── entities.py          # 实体：BidEvaluation, Score
│   ├── value_objects.py     # 值对象：Confidence, Criterion
│   └── events.py            # 领域事件：ScoreCalculated
├── application/             # 应用层（编排）
│   ├── services.py          # 应用服务
│   ├── commands.py          # 命令
│   └── queries.py           # 查询
├── infrastructure/          # 基础设施层（外部依赖）
│   ├── repositories.py      # 仓储实现
│   ├── adapters.py          # 外部服务适配器
│   └── models.py            # ORM 模型
└── api/                     # 接口层
    ├── router.py            # FastAPI 路由
    └── schemas.py           # Pydantic 模型
```

---

## 四、评标系统架构建议

### 4.1 限界上下文划分

基于评标业务域，建议划分为以下模块：

```
src/modules/
├── evaluation/           # 评标核心
│   └── 职责：评分计算、报告生成、人工审核
├── documents/            # 文档管理
│   └── 职责：上传、解析、分块、存储
├── retrieval/            # RAG 检索
│   └── 职责：向量检索、图谱查询、重排序
├── compliance/           # 合规审查
│   └── 职责：资质校验、合规检测、风险预警
├── workflow/             # 工作流编排
│   └── 职责：LangGraph 编排、状态管理
└── users/                # 用户管理
    └── 职责：认证、授权、审计日志
```

### 4.2 模块间通信

```
┌─────────────────────────────────────────────────────────────┐
│                     Module Communication                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   evaluation ──────┬──────> workflow (命令)                   │
│        │           │                                          │
│        │           └──────> retrieval (查询)                  │
│        │                                                      │
│        └──────────────────> compliance (事件)                 │
│                                   │                           │
│   documents ───────────────────> retrieval (事件)            │
│                                                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              Event Bus (内存)                         │   │
│   │  • DocumentParsed → retrieval.reindex                │   │
│   │  • ScoreCalculated → compliance.check                │   │
│   │  • ReviewRequested → notification.send               │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 目录结构（推荐）

```
bid-evaluation-assistant/
├── src/
│   ├── modules/
│   │   ├── evaluation/
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── entities.py       # BidEvaluation, Score, Report
│   │   │   │   ├── value_objects.py  # Confidence, Criterion, Evidence
│   │   │   │   └── events.py         # ScoreCalculated, ReviewRequested
│   │   │   ├── application/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── services.py       # EvaluationService
│   │   │   │   ├── commands.py       # CalculateScoreCommand
│   │   │   │   └── queries.py        # GetEvaluationQuery
│   │   │   ├── infrastructure/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── repositories.py   # SQLAlchemyEvaluationRepository
│   │   │   │   └── adapters.py       # LangGraphAdapter, DSPyAdapter
│   │   │   └── api/
│   │   │       ├── __init__.py
│   │   │       ├── router.py         # /api/v1/evaluations/*
│   │   │       └── schemas.py        # Pydantic models
│   │   ├── documents/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   │   ├── parsers/          # MinerU, Docling, PaddleOCR
│   │   │   │   └── chunkers/         # Recursive, Semantic
│   │   │   └── api/
│   │   ├── retrieval/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   │   ├── lightrag/         # LightRAG 集成
│   │   │   │   ├── vectorstore/      # ChromaDB
│   │   │   │   └── reranker/         # BGE-Reranker
│   │   │   └── api/
│   │   ├── compliance/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   └── api/
│   │   ├── workflow/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   │   └── graphs/           # LangGraph 工作流定义
│   │   │   ├── infrastructure/
│   │   │   └── api/
│   │   └── users/
│   │       └── ...
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # 全局配置
│   │   ├── database.py               # 数据库连接
│   │   ├── events.py                 # 事件总线
│   │   ├── exceptions.py             # 全局异常
│   │   ├── logging.py                # 日志配置
│   │   └── security.py               # 认证授权
│   └── main.py                       # 应用入口
├── tests/
│   ├── unit/
│   │   ├── evaluation/
│   │   ├── documents/
│   │   └── retrieval/
│   ├── integration/
│   └── e2e/
├── alembic/                          # 数据库迁移
├── docs/
├── scripts/
├── docker/
├── pyproject.toml
└── README.md
```

---

## 五、决策矩阵

### 5.1 评标系统评估

| 评估维度 | 分层单体 | 模块化单体 | 推荐 |
|----------|----------|------------|------|
| **业务复杂度** | 中等 | 高 | ⭐ 模块化单体 |
| **团队规模** | 2-5 人 | 5-20 人 | ⭐ 模块化单体 |
| **领域边界清晰度** | 模糊 | 清晰（DDD） | ⭐ 模块化单体 |
| **独立测试需求** | 低 | 高 | ⭐ 模块化单体 |
| **未来演进需求** | 低 | 高（可拆微服务） | ⭐ 模块化单体 |
| **开发速度** | 快 | 中等 | 分层单体 |
| **运维复杂度** | 低 | 低 | 相同 |
| **学习曲线** | 低 | 中等 | 分层单体 |

### 5.2 最终建议

| 决策项 | 选择 | 理由 |
|--------|------|------|
| **架构模式** | **模块化单体** | 业务复杂度高，限界上下文清晰，便于团队分工 |
| **组织方式** | 按领域（模块） | 评标、文档、检索、合规等模块独立 |
| **分层策略** | 四层架构 | Domain → Application → Infrastructure → API |
| **通信方式** | 内存事件总线 | 模块解耦，未来可切换到消息队列 |
| **部署方式** | 单一服务 | Docker 容器，简化运维 |

---

## 六、实施建议

### 6.1 模块边界约束

使用 `import-linter` 强制模块边界：

```toml
# pyproject.toml
[tool.importlinter]
root_packages = ["src"]

[[tool.importlinter.contracts]]
name = "Modules must not depend on each other's internals"
type = "forbidden"
source_modules = ["src.modules.evaluation"]
forbidden_modules = ["src.modules.documents.infrastructure"]
```

### 6.2 演进路径

```
Phase 1: 模块化单体（当前）
    ↓
    • 建立清晰的模块边界
    • 实现事件总线
    • 每个模块独立测试
    ↓
Phase 2: 性能优化（6-12 月）
    ↓
    • 识别热点模块
    • 优化检索模块（如需要）
    • 考虑缓存策略
    ↓
Phase 3: 按需拆分（12+ 月）
    ↓
    • 如需要，将高频模块拆为微服务
    • 保持低频模块在单体中
```

---

## 七、参考资料

**架构模式：**
- [FastAPI Project Structure](https://github.com/brianobot/fastAPI_project_structure)
- [FastAPI Boilerplate](https://github.com/teamhide/fastapi-boilerplate)
- [Python DDD 实战](https://gitcode.com/gh_mirrors/py/python-ddd)

**行业研究：**
- [2025 DDD 实践要点](https://www.01xitong.com/jiaocheng/143272.html)
- [AI 系统架构设计实战](https://m.blog.csdn.net/2502_91678797/article/details/150950493)
- [从单体到微服务演进](https://m.blog.csdn.net/2501_91590464/article/details/149989433)

**官方文档：**
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Context7 FastAPI Boilerplate](https://benavlabs.github.io/FastAPI-boilerplate/)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
