# 详细实施计划（Agent-first 端到端任务清单）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 计划原则

1. 不按周排期，按 Gate + 证据推进。
2. 每个任务必须定义：输入、产出、验收、失败回退。
3. 先收敛契约，再推进实现。
4. 可并行任务交给 Codex/Claude Code 执行，最后统一回归。

## 2. Gate 总览

```text
Gate A 设计冻结
 -> Gate B 契约与骨架
 -> Gate C 端到端打通
 -> Gate D 四门禁强化
 -> Gate E 灰度与回滚
 -> Gate F 运营优化
```

## 3. 执行轨道

1. `T1` API 与任务系统
2. `T2` 解析与建库
3. `T3` 检索与评分
4. `T4` LangGraph 工作流
5. `T5` 数据与安全
6. `T6` 前端交互
7. `T7` 测试与观测
8. `T8` 部署与运维

## 4. Gate A：设计冻结

### A-1 术语与状态冻结

输入：现行文档。  
产出：术语字典（状态、错误码、角色、引用对象）。  
验收：所有文档术语一致，无同义混用。

### A-2 边界冻结

输入：SSOT。  
产出：模块边界与副作用边界表。  
验收：每个副作用节点唯一归属（不能重复提交）。

### A-3 旧资料融合冻结

输入：git 历史旧文档。  
产出：采纳/修正/废弃判定表。  
验收：每个“修正后保留”都能定位到现行落点。

### Gate A 输出物（冻结）

1. A-1：`docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md`
2. A-2：`docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md`
3. A-3：`docs/design/2026-02-21-legacy-detail-triage.md`

## 5. Gate B：契约与骨架

### B-1 API 契约

任务：

1. 定稿统一响应模型与错误对象。
2. 定稿写接口幂等策略（`Idempotency-Key`）。
3. 定稿异步任务契约（`202 + job_id` + 状态查询）。
4. 定稿 `resume_token` 与 citation schema。

验收：OpenAPI + 契约测试样例通过。

B-1 输出物：

1. `docs/design/2026-02-21-openapi-v1.yaml`
2. `docs/design/2026-02-21-api-contract-test-samples.md`

### B-2 任务系统骨架

任务：

1. 定义任务状态机：`queued/running/retrying/succeeded/failed`。
2. 落地重试策略：3 次重试 + 指数退避。
3. 打通 DLQ 子流程入口。

验收：状态机与重试行为可回放验证。

B-2 输出物：

1. `docs/design/2026-02-21-job-system-and-retry-spec.md`

### B-3 数据模型骨架

任务：

1. 核心表建模：`jobs/workflow_checkpoints/dlq_items/audit_logs`。
2. RLS 策略与 `app.current_tenant` 注入策略落地。
3. outbox 事件表与消费幂等键建模。

验收：跨租户查询被阻断，RLS 回归通过。

### B-4 解析与检索骨架

任务：

1. 解析器路由骨架：`mineru -> docling -> ocr`。
2. 检索模式选择器骨架：`local/global/hybrid/mix`。
3. 引用对象最小字段打通。

验收：示例文档可完整入库并返回可回跳引用。

### Gate B 输出汇总

1. `docs/design/2026-02-21-openapi-v1.yaml`
2. `docs/design/2026-02-21-api-contract-test-samples.md`
3. `docs/design/2026-02-21-job-system-and-retry-spec.md`
4. `docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md`

## 6. Gate C：端到端打通

### C-1 上传到解析

任务：

1. 上传后异步投递 parse 任务。
2. parse run manifest 记录输入文件 hash 与解析路由。
3. 解析失败按错误码分类。

验收：`upload -> parse -> chunk` 成功率达到基线。

### C-2 MinerU 细节落地

任务：

1. 支持 `content_list.json` 与 `context_list.json` 兼容读取。
2. `full.md` 用于 heading_path 结构补全。
3. bbox 归一化（支持 xyxy/xywh）。
4. 编码回退（`utf-8 -> gb18030`）与错误码落地。

验收：坐标可回跳，chunk 元数据字段完整。

### C-3 检索与证据

任务：

