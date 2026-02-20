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

## 三、GitHub 类似项目详细分析

### 3.1 yibiao-simple（开源标书智能体）⭐⭐⭐⭐⭐

**项目地址**: https://github.com/yibiaoai/yibiao-simple

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | 开源 AI 标书编写工具 |
| **商业产品** | yibiao.pro（商业 SaaS） |
| **可信度** | ⭐⭐⭐⭐ 有商业产品背书 |

#### 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    yibiao-simple 架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   前端: React 18+ + TypeScript + Tailwind CSS              │
│   后端: FastAPI + Python 3.8+                               │
│   AI: OpenAI SDK (兼容 OpenAI API)                          │
│   部署: PyInstaller 单文件打包                               │
│                                                             │
│   推荐模型: DeepSeek (性价比高)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 核心功能

```
┌─────────────────────────────────────────────────────────────┐
│                    功能流程                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   招标文件上传                                               │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          智能文档解析                                │  │
│   │  • 自动分析招标文件结构                              │  │
│   │  • 提取关键信息                                      │  │
│   │  • 识别技术评分要求                                  │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          AI 生成目录                                 │  │
│   │  • 基于招标文件智能生成                              │  │
│   │  • 专业三级目录结构                                  │  │
│   │  • 符合行业标准                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          内容自动生成                                │  │
│   │  • 为每个章节生成针对性内容                          │  │
│   │  • 高质量、专业化表述                                │  │
│   │  • 支持人工微调                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│   一键导出 Word → 自由编辑                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **招标文件解析** | ⭐⭐⭐⭐⭐ | 提取关键信息和技术评分要求 |
| **AI 生成目录** | ⭐⭐⭐⭐ | 智能生成结构化大纲 |
| **内容生成** | ⭐⭐⭐⭐ | 针对性内容生成策略 |
| **Word 导出** | ⭐⭐⭐ | 报告输出格式 |
| **React + FastAPI** | ⭐⭐⭐⭐ | 与我们技术栈一致 |

---

### 3.2 ProposalLLM（中文标书生成工具）⭐⭐⭐⭐

**项目地址**: https://github.com/William-GuoWei/ProposalLLM

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | LLM 驱动的中文标书生成工具 |
| **特点** | 点对点应答格式 |
| **支持模型** | ChatGPT / 百度千帆 (ERNIE-Speed-8K) |
| **可信度** | ⭐⭐⭐ 个人项目，功能专注 |

#### 核心功能

```
┌─────────────────────────────────────────────────────────────┐
│                    ProposalLLM 功能                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 需求对应表驱动                                          │
│      • 根据产品需求对应表自动生成                            │
│      • 点对点应答格式标书                                    │
│                                                             │
│   2. 产品说明书复用                                          │
│      • 自动匹配产品功能                                      │
│      • 拷贝产品说明书相关内容                                │
│                                                             │
│   3. 技术需求偏离表                                          │
│      • 自动填写需求对应表                                    │
│      • 点对点应答                                            │
│                                                             │
│   4. 产品手册拆解                                           │
│      • 拆解为可复用的细节文档                                │
│      • 支持后续标书复用                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 代码示例

