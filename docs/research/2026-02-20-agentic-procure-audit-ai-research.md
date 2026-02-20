# Agentic-Procure-Audit-AI 深度研究报告

> 研究对象: https://github.com/MrAliHasan/Agentic-Procure-Audit-AI
> 研究日期: 2026-02-20
> 研究目的: 为辅助评标专家系统提供架构和设计参考

---

## 1. 项目概述

### 1.1 项目定位

**Agentic-Procure-Audit-AI** 是一个基于 AI 代理的采购智能审计系统，专注于：

- **采购订单智能分析**: 自动化分析采购订单，评估供应商资质
- **文档处理**: OCR + LLM 驱动的文档信息提取
- **供应商评分**: 多维度供应商评估与风险分析
- **市场调研**: 自主网络搜索补充本地知识库

### 1.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **LLM 框架** | LangGraph | 基于状态机的 Agent 工作流编排 |
| **本地 LLM** | Ollama + DeepSeek-R1 | 无需云端 API，完全本地化推理 |
| **向量数据库** | ChromaDB | 轻量级嵌入式向量存储 |
| **OCR 引擎** | Tesseract | 开源光学字符识别 |
| **Web 搜索** | Tavily / Serper API | 外部知识获取 |
| **文档处理** | PyMuPDF + Pillow | PDF 和图像处理 |

### 1.3 目录结构

```
Agentic-Procure-Audit-AI/
├── src/
│   ├── graphs/                 # LangGraph 工作流定义
│   │   ├── states.py          # 状态类型定义 (TypedDict)
│   │   ├── order_intelligence.py    # 主工作流: 检索-评估-搜索-生成
│   │   ├── vendor_analysis.py       # 供应商分析工作流
│   │   └── document_processing.py   # 文档处理工作流
│   ├── processors/             # 业务处理器
│   │   ├── vendor_grader.py   # 供应商评分核心逻辑
│   │   └── document_processor.py    # 文档处理管道
│   ├── tools/                  # 工具函数
│   │   ├── bid_extractor.py   # 标书信息提取
│   │   ├── web_search.py      # 网络搜索集成
│   │   └── embeddings.py      # 向量嵌入工具
│   ├── config/                 # 配置管理
│   │   └── settings.py        # Pydantic 设置模型
│   └── utils/                  # 通用工具
│       └── context_optimizer.py    # LLM 上下文优化
├── data/
│   ├── documents/             # 原始文档存储
│   ├── vectors/               # ChromaDB 向量存储
│   └── processed/             # 处理后数据
└── tests/
```

---

## 2. Agent 架构分析

### 2.1 核心设计模式: Retrieve-Grade-Search-Generate (RGSG)

该项目采用了一个**四阶段闭环 Agentic 工作流**，这是非常值得借鉴的设计：

```
┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌────────────┐
│ Retrieve │───>│  Grade  │───>│   Decision   │───>│  Generate  │
│ (检索)   │    │ (评估)   │    │  (决策路由)   │    │  (生成)    │
└─────────┘    └─────────┘    └──────────────┘    └────────────┘
      ▲                              │                    │
      │                              ▼                    │
      │                      ┌─────────────┐              │
      └──────────────────────│ Web Search  │──────────────┘
                             │ (网络搜索)   │
                             └─────────────┘
```

### 2.2 Agent 节点职责

#### 2.2.1 `retrieve_node` - 检索节点

```python
# 职责：从 ChromaDB 检索相关供应商和文档
async def retrieve_node(state: OrderIntelligenceState) -> dict:
    query = state["query"]

    # 1. 检索供应商向量
    vendors = await vector_store.search_vendors(query, k=5)

    # 2. 检索相关文档
    documents = await vector_store.search_documents(query, k=10)

    return {
        "vendors": vendors,
        "documents": documents
    }
```

**关键设计点**：
- 分离供应商和文档的检索通道
- 支持元数据过滤（按地区、行业等）

#### 2.2.2 `grade_node` - 评估节点