1. 查询标准化 + 约束保持改写。
2. selector 选择 LightRAG 模式。
3. 检索结果 metadata 过滤（tenant/project/doc_type）。
4. rerank 失败降级策略（原分数排序）。

验收：检索输出附完整证据集，且无跨租户召回。

### C-4 评分与解释

任务：

1. 规则引擎先做硬约束判定。
2. LLM 仅在规则允许范围输出软评分与说明。
3. 评分项绑定 citation 列表。
4. 生成总分、置信度、风险标签。

验收：无 citation 的评分项比例为 0。

### C-5 HITL 与恢复

任务：

1. 命中阈值进入 `needs_manual_decision`。
2. 人工提交 `resume_token + decision` 恢复执行。
3. 恢复操作写审计日志。

验收：中断后 24h 内可恢复并完成任务。

### C-6 DLQ 子流程

任务：

1. 第 4 次失败触发 `dlq_pending`。
2. DLQ 写入成功后再置 `failed`。
3. 提供 `requeue/discard` 运维接口。

验收：DLQ 与 failed 时序一致，审计链闭环。

## 7. Gate D：四门禁强化

### D-1 质量门禁

任务：

1. RAGAS 指标门禁。
2. DeepEval 幻觉率门禁。
3. citation 回跳率门禁。
4. P1：RAGChecker 细粒度诊断触发流程。

验收：门禁阈值全部达标。

### D-2 性能门禁

任务：

1. API、检索、解析、评估压测。
2. 高并发任务队列稳定性测试。
3. 关键路径缓存命中率验证。

验收：P95 指标全部达标。

### D-3 安全门禁

任务：

1. 租户越权回归测试。
2. 权限绕过与高风险动作审批测试。
3. 日志脱敏与密钥扫描。

验收：安全阻断项为 0。

### D-4 成本门禁

任务：

1. 任务级成本统计。
2. 模型路由与降级策略验证。
3. 租户预算告警验证。

验收：成本 P95 不突破基线 1.2x。

### Gate D 输出汇总

1. `docs/design/2026-02-22-gate-d-four-gates-checklist.md`

## 8. Gate E：灰度与回滚

### E-1 灰度策略

1. 先按租户白名单灰度。
2. 再按项目规模分层放量。
3. 高风险任务始终保留 HITL。

### E-2 回滚策略

1. 触发条件：任一门禁指标连续超阈值。
2. 回滚顺序：模型配置 -> 检索参数 -> 工作流版本 -> 发布版本。
3. 回滚后必须触发一次回放验证。

验收：30 分钟内完成回滚并恢复服务。

Gate E 输出物：

1. `docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md`

## 9. Gate F：运行优化

### F-1 数据回流

1. DLQ 样本回流到反例集。
2. 人审改判样本回流到黄金集候选。
3. 每次版本迭代更新评估数据集版本号。

### F-2 策略优化

1. 调整 selector 规则与阈值。
2. 调整评分校准参数。
3. 更新工具权限与审批策略。

验收：连续两轮迭代指标稳定改善。

Gate F 输出物：

1. `docs/design/2026-02-22-gate-f-operations-optimization-checklist.md`

## 10. 轨道任务清单（可直接执行）

### T1 API 与任务系统（14项）

1. 统一响应模型与错误模型。
2. 幂等键中间件。
3. `jobs` 查询接口。
4. 写接口异步化改造。
5. trace/request_id 贯穿。
6. 任务重试策略实现。
7. 任务取消策略实现。
8. 状态事件发布。
9. 任务审计落库。
10. 并发冲突处理。
11. 限流策略。
12. 回放测试接口（内部）。
13. 运维查询接口。
14. API 契约回归测试。

### T2 解析与建库（18项）

1. 解析器路由器。
2. 文件探测与 manifest。
3. MinerU 文件发现链。
4. `context_list` 兼容。
5. bbox 归一化。
6. heading_path 提取。
7. chunk 切分器。
8. chunk 合并规则。
9. chunk 去重策略。
10. metadata 最小字段校验。
11. PG chunks 入库。
12. Chroma 索引写入。
13. parse 错误分类。
14. fallback OCR 路径。
15. 解析耗时指标。
16. 样本回放脚本。
17. 引用可回跳验证。
18. 解析链路集成测试。