```python
# ProposalLLM 核心流程
from docx import Document
import openai  # 或百度千帆

class ProposalGenerator:
    """标书生成器"""

    def __init__(self, model="ernie-speed-8k"):
        self.model = model

    def generate_proposal(
        self,
        requirement_table: dict,  # 需求对应表
        product_manual: str,      # 产品说明书
        output_path: str
    ):
        """生成标书"""
        doc = Document()

        for req in requirement_table["requirements"]:
            # 1. 匹配产品功能
            matched_content = self.match_product_content(
                req, product_manual
            )

            # 2. 生成点对点应答
            response = self.generate_response(req, matched_content)

            # 3. 写入文档
            doc.add_heading(req["title"], level=2)
            doc.add_paragraph(response)

        doc.save(output_path)

    def generate_response(self, requirement: dict, product_content: str) -> str:
        """使用 LLM 生成应答"""
        prompt = f"""
        需求：{requirement["description"]}

        产品相关内容：{product_content}

        请生成符合需求的点对点应答内容。
        """
        return self.llm_call(prompt)
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **点对点应答** | ⭐⭐⭐⭐⭐ | 评标报告的核心格式 |
| **需求对应表** | ⭐⭐⭐⭐ | 评分标准 vs 投标响应 |
| **产品手册拆解** | ⭐⭐⭐ | 知识库复用策略 |
| **百度千帆支持** | ⭐⭐⭐ | 国产模型备选 |

---

### 3.3 kotaemon（RAG 文档对话工具）⭐⭐⭐⭐⭐

**项目地址**: https://github.com/Cinnamon/kotaemon

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | 开源 RAG 文档对话工具 |
| **Stars** | 高（活跃项目） |
| **特点** | 支持 GraphRAG、LightRAG、NanoGraphRAG |
| **UI** | Gradio |
| **可信度** | ⭐⭐⭐⭐⭐ 社区活跃，功能完善 |

#### 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    kotaemon 架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   UI 层: Gradio (Web 界面)                                  │
│                                                             │
│   RAG 层:                                                   │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          Hybrid RAG Pipeline                         │  │
│   │  • 全文检索 + 向量检索                               │  │
│   │  • Re-ranking 重排序                                 │  │
│   │  • 多模态 QA 支持                                    │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   GraphRAG 支持:                                            │
│   • GraphRAG (Microsoft)                                    │
│   • LightRAG (HKUDS)                                        │
│   • NanoGraphRAG (轻量版)                                   │
│                                                             │
│   Agent 推理:                                               │
│   • ReAct Agent                                             │
│   • ReWOO Agent                                             │
│                                                             │
│   溯源引用:                                                 │
│   • 高级引用功能                                            │
│   • 浏览器内 PDF 查看器                                     │
│   • 高亮显示来源                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### LightRAG 集成方式

```bash
# 安装 LightRAG
pip install git+https://github.com/HKUDS/LightRAG.git

# 启动 kotaemon 并启用 LightRAG
USE_LIGHTRAG=true python app.py
```

#### 核心功能

```
┌─────────────────────────────────────────────────────────────┐
│                    kotaemon 功能亮点                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 混合 RAG 管道                                          │
│      ┌───────────┐    ┌───────────┐    ┌───────────┐       │
│      │  全文检索  │    │  向量检索  │    │  图谱检索  │       │
│      └─────┬─────┘    └─────┬─────┘    └─────┬─────┘       │
│            │                │                │              │
│            └────────────────┼────────────────┘              │
│                             ▼                               │
│                    ┌───────────────┐                        │
│                    │  Re-ranking   │                        │
│                    └───────────────┘                        │
│                                                             │
│   2. 多模态 QA                                              │
│      • 图片理解                                             │
│      • 表格解析                                             │
│      • 图表分析                                             │
│                                                             │
│   3. 高级溯源引用                                           │
│      • 浏览器内 PDF 查看器                                  │
│      • 高亮显示来源段落                                     │
│      • 精确页码定位                                         │
│                                                             │
│   4. 复杂推理支持                                           │
│      • ReAct (推理+行动)                                    │
│      • ReWOO (规划+执行)                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **LightRAG 集成** | ⭐⭐⭐⭐⭐ | 与我们选型完全一致 |
| **混合检索** | ⭐⭐⭐⭐⭐ | 全文 + 向量 + 图谱 |
| **高级溯源引用** | ⭐⭐⭐⭐⭐ | PDF 查看器 + 高亮 |
| **多模态 QA** | ⭐⭐⭐⭐ | 图片/表格/图表 |
| **Re-ranking** | ⭐⭐⭐⭐ | 重排序策略 |

---

### 3.4 RAGFlow（开源 RAG 引擎）⭐⭐⭐⭐⭐

