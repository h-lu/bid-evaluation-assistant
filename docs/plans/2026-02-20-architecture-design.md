# 辅助评标专家系统 —— 端到端架构设计

> 版本：v5.2
> 设计日期：2026-02-20
> 更新日期：2026-02-20
> 状态：已批准

---

## 〇、研究来源说明

本设计参考了以下 GitHub 项目的深入研究：

### 〇.0 核心技术来源

| 项目 | Star | 可信度 | 研究重点 | 借鉴/使用方式 |
|------|------|--------|----------|---------------|
| **LightRAG** | 30k+ | ⭐⭐⭐⭐⭐ | 轻量级知识图谱 RAG | **直接使用** - 双层检索、知识图谱增强 |
| **RAG-Anything** | 1k+ | ⭐⭐⭐⭐⭐ | 多模态 RAG 框架 | **借鉴设计** - 多模态处理、内容分类 |
| **Agentic-Procure-Audit-AI** | - | ⭐⭐⭐ | Agent架构、评分算法 | 借鉴设计 - RGSG工作流、评分可解释性 |
| **RAGFlow** | 35k+ | ⭐⭐⭐⭐⭐ | 文档解析、RAG架构 | 借鉴设计 - 解析器注册表、位置追踪 |
| **DSPy** | 20k+ | ⭐⭐⭐⭐⭐ | Prompt 优化 | **直接使用** - 评分模型自动优化 |
| **Docling** | 42k+ | ⭐⭐⭐⭐⭐ | 多格式文档解析 | **直接使用** - Word/Excel 解析 |
| **LangGraph** | 40k+ | ⭐⭐⭐⭐⭐ | Agent 工作流编排 | **直接使用** - Evaluator-Optimizer、interrupt |
| **Yuxi-Know** | ~10 | ⭐⭐ | 知识库平台 | **谨慎参考** - 社区验证不足 |

> ⚠️ **重要**: Yuxi-Know 虽然技术栈与我们相似，但 Star 数仅约 10+，社区验证不足，需谨慎参考其设计。详见 `docs/research/2026-02-20-yuxi-know-vs-rag-anything-analysis.md`

### 〇.0.1 v5.2 新增研究来源（2026-02-20）

> **来源文档**: `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md`

| 项目 | Star | 可信度 | 借鉴内容 | 本文档应用章节 |
|------|------|--------|----------|----------------|
| **yibiao-simple** | 中 | ⭐⭐⭐⭐ | 招标文件解析、目录生成 | 3.1 文档解析模块 |
| **ProposalLLM** | 低 | ⭐⭐⭐ | 点对点应答格式、需求对应表 | **3.4.1 评标报告格式** ⭐新增 |
| **kotaemon** | 高 | ⭐⭐⭐⭐⭐ | LightRAG集成、高级溯源引用 | **3.5 溯源引用展示** ⭐新增 |
| **RAGFlow** | 非常高 | ⭐⭐⭐⭐⭐ | MinerU集成、模板化分块 | 3.1 文档解析模块 |
| **RAGAS** | 高 | ⭐⭐⭐⭐⭐ | RAG评估框架 | 6.2 评估指标 |
| **RAGChecker** | 高 | ⭐⭐⭐⭐⭐ | 三层诊断、幻觉检测 | **6.2.1 细粒度诊断** ⭐新增 |

详细研究报告见：
- `docs/research/2026-02-20-architecture-pattern-research.md` ⭐ 架构模式选型
- `docs/research/2026-02-20-end-to-end-design-research.md` ⭐ 端到端设计研究
- `docs/research/2026-02-20-yuxi-know-vs-rag-anything-analysis.md` ⭐ **新增** Yuxi-Know vs RAG-Anything 对比分析
- `docs/research/2026-02-20-mineru-github-projects.md` ⭐ **新增** MinerU 相关项目研究
- `docs/research/2026-02-20-mineru-output-processing.md` ⭐ **新增** MinerU 输出处理研究
- `docs/research/2026-02-20-lightrag-research.md`
- `docs/research/2026-02-20-agentic-procure-audit-ai-research.md`
- `docs/research/2026-02-20-ragflow-research.md`
- `docs/research/2026-02-20-github-projects-round2.md`

---

## 〇.1 版本更新要点

### v5.2 更新要点（2026-02-20）

> **来源文档**: `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md`

基于 6 个新 GitHub 项目研究，本版本新增：

| 更新项 | 来源项目 | 说明 |
|--------|----------|------|
| **点对点应答格式** | ProposalLLM | 评标报告核心输出格式：要求 vs 响应对照表 → 详见 **3.4.1** |
| **高级溯源引用展示** | kotaemon | PDF 查看器 + bbox 高亮实现方案 → 详见 **3.5** |
| **RAGChecker 三层诊断** | Amazon RAGChecker | 细粒度评估：Overall/Retriever/Generator → 详见 **6.2.1** |
| **研究来源表扩展** | 6个新项目 | 明确标注来源，便于后续验证 → 详见 **〇.0.1** |

### v5.1 更新要点

基于 Yuxi-Know 与 RAG-Anything 对比研究，本版本更新：

| 更新项 | 说明 |
|--------|------|
| **多模态处理** | 借鉴 RAG-Anything 的图片/表格/公式分类处理模式 |
| **图谱存储决策** | 使用 LightRAG 内置图谱，**不采用 Neo4j**（避免过度设计） |
| **向量库决策** | 使用 ChromaDB，**不采用 Milvus**（文档量不大时更轻量） |
| **Yuxi-Know 评估** | Star 仅 10+，**谨慎参考**，不采用其完整微服务架构 |
| **MinerU 输出处理** | 使用 content_list.json + 位置信息保留方案 |

v5.0 要点保留：
| 更新项 | 说明 |
|--------|------|
| **架构模式** | 模块化单体（按领域划分） |
| **四层架构** | Domain → Application → Infrastructure → API |
| **三路检索协作** | Vector + SQL + Graph 三路检索架构 |
| **Evaluator-Optimizer** | 评分迭代优化模式 |
| **Human-in-the-Loop** | interrupt 机制实现人工审核 |
| **分块策略优化** | 512 token + 15-20% overlap 黄金配置 |

### 〇.2 关键技术决策（基于研究验证）

| 决策项 | 选择 | 不选择 | 理由 |
|--------|------|--------|------|
| **图谱存储** | LightRAG 内置 | ~~Neo4j~~ | 评标场景不需要重量级图数据库 |
| **向量数据库** | ChromaDB | ~~Milvus~~ | 文档量不大，轻量方案更合适 |
| **工作流编排** | LangGraph | - | 适合评标复杂流程 |
| **文档解析** | MinerU + Docling | - | 复杂PDF用MinerU，Office用Docling |
| **架构风格** | 模块化单体 | ~~微服务~~ | 运维简单，可演进 |
| **Yuxi-Know 设计** | 部分借鉴 | ~~完全采用~~ | 社区验证不足，需谨慎 |

---

## 一、设计概览

### 1.1 项目定位

**辅助评标专家系统** 是一个基于 Agentic RAG 架构的医疗器械招投标智能助手，定位为"AI辅助 + 专家决策"的人机协作系统。

**核心价值：**
- 投标文件智能解析（MinerU）
- 合规性自动审查（资格审查 + 符合性审查）
- 智能评分建议（客观分计算 + 主观分建议）
- 可解释性输出（评分依据 + 原文溯源）

### 1.2 设计约束

| 约束项 | 决策 |
|--------|------|
| **部署环境** | 混合部署，LLM支持API/本地切换 |
| **用户群体** | 多用户群体（评标专家 + 招标代理） |
| **MVP优先级** | 单个评标全流程 |
| **前端技术** | Vue3 + Element Plus |

### 1.3 技术选型（2026最佳实践）

| 层级 | 技术选型 | 说明 | 决策依据 |
|------|----------|------|----------|
| **文档解析** | MinerU 2.5 + Docling | PDF/Word/Excel全覆盖 | RAG-Anything 模式 |
| **RAG 框架** | **LightRAG** ⭐ | 双层检索 + 内置知识图谱 | 30k+ stars，学术验证 |
| **Embedding** | BGE-M3 | 多模式（稠密+稀疏+ColBERT） | 行业标准 |
| **向量数据库** | **ChromaDB** ⭐ | 轻量级向量存储 | 不采用Milvus（过度设计） |
| **知识图谱** | **LightRAG 内置** ⭐ | 基于NetworkX | 不采用Neo4j（过度设计） |
| **Reranker** | BGE-Reranker-v2-m3 | 重排序 | 行业标准 |
| **Agent框架** | **LangGraph** ⭐ | 状态机工作流 | Evaluator-Optimizer模式 |
| **Prompt优化** | **DSPy** ⭐ | 自动优化评分 Prompt | 准确率↑40% |
| **LLM** | DeepSeek / Qwen | 按职责分工 | 性价比高 |
| **评估** | RAGAS + DeepEval | RAG评估 | 五步评估闭环 |
| **可观测性** | Langfuse | 私有化部署 | 开源、完整追踪 |
| **后端API** | FastAPI + Pydantic v2 | 异步框架 | 行业标准 |
| **前端** | Vue3 + Element Plus + Pinia | 评标界面 | 企业级UI |

> ⭐ 标记为本版本核心组件

**技术决策说明：**

