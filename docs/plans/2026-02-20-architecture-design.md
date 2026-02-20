# 辅助评标专家系统 —— 端到端架构设计

> 版本：v1.0
> 设计日期：2026-02-20
> 状态：已批准

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

### 3.1 文档解析模块

```
┌─────────────────────────────────────────────────────────────┐
│                    文档解析模块                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   PDF/图片输入                                               │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────┐                                           │
│   │ 格式检测器  │ ──→ PDF? 图片? Word?                      │
│   └─────┬───────┘                                           │
│         │                                                   │
│   ┌─────┴───────┬───────────────┐                          │
│   ▼             ▼               ▼                          │
│ ┌─────┐    ┌─────────┐    ┌─────────┐                      │
│ │MinerU│    │PaddleOCR│    │python-docx│                    │
│ │(PDF)│    │(扫描件) │    │ (Word)  │                      │
│ └──┬──┘    └────┬────┘    └────┬────┘                      │
│    │            │              │                           │
│    └────────────┴──────────────┘                           │
│                 │                                           │
│                 ▼                                           │
│         ┌─────────────┐                                     │
│         │ Content List│  ← 统一输出格式                     │
│         │   (JSON)    │                                     │
│         └──────┬──────┘                                     │
│                │                                            │
│                ▼                                            │
│         ┌─────────────┐                                     │
│         │  Chunker    │  ← RAG分块器                        │
│         └──────┬──────┘                                     │
│                │                                            │
│                ▼                                            │
│    ┌────────────────────────┐                              │
│    │ 文本块 + 表格块 + 图片块 │                              │
│    └────────────────────────┘                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**分块策略（2026最佳实践）：**

| 文档类型 | 切分策略 | Chunk Size | 理由 |
|---------|---------|------------|------|
| 产品注册证 | 整页切分 | N/A | 原子性文档 |
| 技术参数表 | 按参数项切分 | 200-300 tokens | 独立检索 |
| 招标文件 | 按章节递归切分 | 500 tokens | 保留层级 |
| 法规条文 | 按条款切分 | 300 tokens | 独立引用 |

### 3.2 RAG检索模块

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
│   ┌─────┴───────┐                                          │
│   ▼             ▼                                           │
│ ┌─────┐    ┌─────────┐                                     │
│ │向量  │    │  BM25   │                                     │
│ │检索  │    │ 检索    │                                     │
│ │(BGE)│    │(精确)   │                                     │
│ └──┬──┘    └────┬────┘                                     │
│    │            │                                           │
│    └─────┬──────┘                                           │
│          ▼                                                  │
│   ┌─────────────┐                                           │
│   │  RRF融合    │  ← α=0.3稀疏/稠密平衡                     │
│   └──────┬──────┘                                           │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────┐                                           │
│   │  Reranker   │  ← BGE-Reranker-v2-m3                     │
│   └──────┬──────┘                                           │
│          │                                                  │
│          ▼                                                  │
│   Top-K 相关文档                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 多Agent模块（LangGraph状态机）

```
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph 状态机工作流                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   StateGraph<BidEvaluationState>                               │
│                                                                 │
│   ┌─────────┐                                                   │
│   │ START   │                                                   │
│   └────┬────┘                                                   │
│        ▼                                                        │
│   ┌─────────────┐                                               │
│   │  解析文档   │  document_parser_node                         │
│   └──────┬──────┘                                               │
│          ▼                                                      │
│   ┌─────────────┐                                               │
│   │ 合规审查    │  compliance_agent_node                        │
│   └──────┬──────┘                                               │
│          │                                                      │
│    ┌─────┴─────┐                                                │
│    ▼           ▼                                                │
│  通过        不通过 → 报告                                       │
│    │                                                            │
│    ▼                                                            │
│   ┌─────────────┐                                               │
│   │ 并行评审    │  technical + commercial                       │
│   └──────┬──────┘                                               │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐                                               │
│   │Self-Reflect │  ← 置信度检查                                 │
│   └──────┬──────┘                                               │
│          │                                                      │
│    ┌─────┴─────┐                                                │
│  ≥0.75       <0.75 → 补充检索                                   │
│    │                                                            │
│    ▼                                                            │
│   ┌─────────────┐                                               │
│   │ 异常检测    │  anomaly_detection_node                       │
│   └──────┬──────┘                                               │
│          │                                                      │
│    ┌─────┴─────┐                                                │
│  正常        异常 → 人工审核                                     │
│    │                                                            │
│    ▼                                                            │
│   ┌─────────────┐                                               │
│   │ 生成报告    │  report_generator_node                        │
│   └──────┬──────┘                                               │
│          ▼                                                      │
│   ┌─────────┐                                                   │
│   │   END   │                                                   │
│   └─────────┘                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Agent职责分工：**

| Agent | 职责 | LLM选择 | 原因 |
|-------|------|---------|------|
| Supervisor | 任务协调 | DeepSeek | 推理能力强 |
| Compliance | 合规审查 | Qwen-Turbo | 规则明确 |
| Technical | 技术评审 | Qwen-Max | 深度分析 |
| Commercial | 商务评审 | Qwen-Turbo | 计算型 |
| Reviewer | 终审评估 | DeepSeek | 综合推理 |

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

- MinerU: https://github.com/opendatalab/MinerU
- LangGraph: https://github.com/langchain-ai/langgraph
- RAGAS: https://github.com/explodinggradients/ragas
- DeepEval: https://github.com/confident-ai/deepeval
- Langfuse: https://github.com/langfuse/langfuse

---

*设计文档版本：v1.0*
*最后更新：2026-02-20*