**项目地址**: https://github.com/infiniflow/RAGFlow

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | 开源 RAG 引擎 |
| **Stars** | 非常高（行业领先） |
| **特点** | 深度文档理解、模板化分块 |
| **部署** | Docker (~2GB 镜像) |
| **可信度** | ⭐⭐⭐⭐⭐ 行业领先，持续更新 |

#### 重要更新时间线

| 日期 | 更新内容 |
|------|----------|
| **2025-10-23** | 支持 MinerU & Docling 文档解析 |
| **2025-08-01** | 支持 Agentic Workflow 和 MCP |
| **2025-06-15** | 支持多模态文档处理 |

#### 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    RAGFlow 架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   文档解析层:                                               │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  MinerU  │  Docling  │  原生解析器  │  OCR          │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   深度文档理解:                                             │
│   • 智能布局分析                                            │
│   • 表格结构识别                                            │
│   • 图片内容提取                                            │
│                                                             │
│   模板化分块 (关键特性!):                                   │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          Template-based Chunking                    │  │
│   │  • 智能且可解释                                      │  │
│   │  • 根据文档类型选择模板                              │  │
│   │  • 保留语义边界                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   Agentic Workflow:                                         │
│   • Agent 编排                                              │
│   • MCP 协议支持                                            │
│   • 工具调用                                                │
│                                                             │
│   引用溯源:                                                 │
│   • Grounded citations                                      │
│   • 减少幻觉                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 支持的文档格式

```
┌─────────────────────────────────────────────────────────────┐
│                    支持的格式                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   文档: Word, PDF, TXT, Markdown                           │
│   演示: PowerPoint, Slides                                  │
│   表格: Excel                                               │
│   图片: JPG, PNG, 扫描件                                   │
│                                                             │
│   特殊处理:                                                 │
│   • 扫描件 OCR                                              │
│   • 复杂表格                                                │
│   • 嵌入图片                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **MinerU 集成** | ⭐⭐⭐⭐⭐ | 与我们选型一致 |
| **模板化分块** | ⭐⭐⭐⭐⭐ | **核心借鉴点！** |
| **Agentic Workflow** | ⭐⭐⭐⭐ | Agent 编排思路 |
| **MCP 协议** | ⭐⭐⭐ | 工具标准化 |
| **Grounded citations** | ⭐⭐⭐⭐⭐ | 减少幻觉，精确溯源 |

---

### 3.5 RAGAS（RAG 评估框架）⭐⭐⭐⭐⭐

**项目地址**: https://github.com/explodinggradients/ragas

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | LLM 应用评估框架 |
| **特点** | 客观指标、测试数据生成 |
| **集成** | LangChain 原生支持 |
| **可信度** | ⭐⭐⭐⭐⭐ 行业标准 |

#### 核心功能

```python
# RAGAS 使用示例
from ragas import SingleTurnSample
from ragas.metrics import AspectCritic, LLMContextRecall
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

# 初始化评估 LLM
evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o"))

# 定义评估指标
metrics = [
    AspectCritic(
        name="summary_accuracy",
        llm=evaluator_llm,
        definition="Verify if the summary is accurate."
    ),
    LLMContextRecall(llm=evaluator_llm),
]

# 测试数据
test_data = {
    "user_input": "评标标准是什么？",
    "response": "根据招标文件，评标标准包括...",
    "retrieved_contexts": ["招标文件第5页...", "技术规范第2页..."],
    "reference": "评标标准包括价格、技术、商务三个方面..."
}

# 评估
sample = SingleTurnSample(**test_data)
for metric in metrics:
    score = await metric.single_turn_ascore(sample)
    print(f"{metric.name}: {score}")