| 决策 | 选择 | 不选择 | 理由（基于研究） |
|------|------|--------|------------------|
| 图谱存储 | LightRAG 内置 | ~~Neo4j~~ | Yuxi-Know 使用 Neo4j 但社区验证不足；LightRAG 内置图谱足够评标场景 |
| 向量数据库 | ChromaDB | ~~Milvus~~ | 文档量 < 10万时 ChromaDB 更轻量；Milvus 适合大规模生产 |
| 架构风格 | 模块化单体 | ~~微服务~~ | 单一部署单元，运维简单，可演进到微服务 |
| 多模态处理 | 分类处理模式 | - | 借鉴 RAG-Anything：图片/表格/公式独立处理器 |

---

## 二、系统整体架构

### 2.1 架构选型：模块化单体架构（三路检索协作）

> **设计来源**: 2026 企业级 RAG 最佳实践 + DDD 领域驱动设计
> **详细研究**: `docs/research/2026-02-20-architecture-pattern-research.md`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     系统整体架构 v4.0（三路检索协作版）                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    前端层 (Vue3 + Element Plus)                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ 项目管理  │  │ 评审工作台│  │ 供应商图谱│  │ 报告导出  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │ HTTP/WebSocket                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    API网关层 (FastAPI)                                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ JWT鉴权   │  │ 限流控制  │  │ 审计日志  │  │ API文档   │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         业务服务层                                    │   │
│  │                                                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │              文档解析 Service (MinerU + Docling)               │   │   │
│  │  │  PDF ──→ MinerU    Word/Excel ──→ Docling    扫描件 ──→ OCR   │   │   │
│  │  │         ↓                ↓                    ↓              │   │   │
│  │  │  Chunks (512 token, 15% overlap) + 位置信息 + 结构化数据      │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                │                                    │   │
│  │                                ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │              三路检索协作 (Retrieval Coordinator)              │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │   │   │
│  │  │  │Vector检索   │  │  SQL检索    │  │ Graph检索   │           │   │   │
│  │  │  │(LightRAG)   │  │ (结构化数据) │  │(知识图谱)   │           │   │   │
│  │  │  │语义理解     │  │ 精确查询    │  │ 关系追溯    │           │   │   │
│  │  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │   │   │
│  │  │         │                │                │                  │   │   │
│  │  │         └────────────────┼────────────────┘                  │   │   │
│  │  │                          ▼                                    │   │   │
│  │  │                   ┌─────────────┐                            │   │   │
│  │  │                   │   Reranker  │  ← BGE-Reranker-v2         │   │   │
│  │  │                   └──────┬──────┘                            │   │   │
│  │  └──────────────────────────┼───────────────────────────────────┘   │   │
│  │                             │ 统一检索结果                           │   │
│  │                             ▼                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │              Agent 编排 Service (LangGraph)                    │   │   │
│  │  │                                                               │   │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐  │   │   │
│  │  │  │  Evaluator-Optimizer 工作流                              │  │   │   │
│  │  │  │  Generate → Evaluate → [置信度检查] → Accept/Refine    │  │   │   │
│  │  │  │                          ↓                              │  │   │   │
│  │  │  │                   Human-in-the-Loop                      │  │   │   │
│  │  │  │                   (interrupt 机制)                       │  │   │   │
│  │  │  └─────────────────────────────────────────────────────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                │ 评分结果                             │   │
│  │                                ▼                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │              评分 Service (DSPy 优化) ⭐                        │   │   │
│  │  │  MIPROv2 自动优化 → 评分准确率 ↑40%，成本 ↓35%                 │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         基础设施层                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ LLM抽象层 │  │ ChromaDB │  │PostgreSQL│  │  Redis   │            │   │
│  │  │(可切换)  │  │ (向量库) │  │(关系+SQL)│  │ (缓存)   │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │   │
│  │  │ NetworkX │  │ ~~Neo4j~~│  │ Langfuse │  ← 可观测性              │   │
│  │  │(LightRAG│  │  不采用   │  │ (监控)   │                          │   │
│  │  │内置图谱)│  │          │  │          │                          │   │
│  │  └──────────┘  └──────────┘  └──────────┘                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**架构亮点：**
- **三路检索协作**: Vector（语义）+ SQL（精确）+ Graph（关系）
- **Evaluator-Optimizer**: 评分迭代优化，置信度低自动补充检索
- **Human-in-the-Loop**: interrupt 机制实现人工审核介入
- **DSPy + LangGraph**: 黄金组合，准确率 ↑40%，成本 ↓35%

### 2.2 选型理由：为什么选择模块化单体

| 维度 | 分层单体 | 微服务 | 模块化单体 ⭐ |
|------|----------|--------|---------------|
| **复杂度** | ✅ 低 | ❌ 高 | ⚠️ 中 |
| **开发速度** | ✅ 快 | ❌ 慢 | ⚠️ 中 |
| **MVP适配** | ✅ 高 | ❌ 低 | ✅ 高 |
| **运维成本** | ✅ 低 | ❌ 高 | ✅ 低 |
| **可演进性** | ⚠️ 中 | ✅ 高 | ✅ 高 |
| **模块边界** | ❌ 模糊 | ✅ 清晰 | ✅ 清晰（DDD） |
| **独立测试** | ❌ 难 | ✅ 易 | ✅ 易 |
| **团队分工** | ⚠️ 共享 | ✅ 独立 | ✅ 模块所有权 |

**选择模块化单体的核心原因：**
1. **业务复杂度高**：评标系统包含多个限界上下文（评标、文档、检索、合规）
2. **清晰的模块边界**：便于团队分工和独立测试
3. **单一部署单元**：运维简单，避免分布式复杂性
4. **可演进到微服务**：需要时可按模块拆分

### 2.3 模块划分（按领域）

```
src/modules/
├── evaluation/           # 评标核心模块
│   └── 职责：评分计算、报告生成、人工审核流程
├── documents/            # 文档管理模块
│   └── 职责：上传、解析、分块、存储
├── retrieval/            # RAG 检索模块
│   └── 职责：向量检索、图谱查询、重排序
├── compliance/           # 合规审查模块
│   └── 职责：资质校验、合规检测、风险预警
├── workflow/             # 工作流编排模块
│   └── 职责：LangGraph 编排、状态管理
└── users/                # 用户管理模块
    └── 职责：认证、授权、审计日志
```

### 2.4 模块内部结构（四层架构）

每个模块遵循四层架构：

```
src/modules/evaluation/
├── domain/                  # 领域层（纯 Python，无框架依赖）
│   ├── entities.py          # 实体：BidEvaluation, Score, Report
│   ├── value_objects.py     # 值对象：Confidence, Criterion, Evidence
│   └── events.py            # 领域事件：ScoreCalculated, ReviewRequested
├── application/             # 应用层（编排）
│   ├── services.py          # 应用服务
│   ├── commands.py          # 命令：CalculateScoreCommand
│   └── queries.py           # 查询：GetEvaluationQuery
├── infrastructure/          # 基础设施层（外部依赖）
│   ├── repositories.py      # 仓储实现
│   ├── adapters.py          # 外部服务适配器（LangGraph, DSPy）
│   └── models.py            # ORM 模型
└── api/                     # 接口层
    ├── router.py            # FastAPI 路由
    └── schemas.py           # Pydantic 模型
```

---

## 三、核心模块设计

### 3.1 文档解析模块（解析器注册表模式）

> **设计来源**: RAGFlow 解析器架构 + RAG-Anything 多模态处理
> **详细研究**: `docs/research/2026-02-20-mineru-output-processing.md`

