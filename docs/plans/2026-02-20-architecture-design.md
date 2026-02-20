# 辅助评标专家系统 —— 端到端架构设计

> 版本：v4.0
> 设计日期：2026-02-20
> 更新日期：2026-02-20
> 状态：已批准

---

## 〇、研究来源说明

本设计参考了以下 GitHub 项目的深入研究：

| 项目 | Star | 研究重点 | 借鉴/使用方式 |
|------|------|----------|---------------|
| **LightRAG** | 30k+ | 轻量级知识图谱 RAG | **直接使用** - 双层检索、知识图谱增强 |
| **Agentic-Procure-Audit-AI** | - | Agent架构、评分算法 | 借鉴设计 - RGSG工作流、评分可解释性 |
| **RAGFlow** | 35k+ | 文档解析、RAG架构 | 借鉴设计 - 解析器注册表、位置追踪 |
| **DSPy** | 20k+ | Prompt 优化 | **直接使用** - 评分模型自动优化 |
| **Docling** | 42k+ | 多格式文档解析 | **直接使用** - Word/Excel 解析 |
| **LangGraph** | 40k+ | Agent 工作流编排 | **直接使用** - Evaluator-Optimizer、interrupt |

详细研究报告见：
- `docs/research/2026-02-20-end-to-end-design-research.md` ⭐ 端到端设计研究
- `docs/research/2026-02-20-lightrag-research.md`
- `docs/research/2026-02-20-agentic-procure-audit-ai-research.md`
- `docs/research/2026-02-20-ragflow-research.md`
- `docs/research/2026-02-20-github-projects-round2.md`

---

## 〇.1 v4.0 更新要点

基于端到端设计研究，本版本主要优化：

| 优化项 | 说明 |
|--------|------|
| **三路检索协作** | Vector + SQL + Graph 三路检索架构 |
| **Evaluator-Optimizer** | 评分迭代优化模式 |
| **Human-in-the-Loop** | interrupt 机制实现人工审核 |
| **分块策略优化** | 512 token + 15-20% overlap 黄金配置 |
| **评估闭环** | 五步评估监控体系 |

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

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **文档解析** | MinerU 2.5 + Docling + PaddleOCR | PDF/Word/Excel/扫描件全覆盖 |
| **RAG 框架** | **LightRAG** ⭐ | 双层检索 + 知识图谱增强 |
| **Embedding** | BGE-M3 | 多模式（稠密+稀疏+ColBERT） |
| **向量数据库** | ChromaDB（LightRAG 原生支持） | 向量存储 |
| **知识图谱** | NetworkX（开发）/ Neo4j（生产） | 供应商关系、产品对比 |
| **Reranker** | BGE-Reranker-v2-m3 | 重排序 |
| **Agent框架** | LangGraph | 状态机工作流（RGSG模式） |
| **Prompt优化** | **DSPy** ⭐ | 自动优化评分 Prompt |
| **LLM** | DeepSeek / Qwen | 按职责分工 |
| **评估** | RAGAS + DeepEval | RAG评估 |
| **可观测性** | Langfuse | 私有化部署 |
| **后端API** | FastAPI + Pydantic v2 | 异步框架 |
| **前端** | Vue3 + Element Plus + Pinia | 评标界面 |

> ⭐ 标记为本版本新增的核心组件

---

## 二、系统整体架构

### 2.1 架构选型：分层单体架构（三路检索协作）

> **设计来源**: 2026 企业级 RAG 最佳实践

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
│  │  │ NetworkX │  │  Neo4j   │  │ Langfuse │  ← 可观测性              │   │
│  │  │ (开发)   │  │ (生产)   │  │ (监控)   │                          │   │
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

### 2.2 选型理由

| 维度 | 分层单体 | 微服务 | 模块化单体 |
|------|----------|--------|-----------|
| **复杂度** | ✅ 低 | ❌ 高 | ⚠️ 中 |
| **开发速度** | ✅ 快 | ❌ 慢 | ⚠️ 中 |
| **MVP适配** | ✅ 高 | ❌ 低 | ⚠️ 中 |
| **运维成本** | ✅ 低 | ❌ 高 | ✅ 低 |
| **可演进性** | ⚠️ 中 | ✅ 高 | ✅ 高 |

---

## 三、核心模块设计

### 3.1 文档解析模块（解析器注册表模式）

> **设计来源**: RAGFlow 解析器架构

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
│   │  │ MinerU  │ │PaddleOCR│ │DOCX     │ ...   │          │
│   │  │(PDF优先)│ │(扫描件) │ │Parser   │       │          │
│   │  └─────────┘ └─────────┘ └─────────┘       │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │          Chunker (分块器)                    │          │
│   │  ┌────────────────────────────────────────┐ │          │
│   │  │ naive_merge_with_images()              │ │          │
│   │  │ - 保留表格上下文 (table_context_size)   │ │          │
│   │  │ - 保留图片上下文 (image_context_size)   │ │          │
│   │  │ - 位置追踪 (add_positions)             │ │          │
│   │  └────────────────────────────────────────┘ │          │
│   └─────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────┐          │
│   │  Chunk 输出结构                              │          │
│   │  {                                          │          │
│   │    "content": "文本内容...",                │          │
│   │    "positions": [(page, start, end), ...],  │ ← 溯源引用│
│   │    "metadata": {...},                       │          │
│   │    "table_context": "...",  // 可选         │          │
│   │    "image_context": "..."   // 可选         │          │
│   │  }                                          │          │
│   └─────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**解析器注册表模式（策略模式 + 配置驱动）:**