```python
# 职责：LLM 评估检索结果的相关性
async def grade_node(state: OrderIntelligenceState) -> dict:
    prompt = f"""
    评估以下检索结果是否足以回答用户查询。

    查询: {state['query']}
    检索到的供应商: {state['vendors']}
    检索到的文档: {state['documents']}

    输出 JSON:
    {{
        "relevance_score": 0.0-1.0,
        "decision": "sufficient" | "needs_search",
        "reasoning": "..."
    }}
    """

    result = await llm.ainvoke(prompt)
    return {
        "grade_decision": result.decision,
        "relevance_scores": [result.relevance_score],
        "reasoning_steps": [result.reasoning]
    }
```

**关键设计点**：
- 使用 LLM 做相关性判断，而非简单的向量相似度
- 输出结构化决策结果，便于后续路由

#### 2.2.3 `web_search_node` - 网络搜索节点

```python
# 职责：本地知识不足时，从网络获取补充信息
async def web_search_node(state: OrderIntelligenceState) -> dict:
    # 1. 生成搜索查询
    queries = await generate_search_queries(state["query"], state["vendors"])
    state["web_search_queries"].extend(queries)

    # 2. 执行搜索
    results = []
    for query in queries:
        result = await tavily_client.search(query)
        results.append(result)

    return {
        "web_results": results,
        "reasoning_steps": [f"执行网络搜索: {len(queries)} 个查询"]
    }
```

**关键设计点**：
- 动态生成搜索查询，而非直接使用原始问题
- 支持多轮迭代搜索（通过 `iteration` 计数器）

#### 2.2.4 `generate_node` - 生成节点

```python
# 职责：综合所有信息，生成最终分析报告
async def generate_node(state: OrderIntelligenceState) -> dict:
    context = optimize_context(
        vendors=state["vendors"],
        documents=state["documents"],
        web_results=state["web_results"],
        max_tokens=4000
    )

    prompt = f"""
    基于以下信息，生成供应商分析报告：

    查询: {state['query']}
    评估标准: {state['criteria']}

    可用数据:
    {context}

    输出要求:
    1. 供应商对比分析
    2. 优劣势评估
    3. 风险提示
    4. 推荐建议
    """

    result = await llm.ainvoke(prompt)
    return {
        "final_answer": result.content,
        "analysis": result.structured_output
    }
```

### 2.3 状态管理设计

使用 **TypedDict** 定义强类型状态，这是 LangGraph 的最佳实践：

```python
from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages

class OrderIntelligenceState(TypedDict):
    # 输入
    query: str
    criteria: list[str]

    # 检索结果
    vendors: list[dict]
    documents: list[dict]
    web_results: list[dict]

    # 累积字段 (使用 Annotated[list, add] 实现追加)
    web_search_queries: Annotated[list[str], add]
    reasoning_steps: Annotated[list[str], add]

    # 决策字段
    grade_decision: str  # "sufficient" | "needs_search"
    relevance_scores: list[float]

    # 输出
    analysis: Optional[dict]
    bid_variables: Optional[dict]
    final_answer: str

    # 控制
    iteration: int
    max_iterations: int
    error: Optional[str]
```

**关键设计点**：
- `Annotated[list[str], add]` 实现跨节点的列表累积
- 区分输入、中间、输出字段
- 包含错误处理和控制字段

### 2.4 路由决策

```python
def decide_to_search(state: OrderIntelligenceState) -> str:
    """条件边：决定是否需要网络搜索"""

    # 1. 检查相关性决策
    if state["grade_decision"] == "sufficient":
        return "generate"

    # 2. 检查迭代次数
    if state["iteration"] >= state["max_iterations"]:
        return "generate"  # 强制结束

    # 3. 需要搜索
    return "search"
```

---

## 3. 文档处理流程

