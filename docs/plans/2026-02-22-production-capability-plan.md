# 生产能力阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有 Gate C-F 可运行骨架基础上，完成真实存储、真实任务执行、真实解析检索、真实安全隔离与真实运维观测，达到可上线发布标准。

**Architecture:** 采用“文档契约先行 + 分轨并行 + 串行收口”的执行方式。先冻结生产能力阶段契约，再按数据与队列、解析与检索、工作流与 Worker、安全与租户隔离、观测与部署五条轨道推进，每条轨道提供可独立验收证据，最后进行全链路回放与发布准入评审。

**Tech Stack:** FastAPI, PostgreSQL, Redis, LangGraph, LightRAG, MinerU, Docling, Object Storage, OpenTelemetry, pytest。

---

## 1. 背景与阶段定义

1. 当前阶段完成了 Gate C-F 的“流程骨架可运行”。
2. 现阶段目标是将骨架替换为可生产运行的真实能力。
3. 本阶段不是推翻重写，而是在既有状态机、错误码、契约之上逐项替换实现。

## 2. 入口与出口条件

### 2.1 入口条件

1. `main` 已包含 Gate C-F 契约与测试基线。
2. OpenAPI 与 REST 规范可解析且无冲突。
3. 全量测试基线通过。

### 2.2 出口条件

1. InMemory 关键路径已替换为真实存储与队列。
2. 解析、检索、评分链路由真实适配器驱动。
3. LangGraph checkpoint 与 interrupt/resume 可持久化恢复。
4. API/DB/Vector/Cache/Queue 五层租户隔离通过回归。
5. 发布流水线具备可执行灰度、回滚、回放验证。

## 3. 文档清单（本阶段 SSOT 子集）

1. `docs/design/2026-02-22-persistence-and-queue-production-spec.md`
2. `docs/design/2026-02-22-parser-and-retrieval-production-spec.md`
3. `docs/design/2026-02-22-workflow-and-worker-production-spec.md`
4. `docs/design/2026-02-22-security-and-multitenancy-production-spec.md`
5. `docs/design/2026-02-22-observability-and-deploy-production-spec.md`

## 4. 执行顺序（必须）

```text
P0 契约冻结
 -> P1 存储与队列生产化
 -> P2 解析与检索生产化
 -> P3 工作流与 Worker 生产化
 -> P4 安全与租户隔离收口
 -> P5 观测与部署收口
 -> P6 全链路回放与发布准入
```

## 5. 轨道任务（最小）

### 5.1 T1 存储与队列

1. Repository 层替换 InMemory 关键路径。
2. PostgreSQL 迁移与索引、RLS 策略落地。
3. Redis 队列与幂等、锁、缓存命名规范落地。
4. outbox 事件表与消费幂等落地。

### 5.2 T2 解析与检索

1. MinerU/Docling/OCR 适配器统一接口落地。
2. parse manifest 与 chunk 元数据真实入库。
3. LightRAG 检索链路与 metadata 过滤真实化。
4. rerank 降级与约束保持改写真实化。

### 5.3 T3 工作流与 Worker

1. LangGraph checkpointer 使用持久化后端。
2. `thread_id` 生成、传递、恢复策略落地。
3. HITL interrupt/resume 与审计一致性落地。
4. Worker 并发、重试、DLQ 路由真实执行。

### 5.4 T4 安全与隔离

1. JWT 可信来源与租户注入链路落地。
2. API 层越权阻断与审计落地。
3. DB RLS 与向量检索 metadata 过滤一致化。
4. 高风险动作审批策略强制执行。

### 5.5 T5 观测与部署

1. 指标、日志、Trace 三件套统一语义落地。
2. SLO 与告警分级（P0/P1/P2）落地。
3. staging 回放、canary、rollback 脚本化。
4. 事故 runbook 与变更管理与流水线联动。

## 6. 证据与验收

每轨道必须提供：

1. 契约测试报告。
2. 集成/回放证据。
3. 性能/安全关键指标。
4. 回滚演练记录。

阶段总验收：

1. 真栈 E2E 跑通（上传 -> 解析 -> 检索 -> 评估 -> HITL -> 报告）。
2. 四门禁与 Gate E/F 控制面可在真栈执行。
3. 30 分钟内可完成回滚并完成回放验证。

## 7. 风险与回退策略

1. 风险：真实组件接入导致契约漂移。
2. 控制：文档先改、契约先测、再替换实现。
3. 回退：任一轨道异常时只回退该轨道实现，不破坏已通过轨道。

## 8. 与现有文档关系

1. 本计划是生产能力阶段总计划。
2. `docs/design/2026-02-21-implementation-plan.md` 仍是 Gate A-F 总计划。
3. 本计划不替代 SSOT，只补充“骨架到生产化”的执行路径。

## 9. 参考

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. `docs/design/2026-02-21-implementation-plan.md`
3. `docs/design/2026-02-21-openapi-v1.yaml`

## 10. 阶段完成后的系统形态（目标画像）

完成 P0-P6 后，系统应达到以下状态：

1. 主链路以真栈运行：API 受理、Worker 执行、真实存储与真实队列、真实解析与检索、真实门禁与发布准入。
2. 所有关键流程可追溯：任一 `job_id/evaluation_id/thread_id` 可追到日志、审计、checkpoint、回放结果。
3. 多租户隔离具备工程化防线：API/DB/Vector/Cache/Queue 全链路阻断跨租户访问。
4. 发布具备可控性：灰度、回滚、回放与准入评估可以重复执行，不依赖人工临场判断。

## 11. 距“完全实现”的剩余差距（分层）

### 11.1 必做差距（上线前必须清零）

1. 真实组件替换尚未完成的部分（若仍存在 sqlite/memory 路径，需全部下线）。
2. 生产环境 SLO 基线与容量压测（峰值、故障注入、恢复时间）需形成正式报告。
3. 安全合规闭环（密钥治理、审计留存、审批策略）需经过一次完整演练并归档。

### 11.2 强烈建议差距（上线后 1-2 个迭代内完成）

1. 自动化运维深度：告警抑制、自动降级、自动回放编排。
2. 评估数据集治理：反例集与黄金集迭代策略精细化。
3. 成本治理：模型路由精调、预算预测与告警精度优化。

### 11.3 增强项差距（中长期）

1. 多区域容灾与跨地域部署。
2. 更细粒度的权限模型与策略平台化。
3. 高级检索优化（图谱增强、跨文档结构化推理）。
