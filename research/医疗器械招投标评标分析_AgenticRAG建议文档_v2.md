# 医疗器械招投标评标分析系统 —— Agentic RAG 设计建议文档（完整版）

> 基于《LLM 时代的文本智能与商务应用》教材 + 行业最佳实践 + Context7 技术文档

---

## 1. 项目背景与核心挑战

### 1.1 医疗器械招投标的市场规模与痛点

根据百炼智能知了标讯数据（截至 2024 年 4 月）：
- **中标数量**：176,390 个
- **中标总金额**：12,577 亿元
- **经销商数量**：61,802 家
- **参与医院**：6,514 家

**行业三大痛点**：

| 痛点 | 传统解决方案的局限 | Agentic RAG 的解决思路 |
|-----|------------------|---------------------|
| **信息获取效率低** | 人工查阅数百页招标文件和附件，耗时费力 | 智能 OCR + RAG 检索，自动提取关键信息 |
| **名称变种复杂** | 同一器械在不同招标中名称不同，难以统一 | 知识图谱 + Embedding 语义匹配 |
| **多层销售网络** | 品牌商→经销商→医院三层架构，信息不透明 | 多智能体追踪各主体关系 |

### 1.2 医疗器械招投标的特殊性

- **技术复杂性高**：涉及设备参数、技术指标、临床验证、售后服务等多维度评估
- **法规约束严格**：需符合《招标投标法》《政府采购法》《医疗器械监督管理条例》等法规
- **数据量大**：单份招标文件可能数百页，涉及多个投标方、历史项目、产品注册证等资料
- **风险控制要求高**：评标结果需可追溯、可审计、经得起质疑

### 1.3 传统 RAG 的局限性

教材 Week 03-04 指出，传统 RAG（检索增强生成）面临三大问题：

| 问题类型 | 具体表现 | 在招投标场景的影响 |
|---------|---------|-------------------|
| **精确匹配失败** | 向量检索会混淆"2024年"和"2023年"、混淆相似型号 | 可能把A厂商的注册证信息匹配到B厂商 |
| **检索噪音过多** | 检索结果混入大量无关内容 | 评标依据不精准，影响公正性 |
| **缺乏推理能力** | 只能检索和总结，无法深度分析 | 无法自动进行技术参数对比、合规性审查 |

### 1.4 Agentic RAG 的解决方案

根据教材 Week 05-06 和行业最佳实践，**Agentic RAG** 引入智能体能力，实现：
- **自主检索**：根据任务需要动态决定检索什么、何时检索（而非一次性检索）
- **多步推理**：规划 → 检索 → 分析 → 验证 → 生成报告的完整流程
- **专业分工**：不同 Agent 负责不同评标维度（技术、商务、合规）
- **自我反思**：低置信度时自动重新分析（Self-Reflective RAG）

---

## 2. Agentic RAG 架构类型选型（基于行业最佳实践）

根据 Analytics Vidhya 2025 年 Agentic RAG 系统架构综述，以下是 7 种主要架构及其适用场景：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Agentic RAG 架构选型矩阵                                │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ 架构类型                  │ 适用场景                                          │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 1. Agentic RAG Router     │ 需要动态路由到不同知识库的查询（如区分法规/技术/商务）│
│ 2. Query Planning RAG     │ 复杂多步骤查询，需要分解子任务                       │
│ 3. Adaptive RAG           │ 查询类型多变，需要自适应策略                         │
│ 4. Corrective RAG         │ 高准确性要求，需要事实校验和纠错                     │
│ 5. Self-Reflective RAG    │ 需要迭代自我评估和修正（推荐用于评标场景）            │
│ 6. Speculative RAG        │ 需要快速响应，可接受一定不确定性                     │
│ 7. Self-Route RAG         │ 简单查询直接回答，复杂查询才检索                     │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

### 2.1 推荐架构：Self-Reflective RAG（自我反思型）

**推荐理由**：
- 医疗器械评标对准确性要求极高，需要**可追溯的推理过程**
- 支持**迭代验证**：置信度低于阈值时自动重新分析
- 与医疗领域多智能体研究（Thakrar et al., 2025）的结论一致

