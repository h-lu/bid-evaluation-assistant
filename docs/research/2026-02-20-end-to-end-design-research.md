# 端到端设计方案深度研究

> 研究日期：2026-02-20
> 研究范围：Agentic RAG、企业级架构、生产部署、评估监控
> 数据来源：Context7、Web Search、GitHub 项目

---

## 一、2026 企业级 RAG 最佳架构

### 1.1 "三路协作"架构（推荐）

2026 年企业级 RAG 系统推荐采用**向量 + SQL + 图谱**三路协作架构：

| 检索类型 | 职责 | 适用场景 |
|----------|------|----------|
| **Vector Retrieval** | 语义理解、文本/视频内容匹配 | "上个月核心利润增长点" |
| **SQL Retrieval** | 精确结构化数据查询 | 从 ERP 提取产品销售/成本数据 |
| **Graph Retrieval** | 逻辑关系与连接追溯 | 追溯"利润增长→产品→团队→技术"链 |

**解决核心问题**：数据不准确 + 逻辑缺失

### 1.2 RAG 演进阶段

| 阶段 | 类型 | 特点 | 优缺点 |
|------|------|------|--------|
| 1 | Naive RAG | 简单 分块→检索→生成 | 易实现，但脆弱、相关性低 |
| 2 | Advanced RAG | 检索前/后优化 | 相关性更好，但流程固定 |
| 3 | Modular RAG | 路由、融合、记忆模块 | 任务自适应，编排复杂 |
| 4 | **Agentic RAG** | 规划、工具使用、反思 | 动态处理复杂查询，延迟较高 |

**我们的系统采用 Agentic RAG 模式**

---

## 二、Agentic RAG 核心设计模式

### 2.1 多引擎 RAG 协调

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic RAG 架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                      ┌─────────────┐                            │
│                      │   Query     │                            │
│                      └──────┬──────┘                            │
│                             │                                   │
│                      ┌──────▼──────┐                            │
│                      │  ToolAgent  │ ← 协调多个 RAG 引擎        │
│                      └──────┬──────┘                            │
│                             │                                   │
│          ┌──────────────────┼──────────────────┐               │
│          ▼                  ▼                  ▼               │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│   │ Vector Index│    │Summary Index│    │  Graph Index│       │
│   │ (事实问题)   │    │ (总结问题)  │    │ (关系问题)  │       │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│          │                  │                  │               │
│          └──────────────────┼──────────────────┘               │
│                             ▼                                   │
│                      ┌─────────────┐                            │
│                      │   Rerank    │                            │
│                      └──────┬──────┘                            │
│                             ▼                                   │
│                      ┌─────────────┐                            │
│                      │   LLM Gen   │                            │
│                      └─────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**核心洞察**：Agentic RAG 是基于 AI Agent 的方法，利用 Agent 的任务规划和工具能力协调多文档、多类型问答需求。

### 2.2 LangGraph 工作流模式

**四大核心模式**（来自 LangGraph 官方文档）：

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| **Prompt Chaining** | 顺序任务处理 | 多步骤文档处理 |
| **Routing** | 动态查询路由 | 不同类型问题分发 |
| **Parallelization** | 并发处理 | 效率优化 |
| **Evaluator-Optimizer** | 评估-优化循环 | 质量迭代提升 |

**Evaluator-Optimizer 模式示例**（适合评标评分）：

```python
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    joke: str
    topic: str
    feedback: str
    funny_or_not: str

def llm_call_generator(state: State):
    """生成器：根据反馈优化输出"""
    if state.get("feedback"):
        msg = llm.invoke(
            f"Write about {state['topic']} considering feedback: {state['feedback']}"
        )
    else:
        msg = llm.invoke(f"Write about {state['topic']}")
    return {"joke": msg.content}

def llm_call_evaluator(state: State):
    """评估器：评估输出质量"""
    grade = evaluator.invoke(f"Grade: {state['joke']}")
    return {"funny_or_not": grade.grade, "feedback": grade.feedback}

def route_joke(state: State):
    """路由：根据评估结果决定下一步"""
    if state["funny_or_not"] == "funny":
        return "Accepted"
    return "Rejected + Feedback"

# 构建工作流
builder = StateGraph(State)
builder.add_node("generator", llm_call_generator)
builder.add_node("evaluator", llm_call_evaluator)
builder.add_edge(START, "generator")
builder.add_edge("generator", "evaluator")
builder.add_conditional_edges("evaluator", route_joke, {
    "Accepted": END,
    "Rejected + Feedback": "generator",
})
```

**应用于评标**：生成评分 → 评估置信度 → 置信度低则补充检索 → 重新评分

### 2.3 Orchestrator-Worker 模式