### 3.1 处理管道

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│ 文档上传    │───>│ OCR 提取   │───>│ 类型检测   │───>│ 字段提取   │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
                                                             │
                      ┌────────────┐    ┌────────────┐       │
                      │ 向量存储   │<───│ 字段验证   │<──────┘
                      └────────────┘    └────────────┘
```

### 3.2 OCR 实现

```python
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

class DocumentProcessor:
    async def extract_text(self, file_path: str) -> str:
        """多格式文档文本提取"""

        if file_path.endswith('.pdf'):
            # PDF 处理
            doc = fitz.open(file_path)
            text_parts = []

            for page in doc:
                # 1. 尝试直接提取文本
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
                else:
                    # 2. 扫描版 PDF，转图像后 OCR
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                    text_parts.append(ocr_text)

            return "\n".join(text_parts)

        elif file_path.endswith(('.png', '.jpg', '.jpeg')):
            # 图像直接 OCR
            img = Image.open(file_path)
            return pytesseract.image_to_string(img, lang='chi_sim+eng')
```

**关键设计点**：
- PDF 优先尝试直接提取文本，失败再 OCR
- 支持中英文混合识别 (`chi_sim+eng`)
- 高 DPI (300) 确保识别质量

### 3.3 文档类型检测

```python
class DocumentProcessor:
    DOCUMENT_TYPES = {
        "invoice": {
            "keywords": ["发票", "Invoice", "金额", "合计"],
            "required_fields": ["vendor_name", "invoice_number", "total_amount"]
        },
        "contract": {
            "keywords": ["合同", "Contract", "甲方", "乙方"],
            "required_fields": ["parties", "effective_date", "contract_value"]
        },
        "bid": {
            "keywords": ["投标", "Bid", "报价", "标书"],
            "required_fields": ["vendor_name", "bid_date", "total_price"]
        }
    }

    def detect_document_type(self, text: str) -> str:
        """基于关键词的文档类型检测"""
        scores = {}
        for doc_type, config in self.DOCUMENT_TYPES.items():
            score = sum(1 for kw in config["keywords"] if kw in text)
            scores[doc_type] = score

        return max(scores, key=scores.get)
