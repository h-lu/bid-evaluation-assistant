# 辅助评标专家系统 —— 端到端统一方案（SSOT）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 单一事实源：本文件

## 0. 一页结论

1. 系统定位：AI 生成“可解释评分建议”，专家做最终裁量。
2. 主链路：`上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`。
3. 任务模型：所有长任务异步化，状态以 `job_id` 为准。
4. 失败模型：`failed` 为 DLQ 子流程结果，不与 DLQ 并行分叉。
5. 隔离模型：MVP 即启用 API/DB/Vector/Cache/Queue 五层租户隔离。
6. 发布模型：质量、性能、安全、成本四门禁同时达标才允许放量。

## 1. 范围与非目标

### 1.1 MVP 范围

1. 项目/供应商/规则管理。
2. 文档上传、解析、分块、索引。
3. 检索增强评分建议与证据链。
4. 人工复核中断与恢复。
5. 报告归档、审计、DLQ 运维。

### 1.2 非目标

1. 全自动终审发布。
2. 微服务拆分与跨服务分布式事务。
3. Neo4j/Milvus 主栈。
4. RAPTOR/GraphRAG 直接进入 MVP。

## 2. 需求约束

### 2.1 业务约束

1. 每个评分项必须有证据引用。
2. 专家保留最终判定权与改判权。
3. 终审记录必须保留审计链条。

### 2.2 技术约束

1. 任何写操作必须有幂等策略。
2. 跨租户访问必须在 API 和 DB 双重阻断。
3. 无 `trace_id` 的请求视为不合规请求。

### 2.3 合规约束

1. 审计日志不可篡改。
2. legal hold 对象不可被自动清理。
3. 高风险动作必须双人复核。

## 3. 参考项目决策（融合旧资料）

### 3.1 直接采用

| 项目 | 采用点 | 落位 |
| --- | --- | --- |
| MinerU | 复杂 PDF 解析输出（含页码与 bbox） | `mineru-ingestion-spec` |
| Docling | Office/HTML/常规 PDF 统一解析 | `mineru-ingestion-spec` |
| LightRAG | local/global/hybrid/mix 检索模式 | `retrieval-and-scoring-spec` |
| LangGraph | checkpointer + interrupt/resume 状态机 | `langgraph-agent-workflow-spec` |

### 3.2 借鉴设计

| 项目 | 借鉴点 | 处理方式 |
| --- | --- | --- |
| RAGFlow | 解析器注册表、分块与位置追踪 | 仅借鉴模式，不引入依赖 |
| Agentic-Procure-Audit-AI | RGSG 任务拆解、可解释评分组织 | 融入状态机与评分流程 |
| ProposalLLM | 点对点应答结构 | 融入评估前端/报告结构 |
| kotaemon | citation 回跳 + PDF 高亮 | 融入前端引用交互 |

### 3.3 明确不采纳（MVP）

1. 以 star 数作为选型依据。
2. 直接上重型图数据库与向量数据库组合。
3. 复杂多 Agent 自治编排替代可控状态机。

## 4. 目标架构

### 4.1 总体架构（ASCII）

```text
+---------------------+      +------------------+      +----------------------+
| 业务用户             | ---> | Frontend (Vue3)  | ---> | FastAPI API          |
+---------------------+      +------------------+      +----------+-----------+
                                                                  |
                                                                  | enqueue
                                                                  v
                                                         +--------+--------+
                                                         | Redis Queue      |
                                                         +--------+--------+
                                                                  |
                                                                  v
                                                         +--------+--------+
                                                         | Worker Pool      |
                                                         +--+----------+---+
                                                            |          |
                                                  parse/index|          |evaluate
                                                            v          v
                                        +----------------------+  +----------------------+
                                        | Parser Router         |  | LangGraph Runtime    |
                                        | MinerU / Docling/OCR  |  | interrupt/resume     |
                                        +----------+-----------+  +----------+-----------+
                                                   |                         |
                                                   +------------+------------+
                                                                |
                                                                v
                      +----------------------------------------------------------------------------+
                      | PostgreSQL: truth/audit/checkpoint/dlq/outbox/legal_hold                  |
                      | Chroma + LightRAG: retrieval index + graph-enhanced retrieval             |
                      | Redis: cache/idempotency/locks                                             |
                      | Object Storage(WORM): raw docs/parsed manifest/reports                     |
                      +----------------------------------------------------------------------------+
```

### 4.2 模块边界

1. `ingestion`：文档接收、解析、分块、入库。
2. `retrieval`：查询理解、检索、重排、证据打包。
3. `evaluation`：规则判定、LLM 评分、置信度计算。
4. `workflow`：状态机编排、HITL、恢复、错误路由。
5. `governance`：审计、权限、发布门禁、运维流程。

### 4.3 通信策略

1. 模块内同步调用。
2. 模块间优先领域事件（outbox），避免隐式耦合。
3. 外部副作用只允许在 workflow 定义的提交节点执行。

## 5. 端到端流程与状态机

### 5.1 主流程

```text
upload_received
 -> parse_queued
 -> parsing
 -> parsed
 -> indexing
 -> indexed
 -> evaluating
 -> needs_manual_decision (optional)
 -> approved
 -> report_generated
 -> archived
```

异常路径：

```text
running
 -> retrying (<=3)
 -> dlq_pending
 -> dlq_recorded
 -> failed
```

### 5.2 HITL 规则

