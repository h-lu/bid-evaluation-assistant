# 辅助评标专家系统 —— 端到端架构设计

> 版本：v2.0
> 设计日期：2026-02-20
> 更新日期：2026-02-20
> 状态：已批准

---

## 〇、研究来源说明

本设计参考了以下 GitHub 项目的深入研究：

| 项目 | 研究重点 | 借鉴内容 |
|------|----------|----------|
| **Agentic-Procure-Audit-AI** | Agent架构、评分算法 | RGSG工作流、TypedDict状态管理、评分可解释性 |
| **RAGFlow** | 文档解析、RAG架构 | 解析器注册表、位置追踪、混合检索、上下文附加 |

详细研究报告见：
- `docs/research/2026-02-20-agentic-procure-audit-ai-research.md`
- `docs/research/2026-02-20-ragflow-research.md`

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
| **文档解析** | MinerU 2.5 + PaddleOCR | PDF解析、扫描件识别 |
| **Embedding** | BGE-M3 | 多模式（稠密+稀疏+ColBERT） |
| **向量数据库** | ChromaDB（开发）/ Milvus（生产） | 向量存储 |
| **Reranker** | BGE-Reranker-v2-m3 | 重排序 |
| **Agent框架** | LangGraph + CrewAI | 状态机工作流 |
| **LLM** | DeepSeek / Qwen | 按职责分工 |
| **评估** | RAGAS + DeepEval | RAG评估 |
| **可观测性** | Langfuse | 私有化部署 |
| **后端API** | FastAPI + Pydantic v2 | 异步框架 |
| **前端** | Vue3 + Element Plus + Pinia | 评标界面 |

---

## 二、系统整体架构

### 2.1 架构选型：分层单体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              系统整体架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    前端层 (Vue3 + Element Plus)                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ 项目管理  │  │ 评审工作台│  │ 对比分析  │  │ 报告导出  │            │   │
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
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ 文档解析  │  │ RAG检索   │  │ Agent编排 │  │ 评分计算  │            │   │
│  │  │ Service  │  │ Service  │  │ Service  │  │ Service  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │   │
│  │  │ 用户管理  │  │ 项目管理  │  │ 报告生成  │                          │   │
│  │  │ Service  │  │ Service  │  │ Service  │                          │   │
│  │  └──────────┘  └──────────┘  └──────────┘                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         基础设施层                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ LLM抽象层 │  │ ChromaDB │  │PostgreSQL│  │  Redis   │            │   │
│  │  │(可切换)  │  │ (向量库) │  │ (关系库) │  │ (缓存)   │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

**分块策略（2026最佳实践）：**

| 文档类型 | 切分策略 | Chunk Size | 理由 |
|---------|---------|------------|------|
| 产品注册证 | 整页切分 | N/A | 原子性文档 |
| 技术参数表 | 按参数项切分 | 200-300 tokens | 独立检索 |
| 招标文件 | 按章节递归切分 | 500 tokens | 保留层级 |
| 法规条文 | 按条款切分 | 300 tokens | 独立引用 |

### 3.2 RAG检索模块（混合检索 + 位置追踪）

> **设计来源**: RAGFlow 混合检索、Agentic-Procure-Audit-AI 检索策略

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG检索模块                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   用户查询                                                   │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────┐                                           │
│   │ 查询理解    │ ──→ 意图识别 / 实体抽取                    │
│   └─────┬───────┘                                           │
│         │                                                   │
│   ┌─────┴───────────────────┐                              │
│   ▼                         ▼                              │
│ ┌─────────────┐       ┌─────────────┐                      │
│ │  向量检索   │       │  BM25检索   │                      │
│ │  (BGE-M3)   │       │  (精确匹配)  │                      │
│ │  稠密向量   │       │  稀疏向量   │                      │
│ └──────┬──────┘       └──────┬──────┘                      │
│        │                      │                            │
│        └──────────┬───────────┘                            │
│                   ▼                                        │
│   ┌───────────────────────────────────────┐                │
│   │        RRF融合 (Reciprocal Rank)       │                │
│   │  score = Σ 1/(k + rank_i), k=60       │                │
│   │  α=0.3 稀疏/稠密平衡                   │                │
│   └───────────────────┬───────────────────┘                │
│                       ▼                                    │
│   ┌───────────────────────────────────────┐                │
│   │        Reranker (BGE-Reranker-v2)      │                │
│   │        重排序 Top-50 → Top-10          │                │
│   └───────────────────┬───────────────────┘                │
│                       ▼                                    │
│   ┌───────────────────────────────────────┐                │
│   │  检索结果 + 位置信息（溯源引用）        │                │
│   │  [{                                    │                │
│   │    "content": "...",                  │                │
│   │    "score": 0.92,                     │                │
│   │    "positions": [(page, start, end)], │ ← 定位原文     │
│   │    "doc_id": "bid_001",               │                │
│   │    "metadata": {...}                  │                │
│   │  }]                                   │                │
│   └───────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**混合检索优势：**
- **向量检索**: 语义相似，处理同义词、改写
- **BM25检索**: 精确匹配，专业术语、型号、编号
- **RRF融合**: 结合两者优势，提升召回率

### 3.3 多Agent模块（RGSG工作流 + LangGraph状态机）

> **设计来源**: Agentic-Procure-Audit-AI 的 RGSG 模式

**RGSG = Retrieve - Grade - Search - Generate（自适应检索循环）**

