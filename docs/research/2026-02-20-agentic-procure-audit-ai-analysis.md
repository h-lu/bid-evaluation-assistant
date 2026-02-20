# Agentic-Procure-Audit-AI 项目研究与类似项目分析

> 研究日期：2026-02-20
> 研究目的：深入研究 Agentic-Procure-Audit-AI 项目，寻找 GitHub 上类似项目
> 数据来源：GitHub、Web Search

---

## 一、Agentic-Procure-Audit-AI 项目详解

### 1.1 项目基本信息

| 维度 | 信息 |
|------|------|
| **GitHub** | https://github.com/MrAliHasan/Agentic-Procure-Audit-AI |
| **定位** | AI-Powered Procurement Intelligence & Bid Analysis Platform |
| **特点** | 100% Local AI（隐私优先） |
| **语言** | Python |

### 1.2 核心架构：RGSG 工作流

```
┌─────────────────────────────────────────────────────────────┐
│                    RGSG 工作流                               │
│              (Retrieve-Grade-Search-Generate)               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │ RETRIEVE │───>│  GRADE   │───>│  SEARCH  │            │
│   │  检索    │    │  评估    │    │  搜索    │            │
│   └──────────┘    └──────────┘    └──────────┘            │
│        │                               │                    │
│        │         ┌──────────┐          │                    │
│        └────────>│ GENERATE │<─────────┘                    │
│        迭代(3次) │   生成   │                               │
│                  └──────────┘                                │
│                                                             │
│   核心循环：检索 → 评估相关性 → 搜索补充 → 生成答案          │
│   如评估不合格，返回重新检索（最多 3 次迭代）               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心功能

#### 1.3.1 文档智能处理

```
┌─────────────────────────────────────────────────────────────┐
│                    文档处理流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   采购文档 ──→ OCR 解析 (Tesseract) ──→ 文本提取            │
│                    │                                        │
│                    ▼                                        │
│              结构化数据提取                                  │
│              • vendor_name (供应商名称)                     │
│              • total_price (总价)                           │
│              • currency (货币)                              │
│              • bid_date (投标日期)                          │
│              • valid_until (有效期)                         │
│              • specifications (规格)                        │
│              • delivery_terms (交付条款)                    │
│              • warranty (保修)                              │
│              • tender_reference (招标编号)                  │
│                    │                                        │
│                    ▼                                        │
│              存入 ChromaDB 向量库                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3.2 多维度评分系统

```json
{
  "overall_score": 85,
  "recommendation": "APPROVED",
  "breakdown": {
    "price": {
      "score": 92,
      "reasoning": "价格具有竞争力，低于市场平均 15%"
    },
    "quality": {
      "score": 85,
      "reasoning": "产品规格满足所有技术要求"
    },
    "reliability": {
      "score": 90,
      "reasoning": "供应商有 5 年以上行业经验"
    },
    "risk": {
      "score": 88,
      "reasoning": "财务状况良好，无重大风险"
    }
  },
  "confidence": 0.9,
  "key_findings": [
    "价格优势明显",
    "技术规格完全符合",
    "供应商信誉良好"
  ]
}
```

#### 1.3.3 人工审核机制

```
┌─────────────────────────────────────────────────────────────┐
│                    Human-in-the-Loop                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   AI 分析完成                                                │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              LangGraph Interrupt                     │  │
│   │  • 暂停工作流                                        │  │
│   │  • 等待人工审核                                      │  │
│   │  • 支持修改/批准/拒绝                                │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ├──→ 批准 ──→ 最终报告                               │
│       ├──→ 修改 ──→ 重新分析                               │
│       └──→ 拒绝 ──→ 标记问题                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| **LLM** | DeepSeek-R1 (Ollama) | 本地推理，隐私保护 |
| **Agent 编排** | LangGraph | 工作流编排、状态管理 |
| **向量存储** | ChromaDB | 文档向量索引 |
| **OCR** | Tesseract | PDF/图片文字识别 |
| **后端** | FastAPI | API 服务 |
| **前端** | Streamlit | 用户界面 |

### 1.5 项目结构

```
Agentic-Procure-Audit-AI/
├── agents/
│   ├── procurement_agent.py    # 采购分析 Agent
│   ├── document_agent.py       # 文档处理 Agent
│   └── scoring_agent.py        # 评分 Agent
├── workflows/
│   └── rgsg_workflow.py        # RGSG 工作流定义
├── tools/
│   ├── ocr_processor.py        # OCR 处理
│   ├── vector_store.py         # 向量存储
│   └── structured_extraction.py # 结构化提取
├── api/
│   └── main.py                 # FastAPI 入口
├── ui/
│   └── app.py                  # Streamlit 界面
└── config/
    └── settings.py             # 配置文件
