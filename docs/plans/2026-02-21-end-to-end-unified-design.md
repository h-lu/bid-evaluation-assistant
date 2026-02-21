# 辅助评标专家系统 —— 端到端统一方案（E2E）

> 版本：v3.0
> 日期：2026-02-21
> 单一事实源（SSOT）：本文件

---

## 0. 一页摘要

1. 系统定位：`AI 辅助 + 专家最终决策`，不做全自动评标。
2. 主链路：上传文档 -> 解析建库 -> 检索评估 -> 人工复核 -> 报告归档。
3. 执行模型：长任务全部异步（`job_id`），失败进入 DLQ 后再标记 `failed`。
4. 隔离策略：MVP 即支持真正多租户（`tenant_id` + RLS + 向量命名空间 + 缓存前缀）。
5. 发布门禁：质量（RAGAS/DeepEval）+ 性能（SLO）+ 安全（审计/留存）+ 成本（预算阈值）。

---

## 1. 范围与边界

### 1.1 业务范围（MVP）

- 项目管理、供应商管理、评标规则管理。
- 文档上传、解析、切分、索引。
- 检索增强评估与评分建议。
- HITL（人工中断/恢复）与报告生成归档。

### 1.2 非目标（MVP 不做）

- 全自动终审决策。
- 完整微服务拆分。
- Neo4j、Milvus、复杂对象存储编排。

---

## 2. 外部项目参考与借鉴

### 2.1 采用/借鉴清单

| 项目 | 链接 | 参考方式 | 在本方案落点 |
| --- | --- | --- | --- |
| LightRAG | https://github.com/HKUDS/LightRAG | 直接采用 | 检索核心（语义+图增强） |
| MinerU | https://github.com/opendatalab/MinerU | 直接采用 | 复杂 PDF 结构化解析 |
| Docling | https://github.com/docling-project/docling | 直接采用 | Office/通用文档解析 |
| LangGraph | https://github.com/langchain-ai/langgraph | 直接采用 | 状态机编排 + HITL |
| RAGFlow | https://github.com/infiniflow/ragflow | 借鉴设计 | 文档处理 pipeline 与工程化经验 |
| Agentic-Procure-Audit-AI | https://github.com/MrAliHasan/Agentic-Procure-Audit-AI | 借鉴设计 | 采购审计任务拆解与角色分工 |
| RAG-Anything | https://github.com/HKUDS/RAG-Anything | 借鉴设计 | 多模态分类处理模式（后续阶段） |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR | 可选补强 | 扫描件 OCR 兜底 |

### 2.2 明确不采用（MVP）

| 技术 | 原因 | 替代 |
| --- | --- | --- |
| Neo4j | 运维复杂度高于当前规模需要 | LightRAG 内置图能力 |
| Milvus | 当前数据规模下成本/复杂度偏高 | Chroma |
| 完整微服务 | 交付速度与运维成本不匹配 | 模块化单体（可演进拆分） |

---

## 3. 目标架构

### 3.1 架构原则

1. 先可用、再优化：优先保证端到端闭环可运行。
2. 契约优先：接口、任务状态机、审计字段先定再实现。
3. 生产可观测：Trace/Metrics/Logs 必选，不可选配。
4. 渐进演进：模块化单体起步，按阈值拆分。

### 3.2 端到端架构图

```text
+---------------------+      +------------------+      +------------------+
| 评标专家 / 招标代理  | ---> | 前端 (Vue3)      | ---> | FastAPI API      |
+---------------------+      +------------------+      +--------+---------+
                                                            | enqueue
                                                            v
                                                     +------+------+
                                                     | Redis Queue |
                                                     +------+------+
                                                            |
                                                            v
                                                     +------+------+
                                                     | Worker      |
                                                     +--+-------+--+
                                                        |       |
                                          parse/index   |       | evaluate
                                                        v       v
                                             +----------+--+  +-------------------+
                                             | MinerU/Docling|  | LangGraph WF    |
                                             +----------+--+  +---------+---------+
                                                        |                |
                                                        v                v
                                           +------------+----------------+-----------+
                                           | PostgreSQL / Chroma / Redis            |
                                           +------------+----------------+-----------+
                                                        |                |
                                                        | hitl=yes       | hitl=no
                                                        v                v
                                               +--------+-----+   +------+---------+
                                               | 人工复核      |   | 报告生成与归档 |
                                               +--------------+   +----------------+

可观测性：API / Worker / Workflow 全链路输出 Trace、Metrics、Logs。
```

### 3.3 模块边界

| 模块 | 职责 |
| --- | --- |
| `projects` | 项目与规则定义 |
| `suppliers` | 供应商主数据 |
| `documents` | 上传、解析、切分、存储 |
| `retrieval` | 索引构建与查询 |
| `compliance` | 合规校验与红线规则 |
| `evaluation` | 评分建议与证据组织 |
| `workflow` | LangGraph 状态机与 HITL |
| `users` | 认证、授权、审计 |

---

## 4. 端到端流程

### 4.1 主流程

1. 创建项目与评分规则。
2. 上传投标文件。
3. 异步解析与切分。
4. 异步索引构建。
5. 异步发起评估。
6. 命中规则时进入人工复核。
7. 人工恢复后继续执行。
8. 生成报告并归档。

### 4.2 E2E 时序图