```
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph 状态机工作流 (RGSG 模式)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   StateGraph<BidEvaluationState>                               │
│                                                                 │
│   ┌─────────┐                                                   │
│   │ START   │                                                   │
│   └────┬────┘                                                   │
│        ▼                                                        │
│   ┌─────────────────┐                                           │
│   │  Retrieve 节点   │  ← 向量检索 + BM25                        │
│   │  retrieve_node  │                                           │
│   └────────┬────────┘                                           │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐                                           │
│   │   Grade 节点     │  ← LLM评估检索结果相关性                  │
│   │   grade_node    │                                           │
│   └────────┬────────┘                                           │
│            │                                                    │
│      ┌─────┴─────┐                                              │
│      ▼           ▼                                              │
│   sufficient   needs_search                                     │
│      │           │                                              │
│      │           ▼                                              │
│      │    ┌─────────────────┐                                   │
│      │    │  Search 节点     │  ← 网络搜索/补充检索              │
│      │    │  web_search     │                                   │
│      │    └────────┬────────┘                                   │
│      │             │                                            │
│      │             │ (iteration++, 最多3次)                     │
│      │             └──────────────┐                             │
│      │                            │                             │
│      ▼                            ▼                             │
│   ┌─────────────────────────────────┐                          │
│   │        Generate 节点             │  ← 生成最终评估           │
│   │        generate_node            │                          │
│   └────────────────┬────────────────┘                          │
│                    │                                            │
│                    ▼                                            │
│   ┌─────────────────────────────────┐                          │
│   │       异常检测 + 人工审核决策     │                          │
│   └────────────────┬────────────────┘                          │
│                    │                                            │
│              ┌─────┴─────┐                                      │
│            正常        异常                                     │
│              │           │                                      │
│              ▼           ▼                                      │
│   ┌─────────────┐  ┌─────────────┐                             │
│   │  生成报告   │  │ 人工审核队列 │                             │
│   └──────┬──────┘  └─────────────┘                             │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────┐                                                   │
│   │   END   │                                                   │
│   └─────────┘                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**TypedDict 状态设计（支持字段累积）:**

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

## 六、评估监控层

### 6.1 RAGAS评估指标

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

> 本节总结了从 GitHub 研究项目中借鉴的核心设计模式

### 10.1 RGSG 工作流模式

**来源**: Agentic-Procure-Audit-AI

```
Retrieve → Grade → Search → Generate
    ↑          │
    └──────────┘ (迭代最多3次)
```

| 节点 | 职责 | 输出 |
|------|------|------|
| Retrieve | 向量 + BM25 混合检索 | retrieved_chunks |
| Grade | LLM 评估检索结果相关性 | grade_decision, relevance_score |
| Search | 本地不足时网络搜索 | web_search_results |
| Generate | 综合生成最终评估 | final_answer |

**适用场景**: 自适应检索，确保答案有据可依

### 10.2 TypedDict 状态管理

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

**优势**: 跨节点自动累积，无需手动合并

### 10.3 解析器注册表模式

**来源**: RAGFlow

```python
PARSERS = {
    "mineru": by_mineru,
    "paddleocr": by_paddleocr,
    "docx": by_docx,
}

def chunk(filename, parser_id="mineru", **kwargs):
    return PARSERS.get(parser_id, default)(filename, **kwargs)
```

**优势**: 开闭原则，新增解析器只需注册，无需修改现有代码

### 10.4 位置追踪机制

**来源**: RAGFlow

```python
@dataclass
class Chunk:
    content: str
    positions: list[tuple[int, int, int]]  # [(page, start, end)]
```

**应用**: 评标报告引用标书原文时可定位到具体页码和位置

### 10.5 评分可解释性

**来源**: Agentic-Procure-Audit-AI

```python
class ScoreWithReasoning(TypedDict):
    score: float          # 分数
    reasoning: str        # 评分理由
    evidence: list[str]   # 证据来源
    confidence: float     # 置信度
```

**原则**: 每个评分必须可追溯、可解释、可审计

### 10.6 混合检索 + RRF 融合

**来源**: RAGFlow / 2026 最佳实践

```
向量检索 ──┬──→ RRF融合 ──→ Reranker ──→ Top-K
BM25检索 ──┘
```

**RRF 公式**: `score = Σ 1/(k + rank_i)`, k=60

---

## 十、附录

### 10.1 核心依赖

```toml
# pyproject.toml
[project]
name = "bid-evaluation-assistant"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "magic-pdf[full]>=0.7.0",
    "paddleocr>=2.8.0",
    "chromadb>=0.5.0",
    "flagembedding>=1.2.0",
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "openai>=1.50.0",
    "dashscope>=1.20.0",
    "ragas>=0.1.0",
    "deepeval>=0.21.0",
    "langfuse>=2.0.0",
]
```

### 10.2 参考资料

**开源项目（直接使用）：**
- MinerU: https://github.com/opendatalab/MinerU
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- ChromaDB: https://github.com/chroma-core/chroma
- LangGraph: https://github.com/langchain-ai/langgraph
- RAGAS: https://github.com/explodinggradients/ragas
- DeepEval: https://github.com/confident-ai/deepeval
- Langfuse: https://github.com/langfuse/langfuse

**研究项目（借鉴设计）：**
- Agentic-Procure-Audit-AI: https://github.com/MrAliHasan/Agentic-Procure-Audit-AI
  - 借鉴：RGSG工作流、TypedDict状态管理、评分可解释性、四维评分框架
- RAGFlow: https://github.com/infiniflow/ragflow
  - 借鉴：解析器注册表模式、位置追踪机制、混合检索、上下文附加

---

*设计文档版本：v2.0*
*最后更新：2026-02-20*
*更新内容：融入 GitHub 项目研究发现的关键设计模式*