```

---

## 二、可借鉴的设计模式

### 2.1 RGSG 工作流模式 ⭐⭐⭐⭐⭐

**核心价值**：通过迭代检索和评估，提高答案质量

```python
# 借鉴到我们的系统
from langgraph.graph import StateGraph, END

class RGSGWorkflow:
    """检索-评估-搜索-生成工作流"""

    def __init__(self):
        self.workflow = StateGraph(EvaluationState)
        self.max_iterations = 3

    def build(self):
        self.workflow.add_node("retrieve", self.retrieve_docs)
        self.workflow.add_node("grade", self.grade_relevance)
        self.workflow.add_node("search", self.search_supplement)
        self.workflow.add_node("generate", self.generate_answer)

        # 条件边：评估后决定是否继续迭代
        self.workflow.add_conditional_edges(
            "grade",
            self.should_continue,
            {
                "continue": "search",
                "generate": "generate",
                "max_retries": "generate"
            }
        )
        return self.workflow.compile()
```

**适用场景**：评标文档复杂，需要多次检索确认

### 2.2 多维度评分 + 推理 ⭐⭐⭐⭐⭐

**核心价值**：评分附带推理过程，可解释性强

```python
from pydantic import BaseModel
from typing import List

class CriterionScore(BaseModel):
    """单项评分"""
    score: float           # 0-100
    reasoning: str         # 评分理由
    evidence: List[str]    # 支持证据

class BidEvaluation(BaseModel):
    """投标评估结果"""
    overall_score: float
    recommendation: str    # APPROVED / CONDITIONAL / REJECTED
    breakdown: Dict[str, CriterionScore]
    confidence: float
    key_findings: List[str]
```

**适用场景**：评标需要透明、可追溯的评分依据

### 2.3 结构化变量提取 ⭐⭐⭐⭐

**核心价值**：从非结构化文档中提取关键信息

```python
class BidVariables(BaseModel):
    """投标关键变量"""
    vendor_name: str
    total_price: float
    currency: str = "CNY"
    bid_date: str
    valid_until: str
    specifications: Dict[str, Any]
    delivery_terms: str
    warranty_period: str
    tender_reference: str
```

**适用场景**：自动提取投标文件中的关键信息

### 2.4 100% 本地化部署 ⭐⭐⭐⭐

**核心价值**：数据不出本地，适合敏感场景

```
┌─────────────────────────────────────────────────────────────┐
│                    本地化部署架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │   Ollama    │   │  ChromaDB   │   │   FastAPI   │      │
│   │ (本地 LLM)  │   │ (本地向量)  │   │  (本地 API) │      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │
│          │                 │                 │               │
│          └────────────────┬┴────────────────┘               │
│                           │                                 │
│                    本地 Docker 环境                          │
│                    无外部 API 调用                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、GitHub 类似项目

### 3.1 直接相关项目