**架构流程**：

```
用户查询（如"评估某品牌CT机的技术参数是否符合要求"）
         │
         ▼
┌─────────────────────────────────────┐
│  Step 1: 初始检索与生成               │
│  - 检索招标文件要求                   │
│  - 检索投标方技术参数                 │
│  - 生成初步评估结论                   │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  Step 2: 自我反思（Self-Reflection）  │
│  - 置信度评分（0-1）                  │
│  - 识别推理漏洞或缺失证据              │
└──────────────────┬──────────────────┘
                   │
         ┌─────────┴─────────┐
         │ 置信度 ≥ 0.75      │ 置信度 < 0.75
         │                   │
         ▼                   ▼
   输出最终结果         重新分析（Re-Analysis）
                        - 补充检索
                        - 修正推理
                        - 回到 Step 2
```

### 2.2 补充架构：Agentic RAG Router（路由型）

用于根据查询类型自动路由到不同的专业 Agent：

```python
# 路由决策示例
ROUTER_DECISION = {
    "查询": "该产品的注册证是否覆盖招标范围？",
    "路由": "compliance_agent",  # 路由到合规审查Agent
    "原因": "涉及注册证有效性验证"
}

ROUTER_DECISION = {
    "查询": "三家投标方的技术参数如何对比？",
    "路由": "comparison_agent",  # 路由到对比分析Agent
    "原因": "需要多文档交叉分析"
}
```

---

## 3. 系统架构设计

### 3.1 整体架构（基于教材 Week 08 端到端设计）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway (FastAPI)                        │
│                    鉴权、限流、审计日志、权限控制                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Workflow Orchestrator                           │
│              评标任务分解、Agent 调度、流程编排                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────┬─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼             ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ 合规审查  │   │ 技术评审  │   │ 商务评审  │   │  对比分析  │   │  终审评估  │
│  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Agentic RAG Layer                               │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│    │ 向量检索  │  │ BM25检索 │  │ 重排序   │  │ 混合融合 │           │
│    │(语义理解)│  │(精确匹配)│  │(Cross-En)│  │  (RRF)   │           │
│    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│         └─────────────┴─────────────┴─────────────┘                  │
│                              │                                       │
│                              ▼                                       │
│    ┌─────────────────────────────────────────────────────┐           │
│    │              Knowledge Base (知识库)                 │           │
│    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │           │
│    │  │ 招标文件 │ │ 投标文件 │ │ 法规标准 │ │ 历史数据 │ │           │
│    │  │  (PDF)   │ │  (PDF)   │ │ (Markdown)│ │  (JSON) │ │           │
│    │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │           │
│    └─────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Observability (可观测性)                          │
│         评标过程追溯、成本监控、质量评估、审计日志                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 多智能体评标架构（基于教材 Week 06 + LangChain Supervisor Pattern）

根据 LangChain Context7 文档推荐的 **Supervisor Pattern**：