```

#### 评估指标体系

```
┌─────────────────────────────────────────────────────────────┐
│                    RAGAS 评估指标                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   检索质量指标:                                             │
│   • Context Precision (上下文精确度)                        │
│   • Context Recall (上下文召回率)                           │
│   • Context Relevancy (上下文相关性)                        │
│                                                             │
│   生成质量指标:                                             │
│   • Faithfulness (忠实度) - 是否基于上下文                  │
│   • Answer Relevancy (答案相关性)                           │
│   • Answer Correctness (答案正确性)                         │
│                                                             │
│   自定义指标:                                               │
│   • AspectCritic (方面评估)                                 │
│   • SimpleCriteria (简单标准)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **Context Precision** | ⭐⭐⭐⭐⭐ | 检索精确度评估 |
| **Faithfulness** | ⭐⭐⭐⭐⭐ | 生成忠实度评估 |
| **测试数据生成** | ⭐⭐⭐⭐ | 自动生成测试用例 |
| **LangChain 集成** | ⭐⭐⭐⭐ | 与 LangGraph 兼容 |

---

### 3.6 RAGChecker（Amazon 细粒度诊断框架）⭐⭐⭐⭐⭐

**项目地址**: https://github.com/amazon-science/RAGChecker

#### 基本信息

| 维度 | 信息 |
|------|------|
| **定位** | 细粒度 RAG 诊断框架 |
| **来源** | Amazon Science |
| **特点** | 三层指标、Claim-level 评估 |
| **可信度** | ⭐⭐⭐⭐⭐ 学术 + 工业验证 |

#### 核心特点：三层指标体系

```
┌─────────────────────────────────────────────────────────────┐
│                    RAGChecker 三层指标                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              Overall Metrics (整体层)                │  │
│   │  • Precision: 73.3%                                 │  │
│   │  • Recall: 62.5%                                    │  │
│   │  • F1: 67.3%                                        │  │
│   └─────────────────────────────────────────────────────┘  │
│                           │                                 │
│           ┌───────────────┴───────────────┐                │
│           ▼                               ▼                 │
│   ┌───────────────────┐         ┌───────────────────┐      │
│   │  Retriever Metrics │         │  Generator Metrics │     │
│   │    (检索层)        │         │    (生成层)        │     │
│   ├───────────────────┤         ├───────────────────┤      │
│   │ • Claim Recall    │         │ • Context Utilization │   │
│   │   61.4%           │         │   87.5%               │   │
│   │ • Context         │         │ • Noise Sensitivity   │   │
│   │   Precision 87.5% │         │   22.5%               │   │
│   │                   │         │ • Hallucination 4.2%  │   │
│   │                   │         │ • Faithfulness 70.8%  │   │
│   └───────────────────┘         └───────────────────┘      │
│                                                             │
│   核心方法: Claim-level Entailment (声明级别蕴含)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 使用示例

```python
# RAGChecker 使用示例
from ragchecker import RAGResults, RAGChecker

# 准备测试数据
rag_results = RAGResults.from_dict({
    "results": [
        {
            "query": "投标保证金是多少？",
            "response": "根据招标文件，投标保证金为合同金额的2%...",
            "retrieved_contexts": ["招标文件第10页: 保证金为合同金额2%..."],
            "ground_truth": "投标保证金为合同金额的2%"
        }
    ]
})

# 运行评估
checker = RAGChecker(
    evaluator_model="gpt-4o",
    batch_size=10
)
metrics = checker.evaluate(rag_results)