```text
参与方：
[User] 评标专家
[FE]   前端
[API]  FastAPI
[Q]    Redis Queue
[WK]   Worker
[WF]   LangGraph
[DB]   PostgreSQL/Chroma

1) User -> FE  : 上传文件 + 发起评估
2) FE   -> API : POST /documents/upload
3) API  -> Q   : enqueue(parse/index)
4) API  -> FE  : 202 + job_id

5) Q    -> WK  : execute parse/index
6) WK   -> DB  : 写入 chunk / 索引

7) FE   -> API : POST /evaluations/{id}/start
8) API  -> Q   : enqueue(evaluate)
9) Q    -> WK  : execute evaluate
10) WK  -> WF  : run workflow
11) WF  -> DB  : 检索证据 + 生成建议

12) if 命中 HITL:
      WF  -> API : needs_manual_decision
      API -> FE  : 等待人工处理
      User-> FE  : 人工复核并恢复
      FE  -> API : POST /jobs/{job_id}/resume
    else:
      WF  -> API : succeeded

13) API -> FE : 返回结果与报告链接
```

---

## 5. 数据与多租户治理

### 5.1 核心实体

- `Project`, `Supplier`, `Document`, `Chunk`
- `EvaluationSession`, `EvaluationItem`, `EvaluationResult`
- `Citation`, `AuditLog`, `Job`, `DlqItem`

### 5.2 强隔离规则

1. 所有关键业务表强制 `tenant_id`。
2. PostgreSQL 启用 RLS。
3. 向量索引按租户命名空间隔离。
4. Redis key 强制租户前缀。
5. Job 创建即绑定 `tenant_id`，执行期二次校验。

### 5.3 留存与合规

- 审计日志：>= 5 年
- 评估报告：>= 5 年
- 中间解析产物：1-2 年
- `legal_hold`：进入 WORM 不可变存储，禁止删除/覆盖

---

## 6. 异步任务与 HITL

### 6.1 任务模型

- 任务类型：`parse`、`index`、`evaluate`、`report_generate`
- 状态机：`queued -> running -> retrying -> succeeded|failed|cancelled|needs_manual_decision`
- 重试策略：指数退避，最多 3 次
- 失败策略：重试超限先写 DLQ，再标记 `failed`

### 6.2 HITL 规则

触发条件（任一命中）：

- `confidence < 0.75`
- 证据覆盖率 `< 0.90`
- 评分偏离组内中位数 `> 20%`
- 命中合规红线

时效规则：

- 30 分钟未响应：提醒
- 2 小时未处理：升级项目负责人
- 24 小时未处理：保持 `needs_manual_decision`，禁止自动放行

---

## 7. 非功能目标与门禁

### 7.1 性能 SLO

- 普通 API：P95 <= 1.5s
- 检索查询：P95 <= 4.0s
- 50 页解析：P95 <= 180s
- 单供应商评估（不含人审）：P95 <= 120s
- 可用性：>= 99.5%

### 7.2 质量门禁

- RAGAS：Precision >= 0.80，Recall >= 0.80，Faithfulness >= 0.90，Relevancy >= 0.85
- DeepEval：Hallucination Rate <= 5%
- E2E 关键流程通过率：100%
- 发布前 P0/P1 缺陷：0

### 7.3 成本门禁

- 单租户月预算偏差：<= 15%
- 单任务成本 P95：<= 基线 1.2x
- 连续 3 天超预算：触发降级（低成本模型 + 限制并发）

---

## 8. 部署、扩展与容灾

### 8.1 生产拓扑

- Nginx
- FastAPI API
- Worker
- PostgreSQL / Redis / Chroma / LightRAG

### 8.2 扩容策略

- 机制：Kubernetes HPA + KEDA
- 预警阈值：检索 P95 > 2.5s 持续 15 分钟（提前扩容）
- 违约阈值：检索 P95 > 4.0s 持续 5 分钟（SLO breach）
- 其他触发：CPU > 70% 15 分钟、队列积压 > 200 10 分钟、Worker 失败率 > 2%

### 8.3 容灾目标

- RPO <= 15 分钟
- RTO <= 60 分钟
- 每月一次恢复演练

---

## 9. 8 周实施路线

- Week 1-2：基础骨架、RBAC、多租户隔离
- Week 3-4：解析、索引、异步任务框架
- Week 5-6：评估流程、HITL、报告
- Week 7-8：门禁、压测、容灾、发布

---

## 10. 发布准入（DoD）

1. 质量门禁通过。
2. SLO 与性能压测达标。
3. 安全门禁通过（租户隔离、审计、留存）。
4. 成本门禁与自动降级演练通过。
5. DLQ 运维流程（查询/重放/废弃）演练通过。

---

## 11. 关联文档

- `docs/design/2026-02-21-implementation-plan.md`
- `docs/design/2026-02-21-rest-api-specification.md`
- `docs/design/2026-02-21-security-design.md`
- `docs/design/2026-02-21-deployment-config.md`
- `docs/design/2026-02-21-testing-strategy.md`

---

## 12. 外部参考

- LangGraph HITL: https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
- LightRAG: https://github.com/HKUDS/LightRAG
- MinerU: https://github.com/opendatalab/MinerU
- Docling: https://github.com/docling-project/docling
- Chroma: https://docs.trychroma.com/docs/run-chroma/clients
- RAGAS: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- DeepEval: https://deepeval.com/docs/getting-started