```python
"""
医疗器械评标多智能体系统架构
基于 LangChain Supervisor Pattern（Context7: /websites/langchain）
"""

# Step 1: 底层工具定义
@tool
def verify_registration_certificate(cert_no: str, product_name: str) -> dict:
    """验证医疗器械注册证有效性和适用范围"""
    pass

@tool
def extract_technical_params(document: str) -> list:
    """从投标文件中提取技术参数"""
    pass

@tool
def search_regulations(query: str) -> list[Document]:
    """检索相关法规条文"""
    pass

# Step 2: 专业子 Agent（基于教材 Week 06）
compliance_agent = create_agent(
    model="gpt-4o",
    tools=[verify_registration_certificate, search_regulations],
    system_prompt="""你是医疗器械合规审查专家。
    你的职责：
    1. 验证投标方资质文件的真实性和有效性
    2. 检查医疗器械注册证是否覆盖招标范围
    3. 识别合规风险点并给出明确结论
    4. 所有结论必须基于检索到的法规依据
    """
)

technical_agent = create_agent(
    model="gpt-4o",
    tools=[extract_technical_params, search_documents],
    system_prompt="""你是医疗器械技术评审专家。
    你的职责：
    1. 提取并理解招标文件的技术要求
    2. 逐条对比投标方的技术参数响应
    3. 识别正偏离、负偏离和无偏离项
    4. 评估技术方案的可行性和先进性
    """
)

# Step 3: 将子 Agent 包装为工具（Supervisor Pattern）
@tool
def review_compliance(bid_document: str) -> str:
    """对投标文件进行合规审查"""
    result = compliance_agent.invoke({
        "messages": [{"role": "user", "content": bid_document}]
    })
    return result["messages"][-1].content

@tool
def review_technical(bid_document: str, requirements: list) -> str:
    """对投标文件进行技术评审"""
    result = technical_agent.invoke({
        "messages": [{"role": "user", "content": f"评审文件：{bid_document}\n要求：{requirements}"}]
    })
    return result["messages"][-1].content

# Step 4: Supervisor Agent（规划者-协调者）
supervisor_agent = create_agent(
    model="gpt-4o",
    tools=[review_compliance, review_technical, review_commercial, compare_bids],
    system_prompt="""你是医疗器械评标 Supervisor。
    你的职责：
    1. 理解评标任务的整体需求
    2. 协调各专业 Agent 完成评审
    3. 整合各维度评审结果
    4. 生成最终的评标报告
    
    工作流程：
    - 首先调用合规审查 Agent，如未通过则终止
    - 然后并行调用技术评审和商务评审 Agent
    - 最后调用对比分析生成最终建议
    """
)
```

---

## 4. 核心模块设计

### 4.1 Agentic RAG 检索层（基于教材 Week 03-04 + 行业最佳实践）

#### 4.1.1 混合检索策略（Advanced RAG）

根据 LeewayHertz Advanced RAG 研究（Databricks 数据）：
- **60%** 的企业 LLM 应用使用 RAG
- **RAG 响应比纯微调准确 43%**

```python
class TenderHybridRetriever:
    """
    医疗器械招投标混合检索器
    结合向量检索（语义理解）+ BM25（精确匹配）+ 重排序
    """
    
    def __init__(self):
        # 向量检索 - 处理语义相似问题
        self.vector_store = ChromaDB(
            embedding_model="text-embedding-3-small",
            collection_name="tender_docs"
        )
        
        # BM25 - 处理精确匹配（注册证号、型号、年份）
        self.bm25_index = BM25Okapi()
        
        # 重排序 - 提升精确度（Cross-Encoder）
        self.reranker = CrossEncoder('BAAI/bge-reranker-base')
        
        # 知识图谱（可选）- 处理实体关系
        self.knowledge_graph = Neo4jGraph()
    
    def search(self, query: str, filters: dict = None) -> list[Document]:
        """
        混合检索流程（教材 Week 04 RRF 融合）
        """
        # 1. 向量检索（Top-K=20）- 捕获语义相似
        vec_results = self.vector_store.similarity_search(query, k=20)
        
        # 2. BM25检索（Top-K=20）- 精确匹配型号、注册证号
        tokenized_query = jieba.lcut(query)
        bm25_results = self.bm25_index.get_top_n(tokenized_query, n=20)
        
        # 3. RRF融合（Reciprocal Rank Fusion）
        # 教材公式：score = Σ 1/(k + rank), k=60
        fused_results = self.reciprocal_rank_fusion(
            vec_results, bm25_results, k=60, alpha=0.5
        )
        
        # 4. Cross-Encoder 重排序
        reranked = self.reranker.rerank(query, fused_results[:20])
        
        # 5. 知识图谱增强（可选）- 查询相关实体关系
        if self.contains_entity(query):
            kg_context = self.knowledge_graph.query(query)
            reranked = self.integrate_kg_context(reranked, kg_context)
        
        return reranked[:10]  # 返回 Top-10
    
    def reciprocal_rank_fusion(self, vec_results, bm25_results, k=60, alpha=0.5):
        """
        倒数排名融合（基于教材 Week 04）
        alpha: 向量检索权重 (1-alpha 为 BM25 权重)
        """
        scores = {}
        
        # 向量检索分数
        for rank, doc in enumerate(vec_results):
            doc_id = doc.metadata["id"]
            scores[doc_id] = alpha * (1.0 / (k + rank + 1))
        
        # BM25 分数
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.metadata["id"]
            if doc_id in scores:
                scores[doc_id] += (1 - alpha) * (1.0 / (k + rank + 1))
            else:
                scores[doc_id] = (1 - alpha) * (1.0 / (k + rank + 1))
        
        # 按分数排序
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [self.get_doc_by_id(doc_id) for doc_id, _ in sorted_results]
```