# 输出结果
print(f"Overall F1: {metrics['overall_metrics']['f1']}")
print(f"Retriever Claim Recall: {metrics['retriever_metrics']['claim_recall']}")
print(f"Generator Faithfulness: {metrics['generator_metrics']['faithfulness']}")
print(f"Hallucination Rate: {metrics['generator_metrics']['hallucination']}")
```

#### 可借鉴点

| 功能 | 借鉴价值 | 说明 |
|------|----------|------|
| **三层诊断** | ⭐⭐⭐⭐⭐ | 区分检索/生成问题 |
| **Claim-level 评估** | ⭐⭐⭐⭐⭐ | 细粒度精确评估 |
| **Hallucination 检测** | ⭐⭐⭐⭐⭐ | 幻觉率量化 |
| **Context Utilization** | ⭐⭐⭐⭐ | 上下文利用效率 |

---

### 3.7 项目对比汇总

| 项目 | Stars | 可信度 | 与评标相关度 | 核心借鉴点 |
|------|-------|--------|--------------|------------|
| **yibiao-simple** | 中 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 招标文件解析、目录生成 |
| **ProposalLLM** | 低 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 点对点应答、需求对应表 |
| **kotaemon** | 高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | LightRAG 集成、溯源引用 |
| **RAGFlow** | 非常高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | MinerU 集成、模板化分块 |
| **RAGAS** | 高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | RAG 评估、测试生成 |
| **RAGChecker** | 高 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 细粒度诊断、幻觉检测 |

---

### 3.8 其他相关项目

| 项目 | 用途 |
|------|------|
| **LangGraph** | Agent 工作流编排 |
| **phidata** | LLM Agent 框架 |
| **Haystack** | 端到端 QA 系统 |
| **RAGEval** | 场景特定评估 |

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
| **点对点应答格式** | ProposalLLM | 评分标准 vs 投标响应对照表 |
| **模板化分块** | RAGFlow | 根据文档类型选择分块模板 |
| **高级溯源引用** | kotaemon | PDF 查看器 + 高亮显示 |

### 5.2 可选借鉴 ⭐⭐⭐⭐

| 设计 | 来源 | 借鉴方式 |
|------|------|----------|
| **100% 本地化** | Agentic-Procure-Audit-AI | 可选部署模式 |
| **Streamlit UI** | Agentic-Procure-Audit-AI | 快速原型验证 |
| **RAGAS 评估** | RAGAS | 检索质量评估 |
| **RAGChecker 诊断** | RAGChecker | 三层指标诊断 |
| **需求对应表** | ProposalLLM | 评分项 vs 投标响应映射 |
| **产品手册拆解** | ProposalLLM | 知识库复用策略 |
| **混合检索** | kotaemon | 全文 + 向量 + 图谱 |
| **MCP 协议** | RAGFlow | 工具调用标准化 |

### 5.3 不采用的设计

| 设计 | 来源 | 不采用理由 |
|------|------|------------|
| **Tesseract OCR** | Agentic-Procure-Audit-AI | MinerU 更适合中文 PDF |
| **DeepSeek-R1 强制** | Agentic-Procure-Audit-AI | 根据实际需求选择 LLM |
| **单一 ChromaDB** | Agentic-Procure-Audit-AI | 我们用 LightRAG 内置存储 |
| **百度千帆** | ProposalLLM | 保持模型可选性 |
| **Docker 大镜像** | RAGFlow | 我们需要轻量部署 |

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

## 九、评估框架集成建议

### 9.1 RAGAS + RAGChecker 组合使用

```
┌─────────────────────────────────────────────────────────────┐
│                    评估框架集成                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   开发阶段 (RAGAS):                                         │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  • 快速迭代评估                                      │  │
│   │  • 自动生成测试数据                                  │  │
│   │  • 基础指标监控                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   生产阶段 (RAGChecker):                                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  • 细粒度诊断                                        │  │
│   │  • 幻觉检测                                          │  │
│   │  • 三层指标分析                                      │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 推荐的评估流程

```python
# 评估流程示例
class EvaluationPipeline:
    """评标系统评估流程"""

    async def evaluate(self, test_cases: List[dict]):
        results = {}

        # 1. RAGAS 快速评估
        ragas_scores = await self.ragas_evaluate(test_cases)
        results["ragas"] = ragas_scores

        # 2. RAGChecker 细粒度诊断
        if ragas_scores["overall"] < 0.8:
            checker_results = await self.ragchecker_diagnose(test_cases)
            results["diagnosis"] = checker_results

            # 根据诊断结果定位问题
            if checker_results["retriever_metrics"]["claim_recall"] < 0.6:
                results["recommendation"] = "优化检索策略"
            elif checker_results["generator_metrics"]["hallucination"] > 0.1:
                results["recommendation"] = "优化生成约束"

        return results
```

---

*文档版本：v2.0*
*更新日期：2026-02-20*
*更新内容：添加 6 个 GitHub 项目的详细分析、评估框架集成建议*