```python
@task
def orchestrator(topic: str):
    """协调器：生成执行计划"""
    report_sections = planner.invoke([...])
    return report_sections.sections

@task
def llm_call(section: Section):
    """工作器：执行具体任务"""
    result = llm.invoke([...])
    return result.content

@task
def synthesizer(completed_sections: list[str]):
    """合成器：汇总结果"""
    final_report = "\n\n---\n\n".join(completed_sections)
    return final_report

@entrypoint()
def orchestrator_worker(topic: str):
    sections = orchestrator(topic).result()
    section_futures = [llm_call(section) for section in sections]  # 并行
    final_report = synthesizer([fut.result() for fut in section_futures]).result()
    return final_report
```

**应用于评标**：协调器分配审查任务 → 多个专家并行评审 → 合成最终报告

---

## 三、DSPy + LangGraph 黄金组合

### 3.1 架构定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    DSPy + LangGraph 架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                     DSPy                                 │  │
│   │              Agent 的"超级大脑"                          │  │
│   │         • Prompt 自动优化                                │  │
│   │         • 自动化 Prompt 编译                             │  │
│   │         • 减少 70% 手动调优工作                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    LangGraph                             │  │
│   │              Agent 的"协作躯体"                          │  │
│   │         • 图结构层级控制                                 │  │
│   │         • 工作流编排                                     │  │
│   │         • 状态持久化                                     │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   效果：复杂 RAG 准确率 ↑40%，成本 ↓35%                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 DSPy 在评标中的应用

```python
import dspy

class BidScorer(dspy.Module):
    """评标评分模块 - DSPy 自动优化"""

    def __init__(self):
        self.score = dspy.Predict(
            "bid_document, criteria -> technical_score, reasoning, evidence"
        )

    def forward(self, bid_document, criteria):
        return self.score(
            bid_document=bid_document,
            criteria=criteria
        )

# 使用 MIPROv2 自动优化（准确率 +15%）
optimizer = dspy.MIPROv2(
    metric=accuracy_metric,
    auto="light",
    num_threads=24
)

optimized_scorer = optimizer.compile(
    BidScorer(),
    trainset=labeled_bidding_data
)
```

---

## 四、LightRAG × LangGraph 集成案例

### 4.1 Yuxi-Know 架构

**技术栈**：
- 后端：LangGraph + FastAPI
- 前端：Vue.js
- 数据库：Neo4j（图谱）+ Milvus（向量）
- AI：LightRAG + LangChain
- 文档处理：MinerU / PP-Structure

### 4.2 多步工作流

```
Query Rewriting          # 查询重写
      ↓
Vector Recall            # 向量召回
      ↓
Graph Expansion          # 图谱扩展（邻居/路径发现）
      ↓
Evidence Reranking       # 证据重排序
      ↓
Generation/Citation      # 生成 + 引用
```

### 4.3 与我们系统的对应

| Yuxi-Know | 我们的评标系统 |
|-----------|---------------|
| Query Rewriting | 查询理解节点 |
| Vector Recall | LightRAG Low-Level 检索 |
| Graph Expansion | LightRAG 知识图谱扩展 |
| Evidence Reranking | BGE-Reranker |
| Generation/Citation | 评分生成 + 溯源引用 |

---

## 五、Human-in-the-Loop 设计

### 5.1 LangGraph interrupt 机制

```python
from langgraph.types import interrupt, Command

def confirm_score(state: FormState) -> dict:
    """人工确认评分"""
    confirmed = interrupt(
        f"确认评分：技术分 {state['technical_score']}，"
        f"置信度 {state['confidence']}。是否确认？(yes/no)"
    )
    return {"confirmed": confirmed == "yes"}

# 使用方式
result = graph.invoke(state, config)  # 暂停在 interrupt
result = graph.invoke(Command(resume="yes"), config)  # 继续执行
```

### 5.2 评标系统人工审核触发条件

| 条件 | 触发动作 |
|------|----------|
| AI 置信度 < 0.75 | 进入人工审核队列 |
| 合规审查不通过 | 强制人工复核 |
| 评分偏离 > 20% | 黄色预警 + 人工确认 |
| 异常行为检测 | 红色预警 + 暂停流程 |

---

## 六、RAG 分块策略最佳实践（2025）

### 6.1 算法对比

| 算法 | 语义完整性 | 实现复杂度 | 处理速度 | 适用场景 |
|------|-----------|-----------|---------|---------|
| 固定长度 | ★☆☆☆☆ | ★☆☆☆☆ | ★★★★★ | 原型验证 |
| **递归字符** | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ | **通用文本(首选)** |
| 结构感知 | ★★★★☆ | ★★★☆☆ | ★★★★☆ | Markdown/HTML |
| 语义切分 | ★★★★★ | ★★★★☆ | ★★☆☆☆ | 长文档、高质量 |

### 6.2 场景化配置

| 场景 | Chunk Size | Overlap | 推荐算法 |
|------|-----------|---------|---------|
| **招投标文档** | 512 token | 15-20% | 结构感知/递归 |
| 法律/合同 | 256–512 token | 20% | 语义切分 |
| 技术参数表 | 按参数项 | 0% | 结构感知 |
| 法规条文 | 256–300 token | 15% | 递归字符 |

### 6.3 关键发现