#### 4.1.2 文档切分策略（基于教材 Week 03）

医疗器械文档的特殊性要求精细切分：

| 文档类型 | 切分策略 | Chunk Size | 理由 |
|---------|---------|------------|------|
| 产品注册证 | 整页切分（按页）| N/A | 注册证是原子性文档，不可分割 |
| 技术参数表 | 按参数项切分 | 200-300 tokens | 每个参数独立检索，避免混淆不同产品 |
| 招标文件 | 按章节递归切分 | 500 tokens | 保留条款层级关系 |
| 法规条文 | 按条款切分 | 300 tokens | 每条法规独立引用 |

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 医疗器械专用切分器（基于教材推荐）
tender_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # 教材推荐：200-500 tokens
    chunk_overlap=50,      # 10-20%重叠
    separators=[
        "\n## ",           # 二级标题
        "\n### ",          # 三级标题
        "\n#### ",         # 四级标题
        "。",              # 句号
        "；",              # 分号
        "\n",              # 换行
        " "                # 空格
    ],
    length_function=len,
    is_separator_regex=False
)
```

### 4.2 专业评标 Agent 设计（基于教材 Week 05-06）

#### 4.2.1 合规审查 Agent（带 Self-Reflection）

```python
class ComplianceReviewAgent:
    """
    合规审查 Agent - 基于 Self-Reflective RAG 架构
    引用：Thakrar et al., "Architecting Clinical Collaboration", 2025
    """
    
    tools = [
        {
            "name": "verify_registration_certificate",
            "description": "验证医疗器械注册证的有效性和适用范围",
            "parameters": {...}
        },
        {
            "name": "check_qualification",
            "description": "检查投标人资质是否符合招标文件要求",
            "parameters": {...}
        },
        {
            "name": "search_regulations",
            "description": "检索相关法规条文",
            "parameters": {...}
        }
    ]
    
    def review(self, bid_document: Document) -> ComplianceReport:
        """
        Self-Reflective RAG 执行流程
        """
        max_iterations = 3
        confidence_threshold = 0.75
        
        for iteration in range(max_iterations):
            # Step 1: 规划审查步骤
            plan = self.create_review_plan(bid_document)
            
            # Step 2: 执行检索和验证
            evidence = []
            for item in plan.check_items:
                # 检索相关法规
                regulations = self.retriever.search(item.query)
                # 调用工具验证
                result = self.execute_tool(item.tool_name, item.params)
                evidence.append({"item": item, "result": result, "regulations": regulations})
            
            # Step 3: 生成初步结论
            preliminary_report = self.generate_preliminary_report(evidence)
            
            # Step 4: 自我反思（Self-Reflection）
            reflection = self.self_reflect(preliminary_report, evidence)
            
            # Step 5: 判断是否满足置信度阈值
            if reflection.confidence >= confidence_threshold:
                return self.finalize_report(preliminary_report, reflection)
            
            # Step 6: 如不满足，根据反思结果补充检索
            if iteration < max_iterations - 1:
                additional_evidence = self.gather_additional_evidence(reflection.gaps)
                evidence.extend(additional_evidence)
        
        # 达到最大迭代次数，返回当前最佳结果并标记
        return self.finalize_report(preliminary_report, reflection, warning="Max iterations reached")
    
    def self_reflect(self, report: PreliminaryReport, evidence: list) -> ReflectionResult:
        """
        自我反思：评估结论的可靠性
        返回：置信度分数、识别的推理漏洞、建议补充的证据
        """
        reflection_prompt = f"""
        请评估以下合规审查结论的可靠性：
        
        审查结论：{report.conclusion}
        依据的证据：{evidence}
        
        请回答：
        1. 置信度评分（0-1）：是否有充分证据支持每个结论？
        2. 推理漏洞：是否存在逻辑不严密之处？
        3. 缺失证据：还需要哪些信息来增强结论可靠性？
        4. 矛盾点：证据之间是否存在矛盾？
        
        以 JSON 格式输出。
        """
        response = self.llm.invoke(reflection_prompt)
        return parse_reflection_response(response)