```

### 3.4 信息提取 (BidExtractor)

```python
class BidExtractor:
    # 货币识别模式
    CURRENCY_PATTERNS = {
        "PKR": ["Rs", "PKR", "rupees", "卢比"],
        "USD": ["$", "USD", "dollars", "美元"],
        "EUR": ["€", "EUR", "euros", "欧元"],
        "CNY": ["¥", "CNY", "RMB", "人民币", "元"]
    }

    # 价格提取模式
    PRICE_PATTERN = r"([\d,]+(?:\.\d{1,2})?)"

    def extract_from_text(
        self,
        text: str,
        source: str = "document",
        llm_analysis: dict = None,
        query_context: str = ""
    ) -> BidVariables:
        """
        混合提取策略：正则 + LLM 增强
        """

        # 1. 正则提取基础字段
        vendor_names = self._extract_vendor_names(text, query_context)
        prices = self._extract_prices(text)
        dates = self._extract_dates(text)

        # 2. LLM 增强提取（复杂字段）
        if llm_analysis:
            specifications = llm_analysis.get("specifications", [])
            delivery_terms = llm_analysis.get("delivery_terms", "")
            warranty = llm_analysis.get("warranty", "")

        # 3. 合并结果，计算置信度
        return BidVariables(
            vendor_name=vendor_names[0] if vendor_names else None,
            vendor_confidence=1.0 if vendor_names else 0.0,
            total_price=prices[0] if prices else None,
            # ...
        )

    def _extract_vendor_names(self, text: str, query_context: str) -> list[str]:
        """查询感知的供应商提取"""

        # 策略 1：如果查询中提到供应商，优先匹配
        if query_context:
            # 提取查询中的供应商名称
            mentioned_vendors = self._extract_entity_names(query_context)
            for vendor in mentioned_vendors:
                if vendor in text:
                    return [vendor]

        # 策略 2：从文档中提取常见模式
        patterns = [
            r"供应商[：:]\s*(.+)",
            r"公司名称[：:]\s*(.+)",
            r"Company[：:]\s*(.+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return [m.strip() for m in matches]

        return []
```

**关键设计点**：
- **查询感知提取**：优先匹配用户查询中提到的供应商
- **混合策略**：正则处理结构化字段，LLM 处理非结构化内容
- **置信度评分**：每个字段都有置信度，便于后续决策

---

## 4. 评分算法

### 4.1 多维度评分框架

```python
class VendorGrader:
    # 默认权重配置
    DEFAULT_WEIGHTS = {
        "price": 0.30,        # 价格竞争力
        "quality": 0.25,      # 质量/技术能力
        "reliability": 0.25,  # 可靠性/交付能力
        "risk": 0.20          # 风险评估（越低越好）
    }

    def __init__(self, weights: dict = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    async def grade(
        self,
        vendor_name: str,
        vendor_data: dict,
        criteria: list[str] = None,
        web_research: list[dict] = None
    ) -> VendorAnalysis:
        """
        供应商综合评分

        Args:
            vendor_name: 供应商名称
            vendor_data: 供应商数据（来自向量库）
            criteria: 自定义评估标准
            web_research: 网络调研结果

        Returns:
            VendorAnalysis: 包含各项评分和推荐结果
        """
```

### 4.2 评分维度定义

| 维度 | 评分范围 | 评估内容 |
|------|----------|----------|
| **Price** | 0-100 | 价格竞争力、性价比 |
| **Quality** | 0-100 | 技术能力、产品质量、认证资质 |
| **Reliability** | 0-100 | 历史交付表现、响应速度、服务态度 |
| **Risk** | 0-100 | 财务风险、合规风险、供应链风险 |

### 4.3 LLM 驱动的评分实现

```python
async def grade(self, vendor_name: str, vendor_data: dict, ...) -> VendorAnalysis:

    # 构建评分 Prompt
    prompt = f"""
    作为采购专家，请对以下供应商进行多维度评估。

    供应商: {vendor_name}

    可用信息:
    - 历史数据: {json.dumps(vendor_data, ensure_ascii=False)}
    - 网络调研: {json.dumps(web_research, ensure_ascii=False)}
    - 评估标准: {criteria}

    请输出 JSON 格式的评分：
    {{
        "price_score": <0-100>,
        "price_reasoning": "<评分理由>",
        "quality_score": <0-100>,
        "quality_reasoning": "<评分理由>",
        "reliability_score": <0-100>,
        "reliability_reasoning": "<评分理由>",
        "risk_score": <0-100>,
        "risk_reasoning": "<评分理由>",
        "overall_assessment": "<综合评价>",
        "recommendation": "<APPROVED / REVIEW / REJECTED>"
    }}
    """

    result = await self.llm.ainvoke(prompt)
    scores = json.loads(result.content)

    # 计算加权总分
    total_score = (
        scores["price_score"] * self.weights["price"] +
        scores["quality_score"] * self.weights["quality"] +
        scores["reliability_score"] * self.weights["reliability"] +
        scores["risk_score"] * self.weights["risk"]
    )

    return VendorAnalysis(
        vendor_name=vendor_name,
        price_score=scores["price_score"],
        quality_score=scores["quality_score"],
        reliability_score=scores["reliability_score"],
        risk_score=scores["risk_score"],
        total_score=total_score,
        price_reasoning=scores["price_reasoning"],
        quality_reasoning=scores["quality_reasoning"],
        reliability_reasoning=scores["reliability_reasoning"],
        risk_reasoning=scores["risk_reasoning"],
        overall_assessment=scores["overall_assessment"],
        recommendation=self._determine_recommendation(total_score)
    )
```

### 4.4 推荐决策逻辑

```python
def _determine_recommendation(self, total_score: float) -> str:
    """基于总分确定推荐结果"""
    if total_score >= 70:
        return "APPROVED"   # 推荐中标
    elif total_score >= 50:
        return "REVIEW"     # 需要进一步审查
    else:
        return "REJECTED"   # 不推荐
```

### 4.5 可解释性设计

每个评分维度都包含 **reasoning（评分理由）**，这是确保 AI 决策透明度的关键：

```python
@dataclass
class VendorAnalysis:
    vendor_name: str

    # 评分
    price_score: float
    quality_score: float
    reliability_score: float
    risk_score: float
    total_score: float

    # 评分理由（可解释性）
    price_reasoning: str
    quality_reasoning: str
    reliability_reasoning: str
    risk_reasoning: str

    # 综合评估
    overall_assessment: str
    recommendation: str
```

---

## 5. RAG 实现

### 5.1 向量存储架构

```
┌─────────────────────────────────────────────────────────┐
│                    ChromaDB                              │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ vendors     │    │ documents   │    │ contracts   │  │
│  │ (供应商)    │    │ (文档)      │    │ (合同)      │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                         │
│  Embedding: sentence-transformers/all-MiniLM-L6-v2     │
│  Distance: cosine similarity                            │
└─────────────────────────────────────────────────────────┘
```

### 5.2 嵌入生成

```python
from chromadb.utils import embedding_functions

class VectorStore:
    def __init__(self, persist_directory: str = "./data/vectors"):
        self.client = chromadb.PersistentClient(path=persist_directory)

        # 使用本地嵌入模型（无需 API）
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # 创建集合
        self.vendors = self.client.get_or_create_collection(
            name="vendors",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

        self.documents = self.client.get_or_create_collection(
            name="documents",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
```

### 5.3 索引策略

```python
async def index_vendor(self, vendor_data: dict):
    """索引供应商信息"""

    # 构建文档文本
    doc_text = f"""
    供应商名称: {vendor_data['name']}
    行业: {vendor_data['industry']}
    地区: {vendor_data['region']}
    主营业务: {vendor_data['business_scope']}
    历史表现: {vendor_data.get('performance_history', '暂无')}
    认证资质: {', '.join(vendor_data.get('certifications', []))}
    """

    # 添加到向量库
    self.vendors.add(
        documents=[doc_text],
        metadatas=[{
            "name": vendor_data['name'],
            "industry": vendor_data['industry'],
            "region": vendor_data['region'],
            "indexed_at": datetime.now().isoformat()
        }],
        ids=[f"vendor_{vendor_data['id']}"]
    )
```

### 5.4 检索策略

```python
async def search_vendors(
    self,
    query: str,
    k: int = 5,
    filters: dict = None
) -> list[dict]:
    """
    混合检索：向量相似度 + 元数据过滤
    """

    # 构建过滤条件
    where_filter = None
    if filters:
        conditions = []
        if filters.get("industry"):
            conditions.append({"industry": filters["industry"]})
        if filters.get("region"):
            conditions.append({"region": filters["region"]})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

    # 执行检索
    results = self.vendors.query(
        query_texts=[query],
        n_results=k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    return self._format_results(results)
```

### 5.5 上下文优化

```python
class ContextOptimizer:
    """LLM 上下文窗口优化器"""

    def __init__(self, max_tokens: int = 4000, tokenizer: str = "cl100k_base"):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(tokenizer)

    def optimize(
        self,
        vendors: list[dict],
        documents: list[dict],
        web_results: list[dict]
    ) -> str:
        """
        智能压缩上下文，确保不超过 token 限制
        """

        # 1. 按相关性排序
        all_items = [
            *[(v, "vendor", v.get("distance", 0)) for v in vendors],
            *[(d, "document", d.get("distance", 0)) for d in documents],
            *[(w, "web", w.get("relevance", 0)) for w in web_results]
        ]
        all_items.sort(key=lambda x: x[2], reverse=True)

        # 2. 逐步添加，直到达到限制
        context_parts = []
        current_tokens = 0

        for item, item_type, _ in all_items:
            item_text = self._format_item(item, item_type)
            item_tokens = len(self.encoding.encode(item_text))

            if current_tokens + item_tokens > self.max_tokens:
                # 尝试压缩
                compressed = self._compress_item(item, item_type, remaining_tokens=self.max_tokens - current_tokens)
                if compressed:
                    context_parts.append(compressed)
                break

            context_parts.append(item_text)
            current_tokens += item_tokens

        return "\n\n---\n\n".join(context_parts)

    def _compress_item(self, item: dict, item_type: str, remaining_tokens: int) -> str:
        """压缩单项内容"""
        # 提取最关键的字段
        if item_type == "vendor":
            return f"供应商: {item.get('name')} - 评分: {item.get('score', 'N/A')}"
        elif item_type == "document":
            return f"文档: {item.get('title')[:100]}..."
        else:
            return item.get('summary', '')[:remaining_tokens * 4]
```

---

## 6. 可借鉴的设计与模式

### 6.1 推荐采用的设计

#### 6.1.1 **RGSG 工作流模式**

```
Retrieve → Grade → [Search] → Generate
```

**优点**：
- 智能决策是否需要外部搜索
- 避免不必要的 API 调用
- 支持迭代优化

**应用场景**：评标系统中，先从本地标书库检索，不足时再搜索市场信息

#### 6.1.2 **TypedDict 状态管理**

```python
class EvaluationState(TypedDict):
    # 输入
    tender_id: str
    evaluation_criteria: list[str]

    # 累积
    reasoning_steps: Annotated[list[str], add]

    # 决策
    current_phase: str

    # 输出
    scores: dict[str, float]
    recommendation: str
```

**优点**：
- 类型安全，IDE 友好
- 清晰的数据流
- 支持增量更新

#### 6.1.3 **混合提取策略**

```
正则表达式 (结构化字段) + LLM (非结构化内容) = 高准确率 + 低成本
```

**应用场景**：
- 正则提取：金额、日期、编号
- LLM 提取：技术方案、服务承诺、创新能力

#### 6.1.4 **查询感知提取**

```python
def extract_with_context(text: str, user_query: str) -> dict:
    """
    优先提取与用户查询相关的信息
    """
    mentioned_entities = extract_entities(user_query)
    # 优先匹配查询中提到的实体
    ...
```

**优点**：提高提取相关性，减少噪音

#### 6.1.5 **可解释评分**

```python
@dataclass
class ScoreResult:
    score: float
    reasoning: str  # 必须包含评分理由
    evidence: list[str]  # 支持证据
```

**优点**：
- 符合招投标法规要求
- 便于审计追溯
- 增强用户信任

### 6.2 需要改进的设计

#### 6.2.1 **文档类型检测**

**当前实现**：基于关键词匹配

**改进建议**：结合规则 + LLM 分类器

```python
async def detect_document_type(self, text: str) -> str:
    # 1. 规则快速筛选
    rule_scores = self._keyword_matching(text)

    # 2. 如果规则不确定，使用 LLM
    if max(rule_scores.values()) < 0.7:
        return await self._llm_classify(text)

    return max(rule_scores, key=rule_scores.get)
```

#### 6.2.2 **评分一致性**

**问题**：纯 LLM 评分可能不一致

**改进建议**：引入校准机制

```python
async def grade_with_calibration(self, vendor_data: dict) -> VendorAnalysis:
    # 1. LLM 初评
    initial_scores = await self._llm_grade(vendor_data)

    # 2. 历史校准
    calibrated_scores = self._calibrate_against_history(
        initial_scores,
        vendor_data["vendor_id"]
    )

    # 3. 一致性检查
    if not self._check_consistency(calibrated_scores):
        # 触发人工审核
        calibrated_scores["requires_review"] = True

    return calibrated_scores
```

#### 6.2.3 **OCR 后处理**

**问题**：OCR 输出可能包含错误

**改进建议**：添加 LLM 纠错层

```python
async def extract_with_correction(self, text: str) -> dict:
    # 1. 原始提取
    raw_result = self._regex_extract(text)

    # 2. LLM 纠错
    correction_prompt = f"""
    以下是从 OCR 识别的文本中提取的信息，请纠正可能的错误：

    原文片段: {text[:500]}
    提取结果: {json.dumps(raw_result)}

    请输出纠正后的结果。
    """

    corrected = await self.llm.ainvoke(correction_prompt)
    return json.loads(corrected)
```

### 6.3 反模式警示

#### 6.3.1 **避免过度依赖单一来源**

```python
# 错误示例：只使用 LLM 评分
score = await llm.grade(vendor_data)

# 正确示例：多来源交叉验证
scores = [
    await llm_grade(vendor_data),
    calculate_statistical_score(vendor_history),
    get_external_rating(vendor_id)
]
final_score = weighted_average(scores)
```

#### 6.3.2 **避免无状态设计**

```python
# 错误示例：每次都重新加载
def evaluate(vendor_id):
    vendor = load_vendor(vendor_id)
    return grade(vendor)

# 正确示例：维护状态和缓存
class EvaluationSession:
    def __init__(self):
        self.vendor_cache = {}
        self.scoring_history = []

    async def evaluate(self, vendor_id):
        if vendor_id not in self.vendor_cache:
            self.vendor_cache[vendor_id] = await load_vendor(vendor_id)
        return self.grade(self.vendor_cache[vendor_id])
```

#### 6.3.3 **避免不可解释的决策**

```python
# 错误示例：黑盒输出
result = await llm.generate(f"评估供应商: {vendor_name}")
return result

# 正确示例：结构化输出 + 推理链
result = await llm.generate(
    f"评估供应商: {vendor_name}",
    response_format={
        "score": "float",
        "reasoning": "string",
        "evidence": "list[string]",
        "confidence": "float"
    }
)
```

---

## 7. 对辅助评标专家系统的建议

### 7.1 架构层面

1. **采用 RGSG 模式**：评标流程天然契合这个模式
   - Retrieve: 从标书库检索相关信息
   - Grade: 评估信息是否充分
   - Search: 必要时搜索市场价格、资质验证
   - Generate: 生成评标报告

2. **状态机设计**：使用 LangGraph 管理评标流程
   - 标书解析阶段
   - 技术评审阶段
   - 商务评审阶段
   - 综合评分阶段
   - 报告生成阶段

3. **多 Agent 协作**：
   - 文档处理 Agent：负责标书解析
   - 技术评审 Agent：负责技术方案评估
   - 商务评审 Agent：负责价格、商务条款评估
   - 合规审查 Agent：负责资质、合规检查
   - 协调 Agent：负责汇总和生成报告

### 7.2 功能层面

1. **评分维度**：
   - 技术评分 (30%): 技术方案、创新性、可行性
   - 商务评分 (30%): 报价合理性、付款条件
   - 资质评分 (20%): 企业资质、业绩案例
   - 服务评分 (20%): 售后服务、响应承诺

2. **可解释性**：
   - 每项评分必须有理由
   - 引用标书原文作为证据
   - 生成评分对比表格

3. **合规性**：
   - 评标过程可追溯
   - 支持 excel 导出标准格式
   - 保留评审日志

### 7.3 技术选型建议

| 需求 | 推荐方案 | 理由 |
|------|----------|------|
| Agent 框架 | LangGraph | 状态管理清晰，可视化支持好 |
| 本地 LLM | Ollama + Qwen2.5 | 中文能力强，部署简单 |
| 向量数据库 | ChromaDB | 轻量级，适合中小规模 |
| OCR | Tesseract + PaddleOCR | 中文支持好，开源免费 |
| 文档处理 | PyMuPDF | PDF 处理能力强 |

---

## 8. 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Ollama 官方网站](https://ollama.ai/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [原项目地址](https://github.com/MrAliHasan/Agentic-Procure-Audit-AI)

---

*报告完成于 2026-02-20*