### T3 检索与评分（19项）

1. 查询标准化。
2. 约束抽取器。
3. 约束保持改写器。
4. mode selector。
5. LightRAG 参数适配。
6. include references 开关。
7. metadata 过滤器。
8. SQL 白名单支路。
9. rerank 组件。
10. rerank 降级策略。
11. evidence packing。
12. 规则引擎。
13. LLM 评分器。
14. 置信度计算器。
15. 评分校准（P1）。
16. citation coverage 检查器。
17. 幻觉保护检查器。
18. 评分结果 schema。
19. 检索评分集成测试。

### T4 工作流（13项）

1. 状态对象定义。
2. 节点边界定义。
3. 条件路由。
4. checkpoint 持久化。
5. `thread_id` 策略。
6. interrupt 节点。
7. resume API 适配。
8. side effect 提交节点。
9. 幂等保护。
10. 错误路由 DLQ。
11. 状态观测埋点。
12. 回放测试场景。
13. 恢复演练脚本。

### T5 数据与安全（10项）

1. 核心表与索引落地。
2. RLS 全量策略。
3. tenant 注入中间件。
4. Redis key 规范。
5. 密钥与配置治理。
6. 审计日志落地。
7. legal hold 控制。
8. 高风险动作审批。
9. 安全扫描基线。
10. 安全集成回归。

### T6 前端（10项）

1. 路由与权限门控。
2. 上传页任务状态。
3. 评估页点对点表格。
4. 证据面板。
5. PDF 页码跳转。
6. bbox 高亮层。
7. 人审操作面板。
8. DLQ 管理页。
9. 错误与重试提示。
10. E2E 场景覆盖。

### T7 测试与观测（12项）

1. 单元测试基线。
2. 集成测试基线。
3. E2E 测试基线。
4. RAGAS 脚本。
5. DeepEval 脚本。
6. RAGChecker 触发器（P1）。
7. 指标看板定义。
8. Trace 关联规则。
9. 告警策略。
10. 压测脚本。
11. 漂移检测作业。
12. 周期复盘模板。

### T8 发布与运维（7项）

1. 环境配置模板。
2. 灰度发布剧本。
3. 回滚剧本。
4. DLQ 处置剧本。
5. 事故 runbook 演练。
6. 变更审批流。
7. 发布门禁流水线。

## 11. 明确不做项

1. 用周计划替代 Gate 证据机制。
2. 在主链路引入未验证的重检索框架。
3. 跳过人审直接自动终审。

## 12. 完成定义（DoD）

同时满足：

1. SSOT 与专项文档一致。
2. 主链路 E2E 可运行。
3. 四门禁报告可复核。
4. 灰度和回滚演练通过。
5. 运维与事故流程可执行。

## 13. 参考来源（核验日期：2026-02-21）

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. LangGraph docs: https://docs.langchain.com/oss/python/langgraph/
3. LangChain docs: https://docs.langchain.com/oss/python/langchain/
4. FastAPI docs: https://fastapi.tiangolo.com/

## 14. 生产能力阶段补充（2026-02-22）

说明：Gate A-F 完成后，进入“生产能力填充阶段”，用于将骨架替换为真实实现，不改变既有契约与状态机语义。

补充计划：

1. `docs/plans/2026-02-22-production-capability-plan.md`

补充专项规范：

1. `docs/design/2026-02-22-persistence-and-queue-production-spec.md`
2. `docs/design/2026-02-22-parser-and-retrieval-production-spec.md`
3. `docs/design/2026-02-22-workflow-and-worker-production-spec.md`
4. `docs/design/2026-02-22-security-and-multitenancy-production-spec.md`
5. `docs/design/2026-02-22-observability-and-deploy-production-spec.md`

执行原则：

1. 先更新文档契约，再替换实现。
2. 每条轨道独立验收，最后统一真栈回放收口。
3. 任一轨道故障可独立回退，不破坏整体骨架契约。