```

#### 4.2.2 技术评审 Agent（多步骤推理）

```python
class TechnicalReviewAgent:
    """
    技术评审 Agent - 基于 Chain-of-Thought + Tool Use
    """
    
    def review(self, bid_doc: Document, tender_reqs: list) -> TechnicalReport:
        """
        技术参数评审流程（ReAct 模式）
        Thought -> Action -> Observation -> Thought...
        """
        # 提取投标方技术参数（Tool Use）
        extraction_result = self.call_tool(
            "extract_technical_params",
            {"document": bid_doc.content, "category": "technical"}
        )
        
        comparison_results = []
        for req in tender_reqs:
            # Thought: 分析当前技术要求
            thought = self.analyze_requirement(req)
            
            # Action: 检索对应的投标参数
            bid_param = self.find_matching_param(extraction_result, req)
            
            # Observation: 记录检索结果
            observation = {"req": req, "bid_param": bid_param}
            
            # Thought: 对比分析
            comparison = self.compare_params(req, bid_param)
            comparison_results.append(comparison)
        
        return TechnicalReport(
            parameters=comparison_results,
            deviations=self.identify_deviations(comparison_results),
            score=self.calculate_technical_score(comparison_results),
            reasoning_trace=self.get_reasoning_trace()  # 可追溯的推理过程
        )
```

### 4.3 知识库设计（基于百炼智能实践 + 教材）

```
knowledge_base/
├── regulations/                    # 法规标准库（教材 Week 03 RAG知识库）
│   ├── laws/                       # 法律法规
│   │   ├── 招标投标法.md
│   │   ├── 政府采购法.md
│   │   ├── 医疗器械监督管理条例.md
│   │   └── 医疗器械注册管理办法.md
│   ├── standards/                  # 行业标准
│   │   ├── GB_9706_医用电气设备.md
│   │   ├── YY_T_医疗器械质量管理体系.md
│   │   └── 医疗器械分类目录.json   # 百炼智能实践：名称标准化
│   └── policies/                   # 政策文件
│       └── 各省招标采购政策/
│
├── tenders/                        # 历史招标项目（千万级数据聚合）
│   ├── 2024/
│   ├── 2023/
│   └── metadata.json               # 项目元数据（用于过滤）
│
├── products/                       # 产品知识库（基于百炼智能超脑模型）
│   ├── registrations/              # 注册证信息（结构化）
│   ├── specifications/             # 技术规格
│   ├── name_variants/              # 名称变体表（解决同名异义问题）
│   └── manufacturers/              # 厂商信息
│
├── templates/                      # 评标模板
│   ├── 技术评审表模板.md
│   ├── 商务评审表模板.md
│   ├── 评标报告模板.md
│   └── 合规检查清单.md
│
└── historical_decisions/           # 历史评标决策（用于学习）
    ├── 类似项目处理结果.json
    └── 争议案例分析.md