| 项目 | GitHub | 描述 | 可借鉴点 |
|------|--------|------|----------|
| **yibiao-simple** | [yibiaoai/yibiao-simple](https://github.com/yibiaoai/yibiao-simple) | 开源标书智能体 | 招标文件解析、内容生成 |
| **ProposalLLM** | [William-GuoWei/ProposalLLM](https://github.com/William-GuoWei/ProposalLLM) | 中文标书生成工具 | LLM 标书生成 |
| **kotaemon** | [Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) | RAG 文档对话工具 | 文档解析与问答 |
| **RAGFlow** | [infiniflow/RAGFlow](https://github.com/infiniflow/RAGFlow) | 开源 RAG 引擎 | 深度文档理解 |

### 3.2 RAG 评估框架

| 项目 | GitHub | 用途 |
|------|--------|------|
| **RAGAS** | [explodinggradients/ragas](https://github.com/explodinggradients/ragas) | RAG 管道评估 |
| **RAGChecker** | [amazon-science/RAGChecker](https://github.com/amazon-science/RAGChecker) | 细粒度诊断框架 |
| **RAGEval** | [OpenBMB/RAGEval](https://github.com/OpenBMB/RAGEval) | 场景特定评估 |

### 3.3 Agent 框架

| 项目 | 用途 |
|------|------|
| **LangGraph** | Agent 工作流编排 |
| **phidata** | LLM Agent 框架 |
| **Haystack** | 端到端 QA 系统 |

---

## 四、市场趋势分析

### 4.1 中国市场

| 产品 | 类型 | 特点 |
|------|------|------|
| **智标领航** | 商业 SaaS | AI 招投标助手 |
| **喜鹊标书AI** | 商业 SaaS | 标书自动生成 |
| **讯飞招采首席官** | 商业 SaaS | 语音 + AI 招采 |

### 4.2 国际市场

| 产品 | 类型 | 特点 |
|------|------|------|
| **AutogenAI** | 商业 | Salesforce 投资，声称提高中标率 20% |
| **EQUA AI** | 商业 | 端到端采购平台 |
| **mytender.io** | 商业 | AI 投标写作平台 |

### 4.3 政府采购趋势

- **2025 年中国政府采购规模**：约 13 万亿美元
- **AI 辅助招投标**：政府鼓励使用 AI 提升效率
- **合规性要求**：对数据安全、透明度要求高

---

## 五、对我们的借鉴建议

### 5.1 必须借鉴 ⭐⭐⭐⭐⭐

| 设计 | 来源 | 借鉴方式 |
|------|------|----------|
| **RGSG 工作流** | Agentic-Procure-Audit-AI | 用于评标文档复杂检索场景 |
| **多维度评分 + 推理** | Agentic-Procure-Audit-AI | 评标结果附带详细理由 |
| **结构化变量提取** | Agentic-Procure-Audit-AI | 自动提取投标关键信息 |
| **Human-in-the-Loop** | Agentic-Procure-Audit-AI | LangGraph interrupt 机制 |

### 5.2 可选借鉴 ⭐⭐⭐

| 设计 | 来源 | 借鉴方式 |
|------|------|----------|
| **100% 本地化** | Agentic-Procure-Audit-AI | 可选部署模式 |
| **Streamlit UI** | Agentic-Procure-Audit-AI | 快速原型验证 |
| **RAGAS 评估** | RAGAS | 检索质量评估 |

### 5.3 不采用的设计

| 设计 | 来源 | 不采用理由 |
|------|------|------------|
| **Tesseract OCR** | Agentic-Procure-Audit-AI | MinerU 更适合中文 PDF |
| **DeepSeek-R1** | Agentic-Procure-Audit-AI | 根据实际需求选择 LLM |
| **单一 ChromaDB** | Agentic-Procure-Audit-AI | 我们用 LightRAG 内置存储 |

---

## 六、技术选型对比

### 6.1 与我们的架构对比

| 组件 | Agentic-Procure-Audit-AI | 我们的系统 |
|------|--------------------------|------------|
| **LLM** | DeepSeek-R1 (Ollama) | 可配置 (OpenAI/本地) |
| **Agent 编排** | LangGraph | LangGraph ✅ |
| **RAG 引擎** | 自建 (ChromaDB) | LightRAG |
| **向量存储** | ChromaDB | ChromaDB (轻量) |
| **文档解析** | Tesseract OCR | MinerU + Docling |
| **后端** | FastAPI | FastAPI ✅ |
| **前端** | Streamlit | 可选 |

### 6.2 工作流对比

| 工作流 | Agentic-Procure-Audit-AI | 我们的系统 |
|--------|--------------------------|------------|
| **文档处理** | OCR → 结构化提取 | MinerU → content_list.json → 分块 |
| **检索策略** | RGSG (迭代检索) | LightRAG (双层检索 + 图谱) |
| **评分方式** | 多维度 + 推理 | DSPy 优化 + 推理链 |
| **人工介入** | LangGraph interrupt | LangGraph interrupt ✅ |

---

## 七、实现建议

### 7.1 借鉴 RGSG 工作流

```python
# src/modules/workflow/application/graphs/rgsg_graph.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict

class RGSGState(TypedDict):
    """RGSG 工作流状态"""
    query: str                    # 原始查询
    retrieved_docs: List[Dict]    # 检索到的文档
    relevance_score: float        # 相关性评分
    supplementary_info: str       # 补充信息
    iteration_count: int          # 迭代次数
    final_answer: str             # 最终答案
    citations: List[Dict]         # 溯源引用

class RGSGWorkflow:
    """检索-评估-搜索-生成工作流"""

    MAX_ITERATIONS = 3
    RELEVANCE_THRESHOLD = 0.7

    def __init__(self, retriever, grader, generator):
        self.retriever = retriever
        self.grader = grader
        self.generator = generator

    def build_graph(self) -> StateGraph:
        workflow = StateGraph(RGSGState)

        # 添加节点
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade", self.grade)
        workflow.add_node("search", self.search_supplement)
        workflow.add_node("generate", self.generate)

        # 设置入口
        workflow.set_entry_point("retrieve")

        # 添加边
        workflow.add_edge("retrieve", "grade")
        workflow.add_conditional_edges(
            "grade",
            self.decide_next,
            {
                "search": "search",
                "generate": "generate"
            }
        )
        workflow.add_edge("search", "retrieve")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def decide_next(self, state: RGSGState) -> str:
        """决定下一步"""
        if state["relevance_score"] >= self.RELEVANCE_THRESHOLD:
            return "generate"
        if state["iteration_count"] >= self.MAX_ITERATIONS:
            return "generate"
        return "search"
```

### 7.2 借鉴多维度评分

```python
# src/modules/evaluation/domain/value_objects.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class Recommendation(str, Enum):
    """推荐结果"""
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"

class CriterionScore(BaseModel):
    """单项评分"""
    score: float = Field(..., ge=0, le=100)
    reasoning: str
    evidence: List[str] = []
    confidence: float = Field(..., ge=0, le=1)

class MultiCriteriaEvaluation(BaseModel):
    """多维度评估结果"""
    overall_score: float = Field(..., ge=0, le=100)
    recommendation: Recommendation
    breakdown: Dict[str, CriterionScore]  # price, quality, reliability, risk
    confidence: float = Field(..., ge=0, le=1)
    key_findings: List[str]
    risk_alerts: List[str] = []
    suggested_questions: List[str] = []
```

### 7.3 借鉴结构化提取

```python
# src/modules/documents/domain/value_objects.py

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import date

class BidVariables(BaseModel):
    """投标关键变量（从 Agentic-Procure-Audit-AI 借鉴）"""
    vendor_name: str
    total_price: float
    currency: str = "CNY"
    bid_date: Optional[date]
    valid_until: Optional[date]
    specifications: Dict[str, Any] = {}
    delivery_terms: Optional[str]
    warranty_period: Optional[str]
    tender_reference: Optional[str]

    # 扩展：中文场景特有
    business_scope: Optional[str]      # 经营范围
    registered_capital: Optional[float] # 注册资本
    qualification_level: Optional[str]  # 资质等级
    past_performance: List[str] = []    # 业绩记录
```

---

## 八、参考资料

**Agentic-Procure-Audit-AI:**
- GitHub: https://github.com/MrAliHasan/Agentic-Procure-Audit-AI

**类似项目:**
- yibiao-simple: https://github.com/yibiaoai/yibiao-simple
- ProposalLLM: https://github.com/William-GuoWei/ProposalLLM
- kotaemon: https://github.com/Cinnamon/kotaemon
- RAGFlow: https://github.com/infiniflow/RAGFlow

**RAG 评估:**
- RAGAS: https://github.com/explodinggradients/ragas
- RAGChecker: https://github.com/amazon-science/RAGChecker

**市场研究:**
- [2025 GitHub AI Projects](https://post.m.smzdm.com/zz/p/a9kov7o7/)
- [政府采购 AI 趋势](http://www.ccgp.gov.cn/)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