```
┌─────────────────────────────────────────────────────────────┐
│                    文档解析模块                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   PDF/图片/Word输入                                          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │          Parser Registry (解析器注册表)      │          │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │          │
│   │  │ MinerU  │ │ Docling │ │PaddleOCR│       │          │
│   │  │(复杂PDF)│ │(Office) │ │(扫描件) │       │          │
│   │  └─────────┘ └─────────┘ └─────────┘       │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │   MinerU 输出处理 (content_list.json)        │          │
│   │  ┌────────────────────────────────────────┐ │          │
│   │  │ • 保留位置信息 (page_idx, bbox)         │ │          │
│   │  │ • 内容类型分类 (text/table/image/formula)│ │          │
│   │  │ • 标题层级提取 (section, heading_path)  │ │          │
│   │  └────────────────────────────────────────┘ │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │   多模态内容处理器 (借鉴 RAG-Anything)        │          │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │          │
│   │  │  Text   │ │  Table  │ │  Image  │       │          │
│   │  │Processor│ │Processor│ │Processor│       │          │
│   │  └─────────┘ └─────────┘ └─────────┘       │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │          Chunker (结构感知分块器)             │          │
│   │  ┌────────────────────────────────────────┐ │          │
│   │  │ • 512 token + 15-20% overlap           │ │          │
│   │  │ • 保留位置追踪 (add_positions)          │ │          │
│   │  │ • 标题层级保留 (heading_path)          │ │          │
│   │  └────────────────────────────────────────┘ │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │  Chunk 输出结构（用于溯源引用）               │          │
│   │  {                                          │          │
│   │    "id": "chunk_xxx",                       │          │
│   │    "content": "文本内容...",                │          │
│   │    "metadata": {                            │          │
│   │      "pages": [1, 2],                       │ ← 溯源引用│
│   │      "positions": [{"page":1,"bbox":[...]}],│          │
│   │      "section": "2.2 技术评审标准",         │          │
│   │      "heading_path": ["2.评审","2.2技术"],  │          │
│   │      "chunk_type": "text"                   │          │
│   │    }                                        │          │
│   │  }                                          │          │
│   └─────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**MinerU 输出处理（基于研究）：**

> **关键发现**: JSON (content_list.json) 包含完整位置信息，是溯源的基础

```python
# 来源: docs/research/2026-02-20-mineru-output-processing.md
class MinerUProcessor:
    """MinerU content_list.json 处理器"""

    def process(self, content_list_path: str) -> List[Dict]:
        """
        处理 MinerU 输出，保留位置信息用于溯源

        输出格式包含：
        - pages: 页码列表
        - positions: [{page, bbox}] 位置信息
        - section: 当前章节
        - heading_path: 标题路径
        - chunk_type: 内容类型
        """
        with open(content_list_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # 按页码和位置排序
        sorted_items = sorted(
            items,
            key=lambda x: (x.get('page_idx', 0), x.get('bbox', [0])[1] if x.get('bbox') else 0)
        )

        chunks = []
        current_chunk = self._init_chunk()
        heading_stack = []

        for item in sorted_items:
            text = item.get('text', '').strip()
            if not text:
                continue

            page = item.get('page_idx', 0)
            bbox = item.get('bbox', [0, 0, 0, 0])
            item_type = item.get('type', 'text')

            # 更新标题栈
            if item_type in ['title', 'section_header']:
                heading_stack.append(text)

            # 检查是否需要分块
            if len(current_chunk['content']) + len(text) > self.chunk_size:
                if current_chunk['content']:
                    chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = self._init_chunk(
                    overlap_text=current_chunk['content'][-self.overlap:]
                )

            # 添加内容
            current_chunk['content'] += text + '\n'
            current_chunk['positions'].append({
                'page': page,
                'bbox': bbox,
                'text_len': len(text)
            })
            current_chunk['pages'].add(page)
            current_chunk['heading_stack'] = heading_stack.copy()

        return chunks
```

**解析器注册表模式（策略模式 + 配置驱动）:**

```python
# 设计模式：开闭原则 - 新增解析器只需注册，无需修改现有代码
PARSERS = {
    "mineru": by_mineru,        # MinerU PDF解析（复杂布局）
    "docling": by_docling,      # Word/Excel 解析
    "paddleocr": by_paddleocr,  # 扫描件OCR
}

def chunk(filename: str, parser_id: str = "auto", **kwargs):
    """主入口：根据配置选择解析器"""
    if parser_id == "auto":
        parser_id = auto_detect_parser(filename)
    parser_func = PARSERS.get(parser_id, by_mineru)
    return parser_func(filename, **kwargs)
```

**分块策略（2026最佳实践 - 基于研究验证）：**

> **关键发现**：512 token 比 1024 token 的 MRR 指标高 **12-18%**
> **Overlap 黄金区间**：15-20%（工程实践验证）

| 文档类型 | Chunk Size | Overlap | 切分算法 | 理由 |
|---------|-----------|---------|---------|------|
| **投标文件** | **512 token** | **15-20%** | 结构感知 | 工程黄金配置 |
| 技术参数表 | 按表格 | 0% | 整表切分 | 保持完整性 |
| 产品注册证 | 整页 | N/A | 原子切分 | 原子性文档 |
| 法规条文 | 256-300 token | 15% | 递归字符 | 独立引用 |
| 报价单 | 按行/项 | 0% | 结构感知 | SQL 精确查询 |

### 3.2 RAG检索模块（LightRAG 双层检索 + 知识图谱）

> **核心组件**: LightRAG（pip 安装，直接使用）

**LightRAG 双层检索架构：**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LightRAG 检索模块                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   用户查询（来自 LangGraph Agent）                                           │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    查询模式选择                                       │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │  │
│   │  │   Local     │  │   Global    │  │   Hybrid    │                  │  │
│   │  │  (低层检索)  │  │  (高层检索)  │  │  (混合检索)  │  ← 推荐         │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│       │                                                                     │
│       ├─────────────────────────────────────────────────────────┐          │
│       │                                                         │          │
│       ▼                                                         ▼          │
│   ┌─────────────────────────────┐     ┌─────────────────────────────┐    │
│   │      Low-Level Retrieval    │     │      High-Level Retrieval   │    │
│   │      (低层：具体细节)        │     │      (高层：全局理解)        │    │
│   │                             │     │                             │    │
│   │  • 实体匹配                  │     │  • 主题/概念检索            │    │
│   │  • 关系查询                  │     │  • 社区发现                 │    │
│   │  • 精确属性                  │     │  • 全局摘要                 │    │
│   │                             │     │                             │    │
│   │  示例：                      │     │  示例：                      │    │
│   │  "供应商A的注册资金？"       │     │  "哪家供应商综合实力最强？"  │    │
│   │  "产品X的技术参数？"         │     │  "各供应商的技术方案对比"    │    │
│   └──────────────┬──────────────┘     └──────────────┬──────────────┘    │
│                  │                                   │                    │
│                  └─────────────────┬─────────────────┘                    │
│                                    ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      知识图谱 + 向量检索融合                          │  │
│   │                                                                     │  │
│   │   ┌─────────────┐           ┌─────────────┐                        │  │
│   │   │ Knowledge   │           │   Vector    │                        │  │
│   │   │   Graph     │           │   Search    │                        │  │
│   │   │ (NetworkX)  │           │ (ChromaDB)  │                        │  │
│   │   └──────┬──────┘           └──────┬──────┘                        │  │
│   │          │                         │                                │  │
│   │          └───────────┬─────────────┘                                │  │
│   │                      ▼                                              │  │
│   │              ┌─────────────┐                                        │  │
│   │              │   Reranker  │  ← BGE-Reranker-v2-m3                  │  │
│   │              └──────┬──────┘                                        │  │
│   │                     ▼                                               │  │
│   │              Top-K Context                                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  检索结果（返回给 LangGraph）                                         │  │
│   │  {                                                                  │  │
│   │    "context": "相关文本内容...",                                    │  │
│   │    "entities": ["供应商A", "产品X"],     ← 知识图谱实体              │  │
│   │    "relations": [("供应商A", "生产", "产品X")],  ← 实体关系         │  │
│   │    "sources": [{"doc_id": "...", "page": 5}],  ← 溯源引用           │  │
│   │    "confidence": 0.92                                               │  │
│   │  }                                                                  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**LightRAG 集成代码：**

```python
# backend/src/rag/lightrag_service.py
from lightrag import LightRAG
from lightrag.types import QueryMode

class LightRAGService:
    """LightRAG 检索服务 - 供 LangGraph Agent 调用"""

    def __init__(self, working_dir: str, llm_model: str = "deepseek-chat"):
        self.rag = LightRAG(
            working_dir=working_dir,
            llm_model=llm_model,
            embedding_model="BAAI/bge-m3",
            # 使用我们已有的 ChromaDB
            vector_storage="chromadb",
        )

    async def insert_chunks(self, chunks: list[dict]):
        """插入解析后的文档块（来自 MinerU/Docling）"""
        for chunk in chunks:
            await self.rag.ainsert(
                chunk["content"],
                metadata={
                    "doc_id": chunk.get("doc_id"),
                    "positions": chunk.get("positions"),
                }
            )

    async def retrieve(
        self,
        query: str,
        mode: QueryMode = QueryMode.HYBRID
    ) -> dict:
        """检索接口 - 供 LangGraph Retrieve 节点调用"""
        result = await self.rag.aquery(query, mode=mode)
        return {
            "context": result.context,
            "entities": result.entities,
            "relations": result.relations,
            "sources": result.sources,
            "confidence": result.confidence,
        }

    async def get_supplier_graph(self, supplier_name: str) -> dict:
        """获取供应商知识图谱（可视化用）"""
        return await self.rag.aget_entity_graph(supplier_name)
```

**检索模式选择指南：**

| 模式 | 适用场景 | 示例查询 |
|------|----------|----------|
| **Local** | 查询具体实体、精确信息 | "供应商A的注册资金是多少？" |
| **Global** | 全局理解、对比分析 | "各供应商的技术方案有何差异？" |
| **Hybrid** | 综合查询（推荐） | "评估供应商A的综合实力" |

**知识图谱在评标中的应用：**

```
供应商关系图谱示例：

     ┌─────────────┐
     │   供应商A   │
     └──────┬──────┘
            │
    ┌───────┼───────┐
    │       │       │
    ▼       ▼       ▼
┌───────┐ ┌───────┐ ┌───────┐
│ 产品X │ │ 产品Y │ │ 资质Z │
│价格:1万│ │价格:2万│ │ISO9001│
└───────┘ └───────┘ └───────┘
    │
    ▼
┌───────────────┐
│ 技术参数表     │
│ 精度: 0.01mm  │
│ 功率: 500W    │
└───────────────┘
```

**与 Yuxi-Know 方案对比：**

| 方面 | Yuxi-Know 方案 | 我们的方案 | 说明 |
|------|----------------|------------|------|
| **图谱存储** | Neo4j（重量级） | LightRAG 内置（NetworkX） | 不需要额外部署 |
| **向量存储** | Milvus（重量级） | ChromaDB（轻量） | 文档量不大时更合适 |
| **工作流** | LangGraph | LangGraph | 相同 |
| **RAG 引擎** | LightRAG | LightRAG | 相同 |
| **可信度** | ⭐⭐（10+ stars） | ⭐⭐⭐⭐⭐（30k+ stars） | 优先参考 LightRAG 官方 |

> **重要决策**: Yuxi-Know 虽然技术栈相似，但社区验证不足（~10 stars），其 Neo4j + Milvus 架构过于复杂，不适合当前阶段。

### 3.3 多Agent模块（Evaluator-Optimizer + Human-in-the-Loop）

> **设计来源**: LangGraph 官方模式 + 2026 最佳实践

**核心模式：Evaluator-Optimizer（评估-优化循环）**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              LangGraph 状态机工作流 (Evaluator-Optimizer 模式)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   StateGraph<BidEvaluationState>                                           │
│                                                                             │
│   ┌─────────┐                                                               │
│   │ START   │                                                               │
│   └────┬────┘                                                               │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  三路检索 (Retrieve Node)                                           │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│   │  │Vector检索   │  │  SQL检索    │  │ Graph检索   │                │   │
│   │  │LightRAG    │  │ PostgreSQL  │  │ NetworkX    │                │   │
│   │  │语义理解    │  │ 精确数据    │  │ 关系追溯    │                │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                │   │
│   │                         ↓ RRF融合 + Rerank                         │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Generator Node (生成器)                                            │   │
│   │  • 合规审查生成                                                     │   │
│   │  • 技术评分生成                                                     │   │
│   │  • 商务评分生成                                                     │   │
│   │  使用 DSPy 优化后的 Prompt                                          │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Evaluator Node (评估器)                                            │   │
│   │  • 评估置信度 (confidence)                                          │   │
│   │  • 检查评分完整性                                                   │   │
│   │  • 验证证据链                                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ├──────────────────────────────────────────────────────────┐        │
│        │                                                          │        │
│        ▼                                                          ▼        │
│   ┌─────────────┐                                      ┌─────────────────┐  │
│   │ 置信度 ≥0.75│                                      │  置信度 < 0.75  │  │
│   │   Accept    │                                      │    Refine       │  │
│   └──────┬──────┘                                      └────────┬────────┘  │
│          │                                                      │          │
│          │                                               ┌──────▼──────┐   │
│          │                                               │ 补充检索     │   │
│          │                                               │ iteration++ │   │
│          │                                               │ (最多3次)   │   │
│          │                                               └──────┬──────┘   │
│          │                                                      │          │
│          │                    ┌─────────────────────────────────┘          │
│          │                    │                                             │
│          │                    ▼                                             │
│          │            ┌─────────────────────────────────────────────────┐   │
│          │            │  Human-in-the-Loop (interrupt 机制) ⭐          │   │
│          │            │  触发条件:                                      │   │
│          │            │  • 置信度 < 0.75                                │   │
│          │            │  • 合规审查不通过                               │   │
│          │            │  • 评分偏离 > 20%                               │   │
│          │            │  • 异常行为检测                                 │   │
│          │            └─────────────────────────────────────────────────┘   │
│          │                    │                                             │
│          │                    ├────────────────┐                            │
│          │                    ▼                ▼                            │
│          │              ┌──────────┐    ┌─────────────┐                    │
│          │              │ 人工确认  │    │ 人工修改评分 │                    │
│          │              │ resume() │    │ 修改后继续  │                    │
│          │              └────┬─────┘    └──────┬──────┘                    │
│          │                   │                 │                            │
│          └───────────────────┼─────────────────┘                            │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Report Generator (报告生成)                                        │   │
│   │  • 评分汇总                                                         │   │
│   │  • 证据溯源                                                         │   │
│   │  • 可视化图表                                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────┐                                                               │
│   │   END   │                                                               │
│   └─────────┘                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Human-in-the-Loop 实现代码：**

```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

class BidEvaluationState(TypedDict):
    # ... 其他字段
    requires_human_review: bool
    human_feedback: str

def evaluator_node(state: BidEvaluationState) -> dict:
    """评估器：判断是否需要人工审核"""
    confidence = state.get("confidence", 0)

    # 触发人工审核的条件
    triggers = []
    if confidence < 0.75:
        triggers.append("置信度过低")
    if state.get("compliance_passed") == False:
        triggers.append("合规审查未通过")
    if state.get("score_deviation", 0) > 20:
        triggers.append("评分偏离过大")

    requires_review = len(triggers) > 0

    if requires_review:
        # 使用 interrupt 暂停流程，等待人工输入
        feedback = interrupt(
            f"需要人工审核，原因：{', '.join(triggers)}\n"
            f"当前评分：{state.get('total_score')}\n"
            f"请确认或提供修改建议："
        )
        return {
            "requires_human_review": True,
            "human_feedback": feedback
        }

    return {"requires_human_review": False}

# 构建工作流
builder = StateGraph(BidEvaluationState)
builder.add_node("evaluator", evaluator_node)
# ... 添加其他节点

# 使用 checkpointer 支持中断恢复
graph = builder.compile(checkpointer=InMemorySaver())

# 调用方式
config = {"configurable": {"thread_id": "bid-001"}}
result = graph.invoke(initial_state, config)  # 可能暂停在 interrupt

# 人工审核后继续
if result.get("__interrupt__"):
    result = graph.invoke(Command(resume="确认通过"), config)
```

```python
from typing import Annotated, TypedDict

def add_lists(left: list, right: list) -> list:
    """列表累积函数"""
    return left + right

class BidEvaluationState(TypedDict, total=False):
    # 输入
    tender_id: str
    bid_documents: list[dict]

    # RGSG 检索结果
    retrieved_chunks: list[dict]
    web_search_results: list[dict]

    # 累积字段（自动追加）- 使用 Annotated[list, add_lists]
    reasoning_steps: Annotated[list[str], add_lists]   # 推理步骤追踪
    search_queries: Annotated[list[str], add_lists]    # 搜索历史
    citations: Annotated[list[dict], add_lists]        # 引用来源

    # RGSG 决策字段
    grade_decision: str        # "sufficient" | "needs_search"
    relevance_score: float     # 0.0-1.0
    iteration: int             # 当前迭代次数

    # 评分（含可解释性）
    technical_score: ScoreWithReasoning
    total_score: ScoreWithReasoning

    # 控制
    max_iterations: int
    errors: Annotated[list[str], add_lists]
```

**Agent职责分工：**

| Agent | 职责 | LLM选择 | 原因 |
|-------|------|---------|------|
| Supervisor | 任务协调 | DeepSeek | 推理能力强 |
| Compliance | 合规审查 | Qwen-Turbo | 规则明确 |
| Technical | 技术评审 | Qwen-Max | 深度分析 |
| Commercial | 商务评审 | Qwen-Turbo | 计算型 |
| Reviewer | 终审评估 | DeepSeek | 综合推理 |

### 3.4 评分可解释性设计

> **设计来源**: Agentic-Procure-Audit-AI 评分算法

**核心原则**: 每个评分必须包含 **score + reasoning + evidence** 三元组，确保AI决策透明可审计。

```python
class ScoreWithReasoning(TypedDict):
    """评分结果（含可解释性）"""
    score: float              # 分数 0-100
    reasoning: str            # 评分理由（为什么给这个分）
    evidence: list[str]       # 证据来源（标书原文引用）
    confidence: float         # 置信度 0-1
```

**多维度评分框架（四维评分）：**

| 维度 | 权重 | 评估内容 | 评分依据 |
|------|------|----------|----------|
| **技术能力** | 35% | 技术方案、产品参数、创新性 | 技术参数表、产品注册证 |
| **商务条件** | 25% | 价格、付款条款、交货期 | 报价单、商务条款 |
| **资质信誉** | 25% | 企业资质、业绩、认证 | 营业执照、资质证书、业绩证明 |
| **风险因素** | 15% | 供应链风险、合规风险 | 信用报告、历史表现 |

**LLM 驱动的评分实现：**

```python
async def grade_supplier(
    supplier_name: str,
    bid_data: dict,
    web_research: list[dict] = None
) -> ScoreWithReasoning:
    """
    LLM 驱动的供应商评分（带可解释性）
    """
    prompt = f"""
    作为医疗器械评标专家，请对以下供应商进行评分。

    供应商: {supplier_name}
    投标数据: {json.dumps(bid_data, ensure_ascii=False)}
    补充信息: {json.dumps(web_research, ensure_ascii=False)}

    请输出 JSON 格式：
    {{
        "technical_score": <0-100>,
        "technical_reasoning": "<评分理由，详细说明为什么给这个分数>",
        "technical_evidence": ["<证据1：标书第X页>", "<证据2：...>"],

        "commercial_score": <0-100>,
        "commercial_reasoning": "<评分理由>",
        "commercial_evidence": ["<证据列表>"],

        "qualification_score": <0-100>,
        "qualification_reasoning": "<评分理由>",
        "qualification_evidence": ["<证据列表>"],

        "risk_score": <0-100>,
        "risk_reasoning": "<评分理由>",
        "risk_evidence": ["<证据列表>"],

        "overall_assessment": "<综合评价>",
        "recommendation": "<APPROVED / REVIEW / REJECTED>"
    }}
    """

    result = await llm.ainvoke(prompt)
    return parse_score_result(result)
```

**推荐决策逻辑：**

| 总分区间 | 推荐结果 | 说明 |
|----------|----------|------|
| ≥ 70 | APPROVED | 推荐中标 |
| 50-69 | REVIEW | 需要进一步审查 |
| < 50 | REJECTED | 不推荐 |

### 3.4.1 评标报告输出格式（点对点应答）⭐ v5.2 新增

> **来源**: ProposalLLM - `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md` 第 3.2 节
> **借鉴价值**: ⭐⭐⭐⭐⭐ 评标报告核心格式，每个评分项必须有"要求 vs 响应"对照

**核心原则**: 评标报告采用**点对点应答格式**，每项评分必须有：
1. 招标要求（来自招标文件）
2. 投标响应（来自投标文件）
3. 符合度判定（完全符合/部分符合/不符合）
4. 评分 + 评分理由

**报告格式定义：**

```python
# 来源: ProposalLLM 点对点应答模式
from typing import List, Literal
from pydantic import BaseModel

class PointToPointItem(BaseModel):
    """点对点应答项"""
    criterion_id: str                    # 评分项ID
    criterion_name: str                  # 评分项名称
    requirement: str                     # 招标要求（原文）
    requirement_source: str              # 来源：招标文件第X页
    response: str                        # 投标响应（原文）
    response_source: str                 # 来源：投标文件第X页
    compliance_status: Literal["full", "partial", "none"]  # 符合度
    score: float                         # 得分
    max_score: float                     # 满分
    reasoning: str                       # 评分理由
    evidence: List[str]                  # 证据列表

class BidEvaluationReport(BaseModel):
    """评标报告（点对点应答格式）"""
    tender_id: str
    supplier_name: str
    evaluation_date: str

    # 资格审查
    qualification_items: List[PointToPointItem]
    qualification_score: float
    qualification_passed: bool

    # 符合性审查
    compliance_items: List[PointToPointItem]
    compliance_score: float
    compliance_passed: bool

    # 技术评分
    technical_items: List[PointToPointItem]
    technical_score: float
    technical_max: float

    # 商务评分
    commercial_items: List[PointToPointItem]
    commercial_score: float
    commercial_max: float

    # 综合结论
    total_score: float
    recommendation: str
    key_findings: List[str]
    risk_alerts: List[str]
```

**报告展示示例：**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           评标报告（点对点应答格式）                                   │
│                    来源: ProposalLLM 点对点应答模式                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  一、资格审查                                                                       │
│  ┌────┬──────────────┬────────────────┬────────────────┬────────┬───────┬────────┐ │
│  │序号│  评审项       │   招标要求      │   投标响应      │ 符合度 │ 得分  │ 理由   │ │
│  ├────┼──────────────┼────────────────┼────────────────┼────────┼───────┼────────┤ │
│  │ 1  │ 注册资本      │ ≥1000万元      │ 5000万元        │ ✓完全 │ 10/10 │ 超出要求│ │
│  │    │              │[招标文件P5]    │[投标文件P12]    │        │       │        │ │
│  ├────┼──────────────┼────────────────┼────────────────┼────────┼───────┼────────┤ │
│  │ 2  │ 营业执照      │ 有效期内        │ 有效至2030年    │ ✓完全 │ 10/10 │ 符合   │ │
│  │    │              │[招标文件P5]    │[投标文件P10]    │        │       │        │ │
│  ├────┼──────────────┼────────────────┼────────────────┼────────┼───────┼────────┤ │
│  │ 3  │ ISO9001认证   │ 有效期内        │ 有效至2027年    │ ✓完全 │ 10/10 │ 符合   │ │
│  │    │              │[招标文件P6]    │[投标文件P25]    │        │       │        │ │
│  └────┴──────────────┴────────────────┴────────────────┴────────┴───────┴────────┘ │
│                                                                                     │
│  二、技术评分                                                                       │
│  ┌────┬──────────────┬────────────────┬────────────────┬────────┬───────┬────────┐ │
│  │ 1  │ 产品精度      │ ≤0.01mm        │ 0.005mm        │ ✓完全 │ 15/15 │ 优于要求│ │
│  │    │              │[技术规范P8]    │[技术方案P5]     │        │       │        │ │
│  ├────┼──────────────┼────────────────┼────────────────┼────────┼───────┼────────┤ │
│  │ 2  │ 售后服务      │ 24小时响应     │ 12小时响应      │ ✓完全 │ 10/10 │ 优于要求│ │
│  │    │              │[招标文件P15]   │[服务方案P2]     │        │       │        │ │
│  └────┴──────────────┴────────────────┴────────────────┴────────┴───────┴────────┘ │
│                                                                                     │
│  三、综合结论                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ 总分: 92/100                                                                    ││
│  │ 推荐结果: ✓ APPROVED                                                            ││
│  │ 关键发现:                                                                        ││
│  │   • 技术参数全面优于招标要求                                                     ││
│  │   • 商务报价具有竞争力                                                           ││
│  │   • 资质证书齐全有效                                                             ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**实现要点：**

| 要点 | 说明 |
|------|------|
| **要求来源溯源** | 每项招标要求必须标注来源（招标文件第X页） |
| **响应来源溯源** | 每项投标响应必须标注来源（投标文件第X页） |
| **符合度判定** | 自动判定 + 人工确认：完全符合/部分符合/不符合 |
| **评分可解释** | 每项评分必须有评分理由 |
| **证据链** | 支持点击跳转到原文（配合 3.5 溯源引用展示） |

### 3.5 溯源引用展示（PDF 查看器 + 高亮）⭐ v5.2 新增

> **来源**: kotaemon - `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md` 第 3.3 节
> **借鉴价值**: ⭐⭐⭐⭐⭐ 高级溯源引用，浏览器内 PDF 查看器 + 高亮显示

**功能描述**: 用户点击评标报告中的引用链接时，打开 PDF 查看器并高亮显示引用内容。

**前端架构：**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         溯源引用展示系统                                             │
│                    来源: kotaemon 高级溯源引用                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   评标报告界面                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐  │
│   │ 评分项: 注册资本                                                            │  │
│   │ 投标响应: "注册资本5000万元人民币"  [📄 查看原文] ← 点击                     │  │
│   └─────────────────────────────────────────────────────────────────────────────┘  │
│                                            │                                        │
│                                            ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────────────┐  │
│   │                        PDF 查看器 (侧边栏/弹窗)                              │  │
│   │  ┌─────────────────────────────────────────────────────────────────────┐    │  │
│   │  │  工具栏: [缩放] [翻页] [下载] [关闭]                                │    │  │
│   │  └─────────────────────────────────────────────────────────────────────┘    │  │
│   │  ┌─────────────────────────────────────────────────────────────────────┐    │  │
│   │  │                                                                       │    │  │
│   │  │  ... 营业执照 ...                                                    │    │  │
│   │  │                                                                       │    │  │
│   │  │  ╔══════════════════════════════════════════════════════════════╗    │    │  │
│   │  │  ║  注册资本：5000万元人民币                                    ║    │    │  │
│   │  │  ║  (高亮显示引用内容)                                          ║    │    │  │
│   │  │  ╚══════════════════════════════════════════════════════════════╝    │    │  │
│   │  │                                                                       │    │  │
│   │  │  ... 其他内容 ...                                                    │    │  │
│   │  │                                                                       │    │  │
│   │  └─────────────────────────────────────────────────────────────────────┘    │  │
│   │                                                                               │  │
│   │  页码: 12 / 50        来源: 投标文件-供应商A.pdf                             │  │
│   └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**技术实现：**

```typescript
// 前端实现 (Vue3)
// 来源: kotaemon PDF 查看器 + bbox 高亮

interface CitationLink {
  docId: string;           // 文档ID
  pageNumber: number;      // 页码
  bbox: [number, number, number, number];  // [x0, y0, x1, y1] 边界框
  text: string;            // 引用文本
}

// PDF 查看器组件
const PdfViewerWithHighlight = defineComponent({
  props: {
    citation: CitationLink,  // 溯源引用信息
  },
  setup(props) {
    const pdfContainer = ref<HTMLElement>();

    onMounted(async () => {
      // 1. 加载 PDF (使用 PDF.js)
      const pdf = await pdfjsLib.getDocument(`/api/documents/${props.citation.docId}`);
      const page = await pdf.getPage(props.citation.pageNumber);

      // 2. 渲染 PDF 页面
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      await page.render({ canvasContext: context, viewport }).promise;

      // 3. 添加高亮覆盖层
      const highlightOverlay = createHighlightOverlay(props.citation.bbox, viewport);
      pdfContainer.value.appendChild(highlightOverlay);

      // 4. 滚动到高亮位置
      scrollToHighlight(highlightOverlay);
    });

    return () => h('div', { ref: pdfContainer, class: 'pdf-viewer' });
  }
});

// 高亮覆盖层生成
function createHighlightOverlay(
  bbox: [number, number, number, number],
  viewport: PDFPageViewport
): HTMLElement {
  const [x0, y0, x1, y1] = bbox;
  const overlay = document.createElement('div');
  overlay.className = 'highlight-overlay';
  overlay.style.cssText = `
    position: absolute;
    left: ${viewport.convertToViewportPoint(x0, y0)[0]}px;
    top: ${viewport.convertToViewportPoint(x0, y0)[1]}px;
    width: ${x1 - x0}px;
    height: ${y1 - y0}px;
    background: rgba(255, 235, 59, 0.4);  // 黄色半透明
    border: 2px solid #FFC107;
    pointer-events: none;
  `;
  return overlay;
}
```

**后端 API 设计：**

```python
# 来源: kotaemon 溯源引用 + MinerU bbox 数据
# 文件: backend/src/api/citations.py

from fastapi import APIRouter
from typing import Tuple

router = APIRouter(prefix="/api/v1/citations")

class CitationResponse(BaseModel):
    """溯源引用响应"""
    doc_id: str
    filename: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    text: str
    context: str  # 前后文

@router.get("/{chunk_id}/source")
async def get_citation_source(chunk_id: str) -> CitationResponse:
    """
    获取引用的源文档信息

    数据来源: MinerU content_list.json 中的 bbox 字段
    """
    # 从向量数据库获取 chunk 元数据
    chunk = await vector_store.get(chunk_id)

    # 解析元数据中的位置信息
    positions = chunk.metadata.get("positions", [])
    if not positions:
        raise CitationNotFound(chunk_id)

    # 返回第一个位置（最相关）
    pos = positions[0]
    return CitationResponse(
        doc_id=chunk.metadata["doc_id"],
        filename=chunk.metadata["filename"],
        page_number=pos["page"],
        bbox=pos["bbox"],  # [x0, y0, x1, y1]
        text=chunk.content,
        context=get_surrounding_text(chunk)
    )
```

**关键依赖：**

| 依赖 | 用途 | 说明 |
|------|------|------|
| **PDF.js** | PDF 渲染 | 前端 PDF 查看器核心 |
| **bbox 数据** | 位置定位 | 来自 MinerU content_list.json |
| **坐标转换** | PDF 坐标 → 屏幕坐标 | PDF.js viewport.convertToViewportPoint |

**用户体验流程：**

```
用户点击 [📄 查看原文]
    │
    ▼
前端调用 /api/v1/citations/{chunk_id}/source
    │
    ▼
后端返回 { doc_id, page_number, bbox, text }
    │
    ▼
前端打开 PDF 查看器（侧边栏或弹窗）
    │
    ▼
加载 PDF 并定位到指定页码
    │
    ▼
使用 bbox 绘制高亮覆盖层
    │
    ▼
滚动到高亮位置
```

---

## 四、LLM服务抽象层

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM服务抽象层                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │                  LLM Gateway (统一入口)              │  │
│   │          routing │ load_balancing │ fallback        │  │
│   └─────────────────────────┬───────────────────────────┘  │
│                             │                              │
│   ┌─────────────────────────┼───────────────────────────┐  │
│   │                         │                           │  │
│   ▼                         ▼                           ▼  │
│ ┌──────────┐         ┌──────────┐              ┌──────────┐│
│ │ 云端API  │         │ 本地部署 │              │ 私有化   ││
│ │ Provider │         │ Provider │              │ Provider ││
│ ├──────────┤         ├──────────┤              ├──────────┤│
│ │• DeepSeek│         │• vLLM    │              │• Ollama  ││
│ │• Qwen    │         │• LMStudio│              │• LocalAI ││
│ │• OpenAI  │         │• TensorRT│              │          ││
│ └──────────┘         └──────────┘              └──────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 配置示例

```yaml
# config/llm_config.yaml
providers:
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com
  qwen:
    api_key: ${QWEN_API_KEY}
    base_url: https://dashscope.aliyuncs.com/api/v1
  local_vllm:
    base_url: http://localhost:8000

agent_model_mapping:
  supervisor: deepseek-chat
  compliance: qwen-turbo
  technical: qwen-max
  commercial: qwen-turbo
  reviewer: deepseek-chat
```

---

## 五、Agent配置层（可扩展）

### 5.1 Agent配置结构

```yaml
# config/agents/compliance.yaml
agent:
  name: "compliance_agent"
  display_name: "合规审查专家"
  enabled: true

model:
  provider: "qwen"
  model_id: "qwen-turbo"
  temperature: 0.1
  max_tokens: 4096

system_prompt: |
  你是医疗器械招投标合规审查专家...

tools:
  - name: "search_regulation"
    enabled: true
  - name: "find_in_document"
    enabled: true
  - name: "verify_license"
    enabled: true

output_schema:
  type: "object"
  properties:
    passed: { type: "boolean" }
    items: { type: "array" }
    warnings: { type: "array" }
    confidence: { type: "number" }
```

### 5.2 工作流配置

```yaml
# config/agents/workflow.yaml
workflow:
  name: "bid_evaluation_workflow"
  version: "1.0"

  nodes:
    - id: "start"
      type: "entry"
      next: "compliance"

    - id: "compliance"
      agent: "compliance_agent"
      on_success: "parallel_review"
      on_failure: "report"

    - id: "parallel_review"
      type: "parallel"
      branches: ["technical", "commercial"]
      merge: "reviewer"

    - id: "reviewer"
      agent: "reviewer_agent"
      next: "report"

    - id: "report"
      agent: "report_agent"
      next: "end"

  human_review:
    triggers:
      - condition: "confidence < 0.75"
      - condition: "anomaly_detected == true"
      - condition: "compliance_passed == false"
```

### 5.3 扩展方式

| 操作 | 方式 | 是否需要编码 |
|------|------|-------------|
| 新增简单Agent | 创建YAML文件 | ❌ 不需要 |
| 新增复杂Agent | Python插件 | ✅ 需要 |
| 调整执行顺序 | 修改workflow.yaml | ❌ 不需要 |
| 启用/禁用Agent | enabled: true/false | ❌ 不需要 |

---

## 六、评估监控层（五步评估闭环）

> **设计来源**: 2026 企业级 RAG 评估最佳实践

### 6.1 评估闭环架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          五步评估闭环                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Step 1: 构建高质量测试集                                            │  │
│   │  • 100-200 条人工标注样本                                           │  │
│   │  • 覆盖各类型查询（实体查询、对比查询、总结查询）                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Step 2: 选择评估框架                                                │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│   │  │   RAGAS     │  │  DeepEval   │  │  TruLens    │                │  │
│   │  │ (快速评估)  │  │ (CI/CD集成) │  │ (深度诊断)  │                │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Step 3: 设置监控告警                                                │  │
│   │  • 实时评估集成到业务监控系统                                        │  │
│   │  • 延迟（P95 < 15s）、Token 消耗、成本监控                          │  │
│   │  • 检索相关度、嵌入漂移告警                                         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Step 4: 持续迭代优化                                                │  │
│   │  • 每次代码提交自动运行评估                                          │  │
│   │  • DSPy 自动优化 Prompt                                             │  │
│   │  • A/B 测试对比                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Step 5: 人工校准                                                    │  │
│   │  • 自动化评估与人工标注对比（目标一致性 85%）                        │  │
│   │  • 定期校准测试集                                                   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    └──────────────────┐                    │
│                                                       │                    │
│                                    ◄──────────────────┘                    │
│                                    持续循环                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 RAGAS 评估指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| Context Precision | 检索相关性 | ≥ 0.80 |
| Context Recall | 检索覆盖率 | ≥ 0.85 |
| Faithfulness | 生成忠实度 | ≥ 0.90 |
| Answer Relevancy | 回答相关性 | ≥ 0.85 |

### 6.2.1 RAGChecker 细粒度诊断 ⭐ v5.2 新增

> **来源**: Amazon RAGChecker - `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md` 第 3.6 节
> **借鉴价值**: ⭐⭐⭐⭐⭐ 三层指标诊断，可精确定位 RAG 系统问题

**核心特点**: 三层指标体系，区分检索层和生成层问题

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         RAGChecker 三层指标体系                                       │
│                    来源: Amazon Science RAGChecker                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────┐  │
│   │                    Overall Metrics (整体层)                                  │  │
│   │  • Precision: 73.3% - 答案中正确声明的比例                                  │  │
│   │  • Recall: 62.5% - 正确声明被覆盖的比例                                     │  │
│   │  • F1: 67.3% - 综合指标                                                     │  │
│   └─────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                               │
│                    ┌───────────────┴───────────────┐                              │
│                    ▼                               ▼                              │
│   ┌─────────────────────────────┐   ┌─────────────────────────────────────────┐  │
│   │   Retriever Metrics (检索层) │   │        Generator Metrics (生成层)       │  │
│   ├─────────────────────────────┤   ├─────────────────────────────────────────┤  │
│   │ • Claim Recall: 61.4%       │   │ • Context Utilization: 87.5%            │  │
│   │   检索到的声明覆盖率         │   │   检索上下文的利用率                    │  │
│   │                             │   │                                         │  │
│   │ • Context Precision: 87.5%  │   │ • Noise Sensitivity: 22.5%              │  │
│   │   检索上下文的精确度         │   │   噪声敏感度（越低越好）                │  │
│   │                             │   │                                         │  │
│   │                             │   │ • Hallucination: 4.2%                   │  │
│   │                             │   │   幻觉率（越低越好）⭐                   │  │
│   │                             │   │                                         │  │
│   │                             │   │ • Faithfulness: 70.8%                   │  │
│   │                             │   │   忠实度（基于上下文的程度）            │  │
│   └─────────────────────────────┘   └─────────────────────────────────────────┘  │
│                                                                                     │
│   核心方法: Claim-level Entailment (声明级别蕴含)                                   │
│   将答案拆解为独立声明，逐一验证是否被上下文支持                                    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**诊断流程：**

```python
# 来源: RAGChecker 官方示例
# 文件: backend/src/evaluation/ragchecker.py

from ragchecker import RAGResults, RAGChecker
from typing import Dict, List

class RAGCheckerDiagnosis:
    """RAGChecker 细粒度诊断服务"""

    def __init__(self, evaluator_model: str = "gpt-4o"):
        self.checker = RAGChecker(
            evaluator_model=evaluator_model,
            batch_size=10
        )

    async def diagnose(self, test_cases: List[Dict]) -> Dict:
        """
        运行细粒度诊断

        返回三层指标和优化建议
        """
        # 准备 RAG 结果
        rag_results = RAGResults.from_dict({
            "results": test_cases
        })

        # 运行评估
        metrics = await self.checker.evaluate(rag_results)

        # 生成诊断报告
        diagnosis = {
            "overall_metrics": metrics["overall_metrics"],
            "retriever_metrics": metrics["retriever_metrics"],
            "generator_metrics": metrics["generator_metrics"],
            "recommendations": self._generate_recommendations(metrics)
        }

        return diagnosis

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """根据指标生成优化建议"""
        recommendations = []

        # 检索层诊断
        retriever = metrics["retriever_metrics"]
        if retriever["claim_recall"] < 0.6:
            recommendations.append(
                "⚠️ 检索层: Claim Recall < 60%，建议优化检索策略："
                "\n  - 增加检索 top-k 数量"
                "\n  - 优化查询重写"
                "\n  - 检查 Embedding 质量"
            )

        if retriever["context_precision"] < 0.8:
            recommendations.append(
                "⚠️ 检索层: Context Precision < 80%，建议："
                "\n  - 优化 Reranker 模型"
                "\n  - 调整相似度阈值"
            )

        # 生成层诊断
        generator = metrics["generator_metrics"]
        if generator["hallucination"] > 0.1:
            recommendations.append(
                "🚨 生成层: Hallucination > 10%，严重问题！建议："
                "\n  - 强化 Prompt 约束"
                "\n  - 启用 Grounded Generation"
                "\n  - 检查 LLM 模型选择"
            )

        if generator["context_utilization"] < 0.7:
            recommendations.append(
                "⚠️ 生成层: Context Utilization < 70%，建议："
                "\n  - 优化上下文组织"
                "\n  - 检查上下文长度限制"
            )

        return recommendations
```

**与 RAGAS 组合使用策略：**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         评估框架组合策略                                             │
│                    来源: docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   开发阶段 (RAGAS 快速迭代):                                                        │
│   ┌─────────────────────────────────────────────────────────────────────────────┐  │
│   │  • 每次 CI/CD 自动运行                                                       │  │
│   │  • 基础指标监控: Context Precision, Faithfulness                            │  │
│   │  • 阈值: ≥ 0.80                                                             │  │
│   │  • 耗时: ~30s / 100 样本                                                    │  │
│   └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│   问题诊断 (RAGChecker 细粒度):                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────┐  │
│   │  • 当 RAGAS 指标低于阈值时触发                                               │  │
│   │  • 三层诊断: 精确定位检索层 vs 生成层问题                                    │  │
│   │  • 输出优化建议                                                             │  │
│   │  • 耗时: ~2min / 100 样本                                                   │  │
│   └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│   决策流程:                                                                         │
│                                                                                     │
│   RAGAS 整体评估 ──→ 通过? ──→ ✅ 继续                                            │
│         │                                                                           │
│         └──→ 未通过 ──→ RAGChecker 细粒度诊断                                       │
│                              │                                                      │
│                              ├──→ Retriever 问题 ──→ 优化检索策略                   │
│                              │                                                      │
│                              └──→ Generator 问题 ──→ 优化生成策略                   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**指标阈值参考：**

| 指标层 | 指标名称 | 健康阈值 | 警告阈值 | 危险阈值 |
|--------|----------|----------|----------|----------|
| **Overall** | F1 | ≥ 0.70 | 0.60-0.70 | < 0.60 |
| **Retriever** | Claim Recall | ≥ 0.70 | 0.60-0.70 | < 0.60 |
| **Retriever** | Context Precision | ≥ 0.80 | 0.70-0.80 | < 0.70 |
| **Generator** | Hallucination | < 0.05 | 0.05-0.10 | > 0.10 ⚠️ |
| **Generator** | Faithfulness | ≥ 0.85 | 0.75-0.85 | < 0.75 |
| **Generator** | Context Utilization | ≥ 0.80 | 0.70-0.80 | < 0.70 |

### 6.3 DeepEval评估指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| Hallucination | 幻觉率 | < 0.05 |
| Tool Call Accuracy | 工具调用准确率 | ≥ 0.90 |

### 6.4 可观测性（Langfuse）

```
┌─────────────────────────────────────────────────────────────┐
│                    Langfuse 追踪示例                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   评标请求 #12345                                           │
│   ├── Document Parse (1.2s, 500 tokens)                    │
│   ├── Compliance Agent (3.5s, 2000 tokens)                 │
│   │   ├── LLM Call: qwen-turbo                             │
│   │   ├── Tool: search_regulation                          │
│   │   └── Tool: verify_license                             │
│   ├── Technical Agent (5.2s, 3500 tokens)                  │
│   └── Report Generate (1.0s, 800 tokens)                   │
│   ──────────────────────────────────────────               │
│   Total: 10.9s, 6800 tokens, $0.14                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、安全与合规设计

### 7.1 安全架构

| 层级 | 安全措施 |
|------|----------|
| **网络安全** | HTTPS/TLS 1.3、IP白名单、DDoS防护 |
| **认证授权** | JWT认证、RBAC权限、会话管理 |
| **数据安全** | 敏感数据加密、文件加密(AES-256) |
| **合规审计** | 操作日志全量记录、评标追溯 |

### 7.2 角色权限模型

| 角色 | 权限范围 | 典型操作 |
|------|----------|----------|
| 系统管理员 | 全系统 | 用户管理、系统配置 |
| 招标代理 | 项目管理 | 创建项目、上传文件、分配专家 |
| 评标专家 | 评审操作 | 查看文件、AI辅助评审、提交评分 |
| 监督人员 | 审计监督 | 查看记录、异常预警、审计日志 |

### 7.3 评标合规性保障

**评分偏离预警：**
- 横向偏离 > 20% → 黄色预警
- 纵向偏离 > 30% → 橙色预警
- 极端评分（>95 或 <40）→ 红色预警

**人工审核触发条件：**
- AI置信度 < 0.75
- 合规审查不通过（强制）
- 检测到异常行为
- 评分偏离触发预警

---

## 八、部署架构

### 8.1 Docker Compose部署

> **架构简化**: 不采用 Yuxi-Know 的 Neo4j + Milvus + MinIO 复杂架构，使用轻量化方案

```yaml
version: '3.8'

services:
  # 前端
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - api

  # 后端API
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/bid_eval
      - CHROMA_HOST=chroma
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - chroma
      - redis
    volumes:
      - ./data:/app/data  # 持久化数据

  # PostgreSQL（关系数据 + SQL 检索）
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=bid_eval
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ChromaDB（向量存储 - 轻量方案）
  # 不采用 Milvus：文档量 < 10万时 ChromaDB 足够
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  # Redis（缓存 + 会话）
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Langfuse（可观测性 - 可选）
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/langfuse
    profiles:
      - observability  # 可选启动

volumes:
  postgres_data:
  chroma_data:
```

**与 Yuxi-Know 部署对比：**

| 服务 | Yuxi-Know | 我们的方案 | 说明 |
|------|-----------|------------|------|
| 图数据库 | Neo4j | ~~不部署~~ | LightRAG 内置 NetworkX |
| 向量库 | Milvus | ChromaDB | 轻量化，部署简单 |
| 对象存储 | MinIO | ~~不部署~~ | 本地文件系统足够 |
| 图数据库 | PostgreSQL | PostgreSQL | 相同 |
| 缓存 | - | Redis | 新增缓存层 |

### 8.2 目录结构

```
bid-evaluation-assistant/
├── frontend/                    # Vue3前端
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── stores/              # Pinia状态管理
│   │   └── api/
│   └── package.json
│
├── backend/                     # FastAPI后端
│   ├── src/
│   │   ├── api/                 # API路由
│   │   ├── services/            # 业务服务
│   │   ├── agents/              # Agent定义
│   │   ├── rag/                 # RAG模块
│   │   ├── document/            # 文档解析
│   │   └── core/                # 核心配置
│   ├── config/
│   │   ├── llm_config.yaml
│   │   └── agents/
│   ├── tests/
│   └── pyproject.toml
│
├── docs/
│   └── plans/
│
├── data/                        # 数据目录
│   ├── uploads/                 # 上传文件
│   ├── parsed/                  # 解析结果
│   └── knowledge_base/          # 知识库
│
├── docker-compose.yml
└── README.md
```

---

## 九、实施路线图

### 阶段一：基础RAG（Week 1-2）
- 目标：搭建可运行的基础检索系统
- 交付物：混合检索、法规知识库、基础查询API
- 关键指标：Recall@5 ≥ 0.70

### 阶段二：Agent能力（Week 3-4）
- 目标：实现单Agent工具调用能力
- 交付物：合规审查Agent、技术评审Agent、ReAct模式
- 关键指标：工具调用准确率 ≥ 0.85

### 阶段三：多智能体协作（Week 5-6）
- 目标：实现LangGraph多Agent协作
- 交付物：Supervisor Pattern、Self-Reflective RAG、对比分析Agent
- 关键指标：系统整体忠实度 ≥ 0.80

### 阶段四：生产部署（Week 7-8）
- 目标：可审计、可监控的生产系统
- 交付物：RAGAS评估、成本监控、FastAPI部署、可观测性
- 关键指标：P95延迟 < 15s、单次评标成本 < $0.20

---

## 十、关键设计模式总结

> 本节总结了核心技术组件和借鉴的设计模式

### 10.1 三路检索协作 ⭐（2026 最佳实践）

**来源**: 2026 企业级 RAG 最佳实践

```
                    Query
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐
    │  Vector   │ │    SQL    │ │   Graph   │
    │ Retrieval │ │ Retrieval │ │ Retrieval │
    │ (语义)    │ │ (精确)    │ │ (关系)    │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
          │             │             │
          └───────────┬─┘             │
                      ▼               │
               ┌─────────────┐        │
               │ RRF 融合    │◄───────┘
               └──────┬──────┘
                      ▼
               ┌─────────────┐
               │  Reranker   │
               └──────┬──────┘
                      ▼
                 Top-K Results
```

| 检索类型 | 职责 | 评标应用 |
|----------|------|----------|
| **Vector** | 语义理解、相似匹配 | "供应商A的技术方案如何？" |
| **SQL** | 精确数据查询 | 报价单、参数表的精确查询 |
| **Graph** | 关系追溯、逻辑链 | 供应商-产品-资质关系追溯 |

### 10.2 LightRAG 双层检索 ⭐（直接使用）

**来源**: LightRAG (港大 HKUDS)

```
                    Query
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      Local       Global       Hybrid
    (低层检索)   (高层检索)   (混合检索)
          │           │           │
          ▼           ▼           ▼
    具体实体      全局概念     综合结果
    精确属性      主题摘要
          │           │           │
          └───────────┼───────────┘
                      ▼
              知识图谱 + 向量检索
                      ▼
                  Reranker
                      ▼
                 Top-K Context
```

**招投标应用：**
- **Local**: "供应商A的注册资金是多少？"
- **Global**: "哪家供应商综合实力最强？"
- **Hybrid**: "评估供应商A并与其他对比"

### 10.2 RGSG 工作流模式（借鉴设计）

**来源**: Agentic-Procure-Audit-AI

```
Retrieve → Grade → Search → Generate
    ↑          │
    └──────────┘ (迭代最多3次)
```

| 节点 | 职责 | LightRAG 集成 |
|------|------|---------------|
| Retrieve | 检索相关上下文 | `lightrag.retrieve(query, mode=HYBRID)` |
| Grade | 评估检索结果相关性 | LLM 评估 |
| Search | 补充搜索 | 网络搜索/图谱扩展 |
| Generate | 生成最终评估 | LLM 生成 |

### 10.3 DSPy Prompt 优化 ⭐（直接使用）

**来源**: Stanford DSPy

```python
import dspy

# 定义评分模块
class BidScorer(dspy.Module):
    def __init__(self):
        self.score = dspy.Predict("context, criteria -> score, reasoning")

    def forward(self, context, criteria):
        return self.score(context=context, criteria=criteria)

# 使用 MIPROv2 自动优化（准确率 +15%）
optimizer = dspy.MIPROv2(metric=accuracy_metric, auto="light")
optimized_scorer = optimizer.compile(BidScorer(), trainset=train_data)
```

**优势**: 不再手动调 Prompt，自动优化评分准确率

### 10.4 TypedDict 状态管理（借鉴设计）

**来源**: Agentic-Procure-Audit-AI / LangGraph 最佳实践

```python
# 关键：使用 Annotated[list, add] 实现字段累积
class State(TypedDict):
    # 普通字段 - 直接覆盖
    query: str

    # 累积字段 - 自动追加
    reasoning_steps: Annotated[list[str], add]
    citations: Annotated[list[dict], add]
```

### 10.5 解析器注册表模式（借鉴设计）

**来源**: RAGFlow

```python
PARSERS = {
    "mineru": by_mineru,      # PDF 复杂布局
    "docling": by_docling,    # Word/Excel
    "paddleocr": by_paddleocr, # 扫描件
}

def chunk(filename, parser_id="mineru", **kwargs):
    return PARSERS.get(parser_id, default)(filename, **kwargs)
```

### 10.6 位置追踪机制（借鉴设计）

**来源**: RAGFlow

```python
@dataclass
class Chunk:
    content: str
    positions: list[tuple[int, int, int]]  # [(page, start, end)]
```

**应用**: 评标报告引用标书原文时可定位到具体页码和位置

### 10.7 评分可解释性（借鉴设计）

**来源**: Agentic-Procure-Audit-AI

```python
class ScoreWithReasoning(TypedDict):
    score: float          # 分数
    reasoning: str        # 评分理由
    evidence: list[str]   # 证据来源
    confidence: float     # 置信度
```

**原则**: 每个评分必须可追溯、可解释、可审计

---

## 十、附录

### 10.1 核心依赖

```toml
# pyproject.toml
[project]
name = "bid-evaluation-assistant"
version = "5.1.0"
requires-python = ">=3.11"

dependencies = [
    # Web 框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",

    # 文档解析
    "magic-pdf[full]>=0.7.0",      # MinerU PDF解析
    "docling>=1.0.0",               # IBM 多格式解析
    # "paddleocr>=2.8.0",           # 扫描件 OCR（可选）

    # RAG 核心
    "lightrag-hku>=0.1.0",          # LightRAG 双层检索（含内置图谱）
    "chromadb>=0.5.0",              # 向量存储（轻量方案）
    "flagembedding>=1.2.0",         # BGE Embedding

    # Agent 框架
    "langgraph>=0.2.0",
    "langchain>=0.3.0",

    # Prompt 优化
    "dspy>=2.5.0",                  # DSPy 自动优化

    # LLM
    "openai>=1.50.0",
    "dashscope>=1.20.0",            # 通义千问

    # 不采用的依赖（基于研究决策）
    # "neo4j>=5.0.0",               # 不需要，LightRAG 内置图谱
    # "pymilvus>=2.0.0",            # 不需要，ChromaDB 足够

    # 评估
    "ragas>=0.1.0",
    "deepeval>=0.21.0",

    # 可观测性
    "langfuse>=2.0.0",
]
```

### 10.2 参考资料

**直接使用的开源项目：**
- LightRAG: https://github.com/HKUDs/LightRAG ⭐⭐⭐⭐⭐ (30k+ stars)
  - 使用：双层检索、知识图谱、向量检索融合
- MinerU: https://github.com/opendatalab/MinerU ⭐⭐⭐⭐⭐ (50k+ stars)
  - 使用：复杂 PDF 解析
- Docling: https://github.com/docling-project/docling ⭐⭐⭐⭐⭐ (42k+ stars)
  - 使用：Word/Excel/多格式解析
- DSPy: https://github.com/stanfordnlp/dspy ⭐⭐⭐⭐⭐ (20k+ stars)
  - 使用：Prompt 自动优化
- ChromaDB: https://github.com/chroma-core/chroma ⭐⭐⭐⭐⭐
  - 使用：向量存储（LightRAG 原生支持）
- LangGraph: https://github.com/langchain-ai/langgraph ⭐⭐⭐⭐⭐ (40k+ stars)
  - 使用：Agent 工作流编排

**借鉴设计的项目：**
- RAG-Anything: https://github.com/HKUDS/RAG-Anything ⭐⭐⭐⭐⭐ (1k+ stars, 学术背书)
  - 借鉴：多模态内容处理、内容分类器、VLM 增强
- Agentic-Procure-Audit-AI: https://github.com/MrAliHasan/Agentic-Procure-Audit-AI ⭐⭐⭐
  - 借鉴：RGSG 工作流、评分可解释性
- RAGFlow: https://github.com/infiniflow/ragflow ⭐⭐⭐⭐⭐ (35k+ stars)
  - 借鉴：解析器注册表模式、位置追踪机制

**v5.2 新增借鉴项目（2026-02-20）：**
> 来源: `docs/research/2026-02-20-agentic-procure-audit-ai-analysis.md`

- **ProposalLLM**: https://github.com/William-GuoWei/ProposalLLM ⭐⭐⭐
  - 借鉴：**点对点应答格式** → 详见 3.4.1 评标报告输出格式
  - 借鉴：需求对应表驱动生成
- **kotaemon**: https://github.com/Cinnamon/kotaemon ⭐⭐⭐⭐⭐
  - 借鉴：**高级溯源引用展示** → 详见 3.5 PDF 查看器 + 高亮
  - 借鉴：LightRAG 集成方式、混合检索策略
- **RAGChecker**: https://github.com/amazon-science/RAGChecker ⭐⭐⭐⭐⭐ (Amazon Science)
  - 借鉴：**三层细粒度诊断** → 详见 6.2.1 RAGChecker 诊断
  - 借鉴：Hallucination 检测、Claim-level 评估
- **yibiao-simple**: https://github.com/yibiaoai/yibiao-simple ⭐⭐⭐⭐
  - 借鉴：招标文件解析流程、目录生成策略
- **RAGAS**: https://github.com/explodinggradients/ragas ⭐⭐⭐⭐⭐
  - 借鉴：RAG 评估框架、测试数据生成
  - 注：已在 v5.0 中采用

**谨慎参考的项目：**
- Yuxi-Know: https://github.com/xerrors/Yuxi-Know ⭐⭐ (~10 stars)
  - 状态：社区验证不足，Beta 阶段
  - 可借鉴：LangGraph 工作流模式、多解析器策略
  - 不采用：Neo4j + Milvus + MinIO 复杂架构
  - 详见：`docs/research/2026-02-20-yuxi-know-vs-rag-anything-analysis.md`

---

*设计文档版本：v5.2*
*最后更新：2026-02-20*
*更新内容：新增点对点应答格式(ProposalLLM)、溯源引用展示(kotaemon)、RAGChecker诊断；完善研究来源标注*