```

---

## 5. 关键技术创新点

### 5.1 自主检索决策（Agentic RAG 核心）

不同于传统 RAG 的"一次性检索"，Agentic RAG 允许 Agent 根据中间结果决定是否需要进一步检索：

```python
class AgenticRAG:
    """
    Agentic RAG - 自主检索增强生成
    引用：LangChain Context7 - "Agentic RAG Overview"
    """
    
    def evaluate_with_retrieval(self, query: str, context: dict) -> EvaluationResult:
        """
        评估过程可能触发多次检索：
        1. 发现某参数不明确 -> 检索产品说明书
        2. 发现法规引用 -> 检索完整法规条文
        3. 发现历史案例 -> 检索类似项目处理结果
        """
        max_iterations = 5
        current_iteration = 0
        accumulated_context = context.copy()
        
        while current_iteration < max_iterations:
            # LLM决定是否需要更多检索
            decision = self.llm.decide_retrieval_need(query, accumulated_context)
            
            if not decision.need_retrieval:
                break
            
            # 执行检索
            new_docs = self.retriever.search(
                query=decision.retrieval_query,
                filters=decision.filters
            )
            
            # 验证检索结果相关性
            relevant_docs = self.verify_relevance(new_docs, decision.purpose)
            
            # 添加到上下文
            accumulated_context["documents"].extend(relevant_docs)
            
            current_iteration += 1
        
        # 基于完整上下文生成评估结果
        return self.generate_evaluation(query, accumulated_context)
```

### 5.2 人机协作机制（Human-in-the-Loop）

根据教材 Week 06：复杂决策需要人工审核点。

```python
class HumanInTheLoop:
    """
    人机协作机制 - 关键决策点人工审核
    """
    
    # 必须人工审核的决策点（法规要求 + 风险控制）
    MANDATORY_REVIEW_POINTS = [
        "disqualification_decision",   # 废标决策
        "compliance_rejection",        # 合规性否决
        "technical_score_anomaly",     # 技术评分异常（偏离均值过大）
        "final_winner_recommendation"  # 最终中标推荐
    ]
    
    def request_human_review(self, decision_point: str, context: dict) -> HumanFeedback:
        """
        在关键决策点暂停，等待人工审核
        """
        # 生成待审核内容摘要
        summary = self.generate_review_summary(context)
        
        # 提交人工审核界面
        review_request = {
            "decision_point": decision_point,
            "summary": summary,
            "supporting_docs": context["documents"],
            "ai_recommendation": context["ai_suggestion"],
            "confidence": context["confidence_score"],
            "reasoning_trace": context["reasoning_steps"]  # 可追溯的推理过程
        }
        
        # 等待人工反馈（异步）
        feedback = self.submit_for_review(review_request)
        
        return feedback
```

### 5.3 名称标准化（解决百炼智能提到的"同名异义"问题）

```python
class ProductNameNormalizer:
    """
    医疗器械名称标准化
    基于百炼智能实践：将不同名称映射到标准分类
    """
    
    def __init__(self):
        # 加载医疗器械分类目录
        self.classification_catalog = load_classification_catalog()
        # 加载名称变体表
        self.name_variants = load_name_variants()
        # Embedding 模型用于语义匹配
        self.embedding_model = load_embedding_model()
    
    def normalize(self, raw_name: str) -> StandardName:
        """
        将原始名称标准化
        示例："CT机" -> "X射线计算机体层摄影设备"
        """
        # 1. 直接匹配
        if raw_name in self.name_variants:
            return self.name_variants[raw_name]
        
        # 2. 语义相似度匹配
        candidates = self.find_similar_names(raw_name, top_k=5)
        
        # 3. 人工确认（不确定性高时）
        if candidates[0].score < 0.8:
            return self.request_human_confirmation(raw_name, candidates)
        
        return candidates[0].standard_name
```

---

## 6. 评估体系（基于教材 Week 04 & Week 07 + RAGAS）

### 6.1 检索质量评估

| 指标 | 计算方法 | 目标值 | 工具 |
|-----|---------|-------|-----|
| **Recall@K** | 相关文档中被检索到的比例 | ≥ 0.85 | 自定义 |
| **MRR** | 第一个相关文档排名的倒数 | ≥ 0.70 | 自定义 |
| **上下文精确度** | 检索结果中相关文档的比例 | ≥ 0.80 | RAGAS |
| **上下文召回率** | 相关文档被检索到的比例 | ≥ 0.85 | RAGAS |

### 6.2 生成质量评估（使用 RAGAS 框架）

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,           # 忠实度 - 报告内容是否基于检索文档
    answer_relevancy,       # 答案相关性 - 是否回答了评标问题
    context_precision,      # 上下文精确度
    context_recall          # 上下文召回率
)

# 评估评标报告质量
result = evaluate(
    dataset=evaluation_dataset,
    metrics=[
        faithfulness,        
        answer_relevancy,    
        context_precision,   
        context_recall
    ]
)
```