- **反直觉结论**：512 token 比 1024 token 的 MRR 指标高 **12-18%**
- **Overlap 黄金区间**：**15-20%**（工程实践最佳）
- **元数据增强**：比纯内容方法召回率提升约 **9%**

---

## 七、企业级评估监控体系

### 7.1 评估框架对比

| 框架 | 定位 | 核心优势 |
|------|------|----------|
| **RAGAS** | RAG 评估标准 | 无需标准答案，本地 LLM 支持 |
| **DeepEval** | 工程化测试 | pytest 集成，CI/CD 友好，14+ 指标 |
| **TruLens** | 深度可观测性 | 全链路追踪，Triad 评估模型 |

### 7.2 核心评估指标

**RAGAS 指标**：
- Context Precision（检索精确度）
- Context Recall（检索召回率）
- Faithfulness（生成忠实度）
- Answer Relevance（答案相关性）

**DeepEval 特色**：
- Hallucination（幻觉检测）
- Agentic Evaluation（智能体评测）
- Red Teaming（红队测试）

### 7.3 监控可观测性

| 工具 | 特点 |
|------|------|
| **Langfuse** | 开源，完整追踪链，成本分析 |
| **LangSmith** | LangChain 生态标杆 |
| **Arize Phoenix** | 嵌入可视化，检索调试 |
| **OpenLIT** | OpenTelemetry 标准，无侵入 |

### 7.4 五步构建评估闭环

1. **构建高质量测试集** - 评估的基石
2. **选择评估框架** - RAGAS 快速评估 / DeepEval CI/CD
3. **设置监控告警** - 实时评估集成业务监控
4. **持续迭代优化** - 每次提交自动评估
5. **人工校准** - 100-200 条人工标注校准（一致性约 85%）

---

## 八、2026 政策与行业趋势

### 8.1 国家政策（2026 关键节点）

| 政策 | 核心要点 |
|------|----------|
| **八部门联合发文** | 2026 年底实现 AI 招投标场景全覆盖 |
| **发改委实施意见** | 明确"人工智能+"定标：评标报告核验、智能审核 |
| **广东推进** | 规划设计、数据治理、应用验证三维度推进 |

### 8.2 AI 智能评标核心场景（12 个）

| 环节 | 场景 |
|------|------|
| **招标** | 智能需求编制 → 文件合规检测 → 智能文件编制 |
| **投标** | 项目智能推荐 → 投标响应比对 → 低价风险提示 |
| **开评标** | 数字开标人 → 专家精准抽取 → **智能辅助评标** |
| **定标** | 评标报告核验 → 辅助定标决策 → 中标合同签订 |

### 8.3 实际落地案例

| 案例 | 效果 |
|------|------|
| 深圳政府采购 | "无人干预评标"，全流程自动化 |
| 链企 AI | 效率 **↑2倍**，中标率 **↑30%** |
| 某省公共资源平台 | AI 清标发现报价大小写不一致，自动修正 |

---

## 九、对我们架构设计的验证

### 9.1 当前架构 v3.0 验证

| 设计决策 | 行业最佳实践 | 验证结果 |
|----------|--------------|----------|
| **LightRAG 双层检索** | 三路协作架构（Vector+SQL+Graph） | ✅ 符合 |
| **LangGraph RGSG 工作流** | Evaluator-Optimizer 模式 | ✅ 符合 |
| **DSPy Prompt 优化** | 黄金组合，准确率 ↑40% | ✅ 符合 |
| **Human-in-the-Loop** | interrupt 机制 | ✅ 符合 |
| **RAGAS + DeepEval** | 评估闭环五步法 | ✅ 符合 |
| **Langfuse 可观测性** | 企业级监控标配 | ✅ 符合 |
| **512 token Chunk** | 工程实践黄金区间 | ✅ 符合 |

### 9.2 建议增强

| 建议 | 优先级 | 说明 |
|------|--------|------|
| 添加 SQL Retrieval | 中 | 结构化数据查询（价格表、参数表） |
| 添加 Red Teaming | 低 | 安全性测试 |
| 添加 OpenLIT | 低 | 无侵入监控备选 |

---

## 十、参考资料

**官方文档：**
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/)
- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [DSPy Documentation](https://dspy.ai/)

**企业架构：**
- [NVIDIA AI Blueprint](https://www.nvidia.cn/ai-data-science/ai-workflows/generative-ai-chatbot-with-rag/)
- [Microsoft Azure AI Architecture](https://learn.microsoft.com/zh-cn/azure/architecture/data-guide/big-data/ai-overview)

**行业研究：**
- [2025 RAG 分块策略深度解析](https://juejin.cn/)
- [RAGAS + DeepEval 评估框架](https://developer.volcengine.com/articles/7529428812854427699)
- [AI+招标一体化](https://m.sohu.com/a/986928017_121193128/)

**政策文件：**
- [发改委 AI+招投标实施意见](https://www.ndrc.gov.cn/xwdt/tzgg/202602/t20260210_1403681.html)
- [广东 AI+招标推进](https://drc.gd.gov.cn/gkmlpt/content/4/4858/mmpost_4858145.html)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