```python
# 设计模式：开闭原则 - 新增解析器只需注册，无需修改现有代码
PARSERS = {
    "mineru": by_mineru,        # MinerU PDF解析（优先）
    "paddleocr": by_paddleocr,  # 扫描件OCR
    "docx": by_docx,            # Word文档
    "plaintext": by_plaintext,  # 纯文本（默认回退）
}

def chunk(filename: str, parser_id: str = "mineru", **kwargs):
    """主入口：根据配置选择解析器"""
    parser_func = PARSERS.get(parser_id, by_plaintext)
    return parser_func(filename, **kwargs)
```

**分块策略（2026最佳实践 - 基于研究验证）：**

> **关键发现**：512 token 比 1024 token 的 MRR 指标高 **12-18%**

| 文档类型 | Chunk Size | Overlap | 切分算法 | 理由 |
|---------|-----------|---------|---------|------|
| **投标文件** | **512 token** | **15-20%** | 递归字符 | 工程黄金配置 |
| 技术参数表 | 按参数项 | 0% | 结构感知 | 独立检索 |
| 产品注册证 | 整页 | N/A | 原子切分 | 原子性文档 |
| 法规条文 | 256-300 token | 15% | 递归字符 | 独立引用 |
| 报价单 | 按行/项 | 0% | 结构感知 | SQL 精确查询 |

**Overlap 黄金区间**：15-20%（工程实践验证）

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

**与 RAGFlow 方案对比：**

| 方面 | 原方案 (RAGFlow 混合检索) | 新方案 (LightRAG) |
|------|---------------------------|-------------------|
| **集成方式** | 借鉴设计，自实现 | pip 安装，直接使用 ✅ |
| **知识图谱** | 无 | 内置轻量级 KG ✅ |
| **双层检索** | 无 | Low-Level + High-Level ✅ |
| **向量存储** | ChromaDB | ChromaDB（兼容）✅ |
| **增量更新** | 需自实现 | 原生支持 ✅ |
| **法律文档** | - | 84.8% 胜率 ✅ |

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

### 6.2 DeepEval评估指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| Hallucination | 幻觉率 | < 0.05 |
| Tool Call Accuracy | 工具调用准确率 | ≥ 0.90 |

### 6.3 可观测性（Langfuse）

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

  # PostgreSQL
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=bid_eval
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ChromaDB
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Langfuse (可观测性)
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/langfuse

volumes:
  postgres_data:
  chroma_data:
```

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
version = "3.0.0"
requires-python = ">=3.11"

dependencies = [
    # Web 框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",

    # 文档解析
    "magic-pdf[full]>=0.7.0",      # MinerU PDF解析
    "docling>=1.0.0",               # IBM 多格式解析 ⭐
    "paddleocr>=2.8.0",             # 扫描件 OCR

    # RAG 核心
    "lightrag-hku>=0.1.0",          # LightRAG 双层检索 ⭐
    "chromadb>=0.5.0",              # 向量存储
    "flagembedding>=1.2.0",         # BGE Embedding

    # Agent 框架
    "langgraph>=0.2.0",
    "langchain>=0.3.0",

    # Prompt 优化
    "dspy>=2.5.0",                  # DSPy 自动优化 ⭐

    # LLM
    "openai>=1.50.0",
    "dashscope>=1.20.0",            # 通义千问

    # 知识图谱（可选，生产环境）
    # "neo4j>=5.0.0",

    # 评估
    "ragas>=0.1.0",
    "deepeval>=0.21.0",

    # 可观测性
    "langfuse>=2.0.0",
]
```

### 10.2 参考资料

**直接使用的开源项目：**
- LightRAG: https://github.com/HKUDS/LightRAG ⭐
  - 使用：双层检索、知识图谱、向量检索融合
- MinerU: https://github.com/opendatalab/MinerU
  - 使用：复杂 PDF 解析
- Docling: https://github.com/docling-project/docling ⭐
  - 使用：Word/Excel/多格式解析
- DSPy: https://github.com/stanfordnlp/dspy ⭐
  - 使用：Prompt 自动优化
- ChromaDB: https://github.com/chroma-core/chroma
  - 使用：向量存储（LightRAG 原生支持）
- LangGraph: https://github.com/langchain-ai/langgraph
  - 使用：Agent 工作流编排

**借鉴设计的项目：**
- Agentic-Procure-Audit-AI: https://github.com/MrAliHasan/Agentic-Procure-Audit-AI
  - 借鉴：RGSG 工作流、评分可解释性
- RAGFlow: https://github.com/infiniflow/ragflow
  - 借鉴：解析器注册表模式、位置追踪机制

---

*设计文档版本：v4.0*
*最后更新：2026-02-20*
*更新内容：三路检索协作、Evaluator-Optimizer、Human-in-the-Loop、五步评估闭环*