触发任一条件进入 `needs_manual_decision`：

1. `score_confidence < 0.65`
2. `citation_coverage < 0.90`
3. `score_deviation_pct > 20%`
4. 命中红线规则（合规项）

恢复要求：

1. 只能使用最新 `resume_token`。
2. 恢复动作必须记录 `reviewer_id`、`decision`、`comment`。
3. 恢复后流程继续到 `finalize_report`，禁止回跳到任意节点。

## 6. 关键设计决策

### 6.1 文档解析

1. `content_list.json` 为定位真值；`full.md` 为结构真值。
2. 兼容旧命名 `context_list.json`，但 canonical 名为 `content_list`。
3. bbox 统一归一化为 `[x0,y0,x1,y1]`。
4. chunk 元数据必须含 `page,bbox,heading_path,chunk_type`。

### 6.2 检索与评分

1. 查询先标准化，再做“约束保持改写”。
2. 模式由 selector 自动选 `local/global/hybrid/mix`。
3. SQL 支路只允许白名单字段，禁止自由 SQL。
4. 最终评分由“规则引擎硬判定 + LLM 软评分”组合完成。

### 6.3 工作流与恢复

1. LangGraph checkpointer 持久化，`thread_id` 作为恢复指针。
2. `interrupt` 仅用于人工决策与高风险动作确认。
3. 每个副作用节点必须声明幂等键。

### 6.4 错误与 DLQ

1. 重试上限 3 次，指数退避+抖动。
2. 第 4 次失败写入 DLQ，再标记 failed。
3. DLQ 支持 `requeue/discard`，其中 discard 需双人复核。

### 6.5 多租户隔离

1. API 层：`tenant_id` 只来源 JWT。
2. DB 层：核心表全量 `tenant_id` + RLS。
3. 检索层：向量查询必须带 `tenant_id+project_id` 过滤。
4. 缓存与队列：key 与消息头强制 tenant 前缀。

## 7. 非功能目标（门禁阈值）

### 7.1 性能

1. API `P95 <= 1.5s`（查询型接口）。
2. 解析 `50页P95 <= 180s`。
3. 评估 `P95 <= 120s`。
4. 检索 `P95 <= 4s`。

### 7.2 质量

1. RAGAS：`precision/recall >= 0.80`，`faithfulness >= 0.90`。
2. DeepEval：幻觉率 `<= 5%`。
3. citation 可回跳率 `>= 98%`。

### 7.3 安全

1. 跨租户越权事件 `= 0`。
2. 高风险动作审计覆盖率 `= 100%`。
3. legal hold 对象违规删除 `= 0`。

### 7.4 成本

1. 单任务成本 P95 不高于基线 `1.2x`。
2. 模型降级策略触发后服务可用性不低于 `99.5%`。

## 8. Agent-first 开发与发布模型

### 8.1 推进方式

```text
Gate A 设计冻结
 -> Gate B 契约与骨架
 -> Gate C 主链路可运行
 -> Gate D 四门禁通过
 -> Gate E 灰度发布
 -> Gate F 运行优化
 -> Production Capability Stage（生产能力填充）
```

### 8.2 每个 Gate 的最小证据

1. 契约测试报告。
2. E2E 回放报告。
3. 评估与压测报告。
4. 安全回归报告。
5. 回滚演练记录。

## 9. 关联文档

1. `docs/design/2026-02-21-implementation-plan.md`
2. `docs/design/2026-02-21-mineru-ingestion-spec.md`
3. `docs/design/2026-02-21-retrieval-and-scoring-spec.md`
4. `docs/design/2026-02-21-langgraph-agent-workflow-spec.md`
5. `docs/design/2026-02-21-rest-api-specification.md`
6. `docs/design/2026-02-21-data-model-and-storage-spec.md`
7. `docs/design/2026-02-21-error-handling-and-dlq-spec.md`
8. `docs/design/2026-02-21-security-design.md`
9. `docs/design/2026-02-21-frontend-interaction-spec.md`
10. `docs/design/2026-02-21-testing-strategy.md`
11. `docs/design/2026-02-21-deployment-config.md`
12. `docs/plans/2026-02-22-production-capability-plan.md`
13. `docs/design/2026-02-22-persistence-and-queue-production-spec.md`
14. `docs/design/2026-02-22-parser-and-retrieval-production-spec.md`
15. `docs/design/2026-02-22-workflow-and-worker-production-spec.md`
16. `docs/design/2026-02-22-security-and-multitenancy-production-spec.md`
17. `docs/design/2026-02-22-observability-and-deploy-production-spec.md`

## 10. 一手来源（核验日期：2026-02-21）

1. LangGraph docs（interrupt/checkpoint/durable execution）  
   https://docs.langchain.com/oss/python/langgraph/
2. LangChain docs（structured output/tool strategy）  
   https://docs.langchain.com/oss/python/langchain/
3. FastAPI docs（BackgroundTasks/202/DI）  
   https://fastapi.tiangolo.com/
4. MinerU 仓库与文档  
   https://github.com/opendatalab/MinerU
5. LightRAG 仓库  
   https://github.com/HKUDS/LightRAG
6. RAGAS  
   https://github.com/explodinggradients/ragas
7. RAGChecker  
   https://github.com/amazon-science/RAGChecker
8. DeepEval  
   https://github.com/confident-ai/deepeval
9. superpowers skill 系统  
   https://github.com/obra/superpowers
