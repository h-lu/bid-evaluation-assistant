# Agentic NLP 课程启示录 —— 对辅助评标专家系统的指导意义

> 参考课程：[h-lu/agentic-nlp](https://github.com/h-lu/agentic-nlp) - LLM时代的文本智能与商务应用（8周课程）
> 调研时间：2026年2月20日

---

## 一、课程核心架构概览

该课程是一个8周的NLP实战课程，从"训练模型"到"设计系统"的范式转变出发，系统讲解了：

| 阶段 | 周次 | 主题 | 核心技术 |
|------|------|------|---------|
| 阶段一 | 01-02 | LLM基础 | API封装、Prompt Engineering、评估框架 |
| 阶段二 | 03-04 | RAG系统 | 向量检索、混合检索、重排序、RAGAS评估 |
| 阶段三 | 05-06 | Agent设计 | Function Calling、ReAct模式、多智能体协作、Agentic RAG |
| 阶段四 | 07-08 | 企业应用 | 成本优化、部署实践、A/B测试、端到端系统设计 |

---

## 二、对辅助评标系统的关键技术启示

### 1. 文档切分策略（Week 03）

**课程要点**：
- Chunk Size：200-500 tokens（约300-1000中文字符）
- Overlap：Chunk Size的10-20%
- 按语义边界切分（段落、句子）优于固定长度

**评标系统应用**：
```
投标文件结构：
├─ 资格审查部分 → 按证照/资质独立切分
├─ 技术方案部分 → 按章节/评分项切分
├─ 报价部分 → 作为一个整体（通常很短）
└─ 业绩证明 → 每个业绩案例独立切分
```

**针对评标的特殊处理**：
- 技术参数表 → 保持表格完整性
- 资质证书 → 提取关键字段（名称、编号、有效期）
- 报价明细 → 保持结构化

### 2. 混合检索与重排序（Week 04）

**课程要点**：
```python
# RRF融合算法
def reciprocal_rank_fusion(vec_results, bm25_results, k=60, alpha=0.5):
    scores = {}
    for rank, doc in enumerate(vec_results):
        scores[doc['id']] = alpha / (k + rank + 1)
    for rank, doc in enumerate(bm25_results):
        scores[doc['id']] += (1-alpha) / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**评标系统应用**：
| 检索场景 | 推荐策略 | 原因 |
|---------|---------|------|
| 技术参数比对 | 混合检索（向量+BM25） | 需要精确匹配参数值 |
| 资质证书核查 | 纯BM25 | 证书编号需精确匹配 |
| 方案相似度检测 | 向量检索 | 语义相似性 |
| 评分标准匹配 | 混合+重排序 | 需要高准确率 |

### 3. ReAct Agent模式（Week 05）

**课程要点**：
```
ReAct循环：
Thought → Action → Observation → Thought → ... → Final Answer
```

**评标系统Agent设计**：
```python
class BidEvaluationAgent:
    """评标Agent的ReAct实现"""

    SYSTEM_PROMPT = """你是资深的医疗器械招投标评标专家。

    你有以下工具可用：
    - check_qualification: 检查供应商资质
    - analyze_technical: 分析技术方案
    - calculate_price_score: 计算价格分
    - detect_anomaly: 异常检测（围标串标）
    - retrieve_regulations: 检索相关法规

    请按以下格式工作：
    Thought: [你的思考过程]
    Action: [工具名称]
    Action Input: [工具参数JSON]

    当完成分析后，用以下格式给出最终评分：
    Final Answer: [评分结果和建议]
    """
```

### 4. 多智能体协作架构（Week 06）

**课程核心**：规划者-执行者-审核者（Planner-Executor-Reviewer）模式

**评标系统多Agent设计**：
```
┌─────────────────────────────────────────────────┐
│              评标多智能体系统                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐                                │
│  │ 协调者Agent  │ ← 任务分解、进度控制           │
│  │ (Orchestrator)                               │
│  └──────┬──────┘                                │
│         │                                       │
│  ┌──────┴──────────────────────────┐           │
│  │                                 │           │
│  ▼                                 ▼           │
│ ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│ │资格审查  │  │技术评审  │  │价格评审  │          │
│ │ Agent  │  │ Agent  │  │ Agent  │          │
│ └────┬────┘  └────┬────┘  └────┬────┘          │
│      │            │            │               │
│      └────────────┼────────────┘               │
│                   ▼                            │
│           ┌─────────────┐                      │
│           │ 审核者Agent  │ ← 质量检查、一致性验证│
│           │ (Reviewer)  │                      │
│           └──────┬──────┘                      │
│                  ▼                             │
│           ┌─────────────┐                      │
│           │ 报告生成Agent│                      │
│           └─────────────┘                      │
└─────────────────────────────────────────────────┘
```

**各Agent职责**：
| Agent | 职责 | 使用的模型 |
|-------|------|----------|
| 协调者 | 任务分解、进度跟踪 | GPT-4o |
| 资格审查Agent | 证照核查、资质验证 | GPT-4o-mini（规则明确） |
| 技术评审Agent | 方案分析、参数比对 | GPT-4o（复杂推理） |
| 价格评审Agent | 价格分计算 | GPT-4o-mini（数学计算） |
| 审核者Agent | 结果校验、一致性检查 | GPT-4o |
| 报告生成Agent | 生成评标报告 | GPT-4o-mini |

### 5. Agentic RAG（Week 06）

**课程核心**：让Agent自主决定检索策略

**评标系统Agentic RAG设计**：
```python
class BidRetrieverAgent:
    """评标检索Agent - 自主决定检索策略"""

    def retrieve(self, query: str, context: dict) -> dict:
        # 1. 分析查询类型
        query_type = self._analyze_query(query)

        # 2. 选择检索策略
        if query_type == "qualification_check":
            # 资质核查 - 精确匹配
            strategy = {"method": "keyword", "threshold": 1.0}
        elif query_type == "technical_comparison":
            # 技术比对 - 语义相似
            strategy = {"method": "hybrid", "alpha": 0.6}
        elif query_type == "regulation_lookup":
            # 法规检索 - 混合+重排序
            strategy = {"method": "hybrid_rerank"}

        # 3. 执行检索
        results = self._execute_strategy(query, strategy)

        # 4. 评估结果
        if not self._is_sufficient(results):
            # 重新检索或扩展查询
            results = self._refine_and_retrieve(query, results)

        return results
```

### 6. Human-in-the-Loop（Week 06）

**课程核心**：在关键决策点引入人工审核

**评标系统审核点设计**：
```
审核点1：资格审查结果
├─ 触发条件：发现资质存疑、证照过期
├─ 审核内容：供应商资质列表
└─ 处理方式：人工确认或驳回

审核点2：废标判定
├─ 触发条件：AI建议废标
├─ 审核内容：废标理由和证据
└─ 处理方式：必须人工确认

审核点3：异常预警
├─ 触发条件：围标串标风险>阈值
├─ 审核内容：异常证据链
└─ 处理方式：人工判断+启动调查

审核点4：评分差异过大
├─ 触发条件：AI评分与专家差异>15分
├─ 审核内容：评分明细对比
└─ 处理方式：人工复核
```

### 7. 成本优化（Week 07）

**课程核心**：按任务复杂度选择模型

**评标系统模型选择策略**：
```python
AGENT_MODELS = {
    # 复杂推理任务 - 用大模型
    "coordinator": "gpt-4o",      # 需要理解复杂任务
    "technical_reviewer": "gpt-4o", # 需要深度分析
    "anomaly_detector": "gpt-4o",   # 需要模式识别

    # 简单规则任务 - 用小模型
    "qualification_checker": "gpt-4o-mini",  # 规则明确
    "price_calculator": "gpt-4o-mini",       # 数学计算
    "report_generator": "gpt-4o-mini",       # 模板生成
}
```

**成本预估**（单次评标）：
| Agent | 调用次数 | 模型 | 单次成本 | 总成本 |
|-------|---------|------|---------|--------|
| 协调者 | 2-3次 | GPT-4o | $0.01 | $0.03 |
| 资格审查 | 3-5次 | GPT-4o-mini | $0.001 | $0.005 |
| 技术评审 | 5-10次 | GPT-4o | $0.02 | $0.20 |
| 价格计算 | 1-2次 | GPT-4o-mini | $0.001 | $0.002 |
| 审核者 | 1-2次 | GPT-4o | $0.01 | $0.02 |
| **合计** | - | - | - | **~$0.26** |

### 8. RAGAS评估框架（Week 04）

**课程核心**：四大评估指标

**评标系统评估指标设计**：
```python
evaluation_metrics = {
    # 检索质量
    "context_precision": "检索到的法规/标准是否相关",
    "context_recall": "是否找到了所有需要的法规",

    # 生成质量
    "faithfulness": "评分建议是否基于招标文件要求",
    "answer_relevancy": "回答是否针对评标问题",

    # 评标特有指标
    "qualification_accuracy": "资质核查准确率",
    "scoring_consistency": "评分与专家一致性",
    "regulation_compliance": "法规引用正确率"
}
```

---

## 三、系统架构设计建议

基于课程内容，建议评标系统采用以下架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                    辅助评标专家系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                            │
│  ├── /api/bids/analyze     # 投标文件分析                        │
│  ├── /api/bids/evaluate    # 评标执行                            │
│  ├── /api/bids/report      # 报告生成                            │
│  └── /api/admin/feedback   # 反馈收集                            │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration Layer                                            │
│  ├── WorkflowOrchestrator  # 工作流编排                          │
│  ├── CostTracker           # 成本追踪                            │
│  └── HumanInTheLoop        # 人工审核点                          │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer                                                    │
│  ├── CoordinatorAgent   # 协调者                                 │
│  ├── QualificationAgent # 资格审查                               │
│  ├── TechnicalAgent     # 技术评审                               │
│  ├── PriceAgent         # 价格评审                               │
│  ├── AnomalyAgent       # 异常检测                               │
│  └── ReviewerAgent      # 审核者                                 │
├─────────────────────────────────────────────────────────────────┤
│  Capability Layer                                               │
│  ├── MinerU Parser       # 文档解析（已集成）                     │
│  ├── RAG Engine          # 检索增强                              │
│  ├── LLM Client          # 大模型调用                            │
│  └── Tool Registry       # 工具注册                              │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ├── Vector Store (ChromaDB)  # 向量存储                         │
│  ├── Knowledge Base            # 法规/案例库                     │
│  └── Audit Log                 # 审计日志                        │
├─────────────────────────────────────────────────────────────────┤
│  Observability Layer                                            │
│  ├── Tracing             # 调用链追踪                            │
│  ├── Metrics             # 性能指标                              │
│  └── Alerts              # 告警通知                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、关键技术选型建议

| 模块 | 推荐方案 | 课程依据 | 备注 |
|------|---------|---------|------|
| Agent框架 | 原生实现 + LangGraph | Week 05-06 | 简单场景用原生，复杂工作流用LangGraph |
| RAG检索 | 混合检索 + 重排序 | Week 04 | RRF融合 + Cross-Encoder |
| 向量数据库 | ChromaDB | Week 03-04 | 轻量级，易于部署 |
| 评估框架 | RAGAS + 自定义指标 | Week 04, 07 | 需要评标专用指标 |
| 成本优化 | 按Agent职责选模型 | Week 07 | 复杂推理用GPT-4o，规则任务用mini |
| 人工介入 | 关键点审核 | Week 06 | 废标判定必须人工确认 |

---

## 五、课程代码可直接复用的部分

1. **RAG Pipeline**（Week 03-04）
   - `HybridRetriever`：混合检索
   - `CrossEncoderReranker`：重排序
   - `QueryRewriter`：查询重写

2. **Agent框架**（Week 05-06）
   - `ReActAgent`：ReAct模式Agent
   - `PlannerAgent`/`ExecutorAgent`/`ReviewerAgent`：多Agent协作
   - `HumanInTheLoopAgent`：人工审核机制

3. **评估与监控**（Week 07）
   - `CostTracker`：成本追踪
   - `LLMEvaluator`：LLM评估器

---

## 六、实施路线图

```
Phase 1：基础能力（2周）
├─ Week 1：MinerU解析 + RAG基础
└─ Week 2：向量库建设 + 基础检索

Phase 2：Agent能力（3周）
├─ Week 3：单Agent（资格审查）
├─ Week 4：ReAct模式 + 工具集成
└─ Week 5：多Agent协作

Phase 3：生产就绪（2周）
├─ Week 6：评估体系 + Human-in-the-Loop
└─ Week 7：成本优化 + 部署

Phase 4：优化迭代（持续）
├─ A/B测试
├─ 用户反馈收集
└─ 模型/策略迭代
```

---

## 七、关键注意事项

1. **不要过度设计**：课程强调"从简单开始，按需升级"
2. **评估驱动**：每个优化都要有数据支撑
3. **成本意识**：从第一天就追踪成本
4. **可解释性**：评标场景必须能解释每个决策
5. **人工兜底**：AI建议 + 专家决策

---

*整理时间：2026年2月20日*