### 6.3 Agent 执行轨迹评估（基于 LangChain Context7）

```python
from agentevals.trajectory.match import create_trajectory_match_evaluator

# 评估 Agent 执行轨迹是否符合预期
evaluator = create_trajectory_match_evaluator(
    trajectory_match_mode="superset",  # 或 "strict", "unordered", "subset"
)

result = evaluator(
    outputs=actual_trajectory,      # 实际执行的工具调用序列
    reference_outputs=expected_trajectory  # 预期的工具调用序列
)

# 结果：是否按正确顺序调用了正确的工具
```

### 6.4 成本监控（基于教材 Week 07）

```python
class TenderCostTracker:
    """
    评标系统成本追踪（教材 Week 07 实现）
    """
    
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},      # 每 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    }
    
    def track_evaluation(self, project_id: str, agents: list[Agent]):
        """追踪单次评标的成本"""
        costs = {
            "project_id": project_id,
            "by_agent": {},
            "by_model": {},
            "total_tokens": 0,
            "total_cost_usd": 0,
            "latency_ms": 0
        }
        
        for agent in agents:
            agent_cost = agent.get_cost_metrics()
            costs["by_agent"][agent.name] = agent_cost
            costs["total_cost_usd"] += agent_cost["cost_usd"]
            costs["total_tokens"] += agent_cost["total_tokens"]
        
        # 按 Agent 分组的成本分析（关键！）
        # 示例输出：
        # compliance_agent: $0.12 (15%)
        # technical_agent: $0.45 (56%)
        # commercial_agent: $0.18 (22%)
        # reviewer_agent: $0.06 (7%)
        
        return costs
```

---

## 7. 实施路线图（8周计划，对应教材周次）

### 阶段一：基础 RAG（Week 1-2）
- **目标**：搭建可运行的基础检索系统
- **交付物**：
  - 混合检索实现（向量 + BM25）
  - 法规知识库构建
  - 基础查询 API
- **关键指标**：Recall@5 ≥ 0.70

### 阶段二：Agent 能力（Week 3-4）
- **目标**：实现单 Agent 工具调用能力
- **交付物**：
  - 合规审查 Agent（Function Calling）
  - 技术评审 Agent
  - ReAct 模式实现
- **关键指标**：工具调用准确率 ≥ 0.85

### 阶段三：多智能体协作（Week 5-6）
- **目标**：实现 Supervisor Pattern 多 Agent 协作
- **交付物**：
  - 规划者-执行者-审核者架构
  - Self-Reflective RAG 实现
  - 对比分析 Agent
- **关键指标**：系统整体忠实度 ≥ 0.80

### 阶段四：生产部署（Week 7-8）
- **目标**：可审计、可监控的生产系统
- **交付物**：
  - RAGAS 评估流水线
  - 成本监控与告警
  - FastAPI 部署 + 可观测性
  - 人机协作界面
- **关键指标**：
  - P95 延迟 < 10s
  - 单次评标成本 < $1.00
  - 人工审核触发率 < 20%

---

## 8. 参考来源

### 8.1 教材与框架文档
- 《LLM 时代的文本智能与商务应用》(h-lu/agentic-nlp): Week 01-08
- LangChain Context7: /websites/langchain (Multi-Agent, Agentic RAG)
- LlamaIndex Context7: /websites/developers_llamaindex_ai

### 8.2 行业研究
- 百炼智能知了标讯医疗器械版 (bailian-ai.com)
- LeewayHertz: Advanced RAG Architecture (2025)
- Analytics Vidhya: Top 7 Agentic RAG System Architectures (2025)

### 8.3 学术研究
- Thakrar et al., "Architecting Clinical Collaboration: Multi-Agent Reasoning Systems for Multimodal Medical VQA", 2025
- Databricks State of Enterprise AI Report (RAG adoption statistics)

---

*文档版本：v2.0（含行业最佳实践与 Context7 技术细节）*
*最后更新：2026-02-20*
