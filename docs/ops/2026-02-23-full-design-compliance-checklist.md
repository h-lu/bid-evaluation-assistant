# 全量设计条款对齐核对清单

> 日期：2026-02-23
> 范围：docs/design、docs/plans、docs/datasets（含生产级文档）
> 说明：逐条款核对，状态为 已实现/部分实现/未实现/未验证。

**精校批次 1（条款级复核完成）**
覆盖：`docs/plans/2026-02-21-end-to-end-unified-design.md`、`docs/plans/2026-02-22-production-capability-plan.md`

**文件：docs/plans/2026-02-21-end-to-end-unified-design.md**
1. 状态=部分实现 | 条款=系统定位：AI 生成“可解释评分建议”，专家做最终裁量。 | 证据=HITL/报告存在，但终审发布流未实现 | 参考=app/langgraph_runtime.py, app/store.py, frontend/src/views/EvaluationReportView.vue
2. 状态=已实现 | 条款=主链路：上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档。 | 证据=E2E 通过 | 参考=frontend/scripts/e2e-smoke.mjs, docs/ops/2026-02-23-n9-frontend-e2e-evidence.md
3. 状态=已实现 | 条款=任务模型：长任务异步化，状态以 job_id 为准。 | 证据=202+job_id | 参考=app/main.py, docs/design/2026-02-21-rest-api-specification.md
4. 状态=已实现 | 条款=失败模型：failed 为 DLQ 子流程结果。 | 证据=状态机实现 | 参考=app/store.py, tests/test_worker_runtime.py
5. 状态=部分实现 | 条款=隔离模型：API/DB/Vector/Cache/Queue 五层租户隔离。 | 证据=API/DB/Queue 有，Vector/Cache 未落地 | 参考=app/main.py, app/db/rls.py, app/queue_backend.py
6. 状态=已实现 | 条款=发布模型：质量/性能/安全/成本四门禁同时达标放量。 | 证据=门禁接口与证据 | 参考=app/quality_gates.py, app/performance_gates.py, app/security_gates.py, app/cost_gates.py, docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=部分实现 | 条款=每个评分项必须有证据引用。 | 证据=评分项含 citations，但真实 LLM 链路未落地 | 参考=app/store.py
8. 状态=部分实现 | 条款=专家保留最终判定权与改判权。 | 证据=HITL 机制有，终审发布/改判流程缺失 | 参考=app/langgraph_runtime.py, frontend/src/views/EvaluationReportView.vue
9. 状态=部分实现 | 条款=终审记录必须保留审计链条。 | 证据=审计日志有，但终审动作缺失 | 参考=app/store.py
10. 状态=已实现 | 条款=任何写操作必须有幂等策略。 | 证据=Idempotency-Key | 参考=app/main.py, app/store.py
11. 状态=部分实现 | 条款=无 trace_id 的请求视为不合规请求。 | 证据=有严格开关但默认未强制 | 参考=app/main.py
12. 状态=部分实现 | 条款=审计日志不可篡改。 | 证据=哈希链字段有，但不可篡改存储未验证 | 参考=app/store.py
13. 状态=已实现 | 条款=legal hold 对象不可被自动清理。 | 证据=cleanup 阻断 | 参考=app/store.py
14. 状态=已实现 | 条款=高风险动作必须双人复核。 | 证据=DLQ discard/legal hold release 双 reviewer | 参考=app/main.py, app/store.py
15. 状态=部分实现 | 条款=content_list.json 为定位真值；full.md 为结构真值。 | 证据=解析规范存在但真实产物未落地 | 参考=app/parser_adapters.py
16. 状态=部分实现 | 条款=bbox 统一归一化为 [x0,y0,x1,y1]。 | 证据=引用对象遵守，解析链路未实证 | 参考=app/store.py, frontend/src/views/EvaluationReportView.vue
17. 状态=部分实现 | 条款=检索模式 selector 自动选 local/global/hybrid/mix。 | 证据=mode_hint 支持，真实 LightRAG 未落地 | 参考=app/store.py
18. 状态=未实现 | 条款=SQL 支路只允许白名单字段。 | 证据=未见 SQL 检索实现 | 参考=-
19. 状态=部分实现 | 条款=规则引擎硬判定 + LLM 软评分组合完成。 | 证据=规则/评分为 stub | 参考=app/store.py
20. 状态=已实现 | 条款=LangGraph checkpointer 持久化，thread_id 作为恢复指针。 | 证据=LangGraph runtime | 参考=app/langgraph_runtime.py, docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md
21. 状态=已实现 | 条款=interrupt 仅用于人工决策与高风险动作确认。 | 证据=HITL interrupt | 参考=app/langgraph_runtime.py
22. 状态=已实现 | 条款=副作用节点必须声明幂等键。 | 证据=幂等与 outbox 机制 | 参考=app/store.py
23. 状态=已实现 | 条款=重试上限 3 次，指数退避+抖动。 | 证据=worker retry 配置与逻辑 | 参考=app/store.py
24. 状态=已实现 | 条款=第 4 次失败写入 DLQ，再标记 failed。 | 证据=DLQ 状态机 | 参考=app/store.py
25. 状态=已实现 | 条款=DLQ 支持 requeue/discard，discard 需双人复核。 | 证据=API 与逻辑 | 参考=app/main.py, app/store.py
26. 状态=部分实现 | 条款=API 层 tenant_id 只来源 JWT。 | 证据=目前使用 header | 参考=app/main.py
27. 状态=部分实现 | 条款=DB 层核心表全量 tenant_id + RLS。 | 证据=有 RLS manager，但需启用 | 参考=app/db/rls.py
28. 状态=部分实现 | 条款=检索层必须带 tenant_id+project_id 过滤。 | 证据=检索 stub | 参考=app/store.py
29. 状态=部分实现 | 条款=缓存与队列 key 与消息头 tenant 前缀。 | 证据=queue 前缀已做，缓存未落地 | 参考=app/queue_backend.py
30. 状态=部分实现 | 条款=性能阈值（API/解析/评估/检索 P95）。 | 证据=未见压测报告 | 参考=-
31. 状态=部分实现 | 条款=质量阈值（RAGAS/DeepEval/citation）。 | 证据=门禁接口存在，离线评估未全量 | 参考=app/quality_gates.py
32. 状态=部分实现 | 条款=安全阈值（越权=0/审计覆盖/hold 删除=0）。 | 证据=逻辑有，真实演练不全 | 参考=app/security_gates.py
33. 状态=部分实现 | 条款=成本阈值与降级策略。 | 证据=成本门禁有，真实成本采集未落地 | 参考=app/cost_gates.py
34. 状态=已实现 | 条款=Gate A-F 推进模型与证据最小集合。 | 证据=证据文档齐全 | 参考=docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/plans/2026-02-22-production-capability-plan.md**
1. 状态=已实现 | 条款=Gate C-F 骨架可运行。 | 证据=API/测试 | 参考=tests/*, app/main.py
2. 状态=部分实现 | 条款=存储/队列真栈替换。 | 证据=Postgres/Redis 实现存在但未强制 | 参考=app/repositories/*, app/queue_backend.py
3. 状态=部分实现 | 条款=解析/检索/评分真实适配器驱动。 | 证据=parser stub | 参考=app/parser_adapters.py
4. 状态=已实现 | 条款=LangGraph checkpoint + interrupt/resume 持久化。 | 证据=LangGraph runtime | 参考=app/langgraph_runtime.py
5. 状态=部分实现 | 条款=API/DB/Vector/Cache/Queue 五层隔离回归。 | 证据=Vector/Cache 未落地 | 参考=app/main.py, app/db/rls.py, app/queue_backend.py
6. 状态=部分实现 | 条款=灰度/回滚/回放可执行。 | 证据=脚本/证据有，真实环境未验证 | 参考=docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=已实现 | 条款=证据产物包含契约测试/集成/性能/安全/回滚。 | 证据=ops 文档 | 参考=docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=部分实现 | 条款=真栈 E2E 跑通。 | 证据=当前为模拟链路 | 参考=docs/ops/2026-02-23-n9-frontend-e2e-evidence.md
9. 状态=部分实现 | 条款=30 分钟内回滚并完成回放。 | 证据=脚本/证据有，未见真实演练时间窗口 | 参考=docs/ops/2026-02-22-backend-rollback-runbook.md
10. 状态=未实现 | 条款=生产环境 SLO 基线与容量压测正式报告。 | 证据=缺 | 参考=-
11. 状态=部分实现 | 条款=安全合规闭环完整演练并归档。 | 证据=有 drill 脚本/证据但不完整 | 参考=docs/ops/2026-02-23-production-drill-evidence.md
12. 状态=未实现 | 条款=自动化运维深度（告警抑制、自动降级、自动回放编排）。 | 证据=缺 | 参考=-
13. 状态=未实现 | 条款=评估数据集治理/反例与黄金集迭代策略。 | 证据=缺 | 参考=docs/datasets/eval-dataset-governance.md
14. 状态=未实现 | 条款=成本治理精调与预算预测告警优化。 | 证据=缺 | 参考=-
15. 状态=未实现 | 条款=多区域容灾与跨地域部署。 | 证据=缺 | 参考=-
16. 状态=未实现 | 条款=更细粒度权限模型与策略平台化。 | 证据=缺 | 参考=-
17. 状态=未实现 | 条款=高级检索优化（图谱增强等）。 | 证据=缺 | 参考=-

**精校批次 2（条款级复核完成）**
覆盖：`docs/design/2026-02-22-persistence-and-queue-production-spec.md`、`docs/design/2026-02-22-parser-and-retrieval-production-spec.md`、`docs/design/2026-02-22-workflow-and-worker-production-spec.md`、`docs/design/2026-02-22-security-and-multitenancy-production-spec.md`、`docs/design/2026-02-22-observability-and-deploy-production-spec.md`

**文件：docs/design/2026-02-22-persistence-and-queue-production-spec.md**
1. 状态=部分实现 | 条款=memory/sqlite 升级为 PostgreSQL + Redis 生产实现。 | 证据=实现存在但未强制真栈 | 参考=app/repositories/*, app/queue_backend.py
2. 状态=已实现 | 条款=保持 API 契约/错误码/状态机语义不变。 | 证据=测试通过 | 参考=tests/test_store_persistence_backend.py
3. 状态=部分实现 | 条款=jobs/workflow_checkpoints/dlq_items/audit_logs/evaluation_reports/documents/document_chunks 真值迁移。 | 证据=仓储层实现 | 参考=app/repositories/*
4. 状态=已实现 | 条款=幂等/outbox 事件可靠投递与消费去重。 | 证据=outbox 机制与测试 | 参考=app/store.py, tests/test_internal_outbox_queue_api.py
5. 状态=已实现 | 条款=Redis 队列 ack/nack/retry/DLQ。 | 证据=RedisQueueBackend | 参考=app/queue_backend.py
6. 状态=部分实现 | 条款=DB RLS 注入与强校验。 | 证据=RLS manager 存在但默认未启用 | 参考=app/db/rls.py
7. 状态=已实现 | 条款=对象存储 WORM/hold/cleanup 联动。 | 证据=WORM 实现与证据 | 参考=app/object_storage.py, docs/ops/2026-02-23-n6-worm-api-evidence.md
8. 状态=部分实现 | 条款=事务与 outbox 同事务提交。 | 证据=PostgresTxRunner 存在，未见显式同事务 outbox 约束 | 参考=app/db/postgres.py
9. 状态=已实现 | 条款=重试失败不得破坏状态机时序。 | 证据=状态流转测试 | 参考=tests/test_worker_runtime.py
10. 状态=已实现 | 条款=queue key 命名规范与 tenant 前缀。 | 证据=queue_key | 参考=app/queue_backend.py
11. 状态=部分实现 | 条款=outbox relay 幂等键与状态。 | 证据=outbox records 在 store 中实现，但 relay worker 未见 | 参考=app/store.py
12. 状态=部分实现 | 条款=灰度切换与回退脚本。 | 证据=runbook 存在，真实演练未全量 | 参考=docs/ops/2026-02-22-backend-rollback-runbook.md
13. 状态=已实现 | 条款=对象存储抽象 + local/s3。 | 证据=object_storage.py | 参考=app/object_storage.py
14. 状态=已实现 | 条款=storage_uri/report_uri 记录。 | 证据=report/document 写入 | 参考=app/store.py
15. 状态=部分实现 | 条款=测试与验证命令覆盖。 | 证据=pytest 通过，但真栈回放未见 | 参考=tests/*
16. 状态=部分实现 | 条款=退出条件 P1 完成定义。 | 证据=部分达成 | 参考=docs/ops/2026-02-23-true-stack-enforcement-evidence.md

**文件：docs/design/2026-02-22-parser-and-retrieval-production-spec.md**
1. 状态=部分实现 | 条款=MinerU/Docling/OCR 适配器统一接口。 | 证据=parser_adapters 存在但真实集成缺失 | 参考=app/parser_adapters.py
2. 状态=部分实现 | 条款=parse manifest 与 chunk 元数据真实入库。 | 证据=manifest/仓储实现 | 参考=app/repositories/parse_manifests.py
3. 状态=部分实现 | 条款=LightRAG 检索链路与 metadata 过滤真实化。 | 证据=模式参数存在，未见 LightRAG 集成 | 参考=app/store.py
4. 状态=部分实现 | 条款=rerank 降级与约束保持改写真实化。 | 证据=rerank stub | 参考=app/store.py

**文件：docs/design/2026-02-22-workflow-and-worker-production-spec.md**
1. 状态=已实现 | 条款=LangGraph checkpointer 持久化后端。 | 证据=LangGraph runtime | 参考=app/langgraph_runtime.py
2. 状态=已实现 | 条款=thread_id 生成/传递/恢复策略。 | 证据=store/langgraph runtime | 参考=app/store.py, app/langgraph_runtime.py
3. 状态=已实现 | 条款=HITL interrupt/resume 与审计一致性。 | 证据=resume + audit | 参考=app/store.py
4. 状态=已实现 | 条款=worker 并发/重试/DLQ 路由。 | 证据=worker runtime + tests | 参考=app/worker_runtime.py, tests/test_worker_runtime.py

**文件：docs/design/2026-02-22-security-and-multitenancy-production-spec.md**
1. 状态=未实现 | 条款=JWT 可信来源与租户注入链路。 | 证据=当前 header 注入 | 参考=app/main.py
2. 状态=部分实现 | 条款=API 层越权阻断与审计。 | 证据=tenant 校验与 audit | 参考=app/store.py
3. 状态=部分实现 | 条款=DB RLS 与向量检索 metadata 过滤一致化。 | 证据=RLS manager 存在，向量过滤缺失 | 参考=app/db/rls.py
4. 状态=已实现 | 条款=高风险动作审批策略强制执行。 | 证据=双 reviewer | 参考=app/store.py

**文件：docs/design/2026-02-22-observability-and-deploy-production-spec.md**
1. 状态=部分实现 | 条款=指标/日志/Trace 统一语义。 | 证据=trace_id + audit，但统一平台缺失 | 参考=app/main.py, app/store.py
2. 状态=部分实现 | 条款=SLO 与告警分级（P0/P1/P2）。 | 证据=脚本存在，但告警链路未落地 | 参考=app/ops/slo_probe.py
3. 状态=部分实现 | 条款=staging 回放、canary、rollback 脚本化。 | 证据=runbook/脚本 | 参考=docs/ops/2026-02-22-backend-rollback-runbook.md
4. 状态=未实现 | 条款=事故 runbook 与变更管理与流水线联动。 | 证据=缺 | 参考=-

**精校批次 3（条款级复核完成）**
覆盖：`docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md`、`docs/design/2026-02-21-error-handling-and-dlq-spec.md`、`docs/design/2026-02-21-data-model-and-storage-spec.md`、`docs/design/2026-02-21-security-design.md`、`docs/design/2026-02-21-testing-strategy.md`、`docs/design/2026-02-21-frontend-interaction-spec.md`

**文件：docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md**
1. 状态=已实现 | 条款=核心字段命名冻结（tenant_id...resume_token）。 | 证据=一致字段 | 参考=app/main.py, app/store.py
2. 状态=已实现 | 条款=评分与复核字段（confidence/citation_coverage/needs_manual_decision/needs_human_review）。 | 证据=字段存在 | 参考=app/store.py
3. 状态=已实现 | 条款=任务状态字典。 | 证据=ALLOWED_TRANSITIONS | 参考=app/store.py
4. 状态=部分实现 | 条款=评估流程状态字典（upload_received...archived）。 | 证据=未落地完整状态流 | 参考=app/store.py
5. 状态=已实现 | 条款=DLQ 条目状态与 discard 双人复核。 | 证据=DLQ 双 reviewer | 参考=app/store.py
6. 状态=部分实现 | 条款=错误码字典完整覆盖。 | 证据=多数落地，部分未用 | 参考=app/errors.py
7. 状态=部分实现 | 条款=角色字典与高风险权限。 | 证据=前端角色矩阵有，后端未强校验 | 参考=frontend/src/stores/session.js
8. 状态=已实现 | 条款=Citation 最小对象字段（text/context/page/bbox）。 | 证据=citation source | 参考=app/main.py, app/store.py
9. 状态=部分实现 | 条款=同义词映射（content_list/context_list）。 | 证据=parser 路由兼容未完整 | 参考=app/parser_adapters.py

**文件：docs/design/2026-02-21-error-handling-and-dlq-spec.md**
1. 状态=已实现 | 条款=错误分类与响应格式。 | 证据=error envelope | 参考=app/errors.py, app/main.py
2. 状态=已实现 | 条款=DLQ 状态机与操作（requeue/discard）。 | 证据=DLQ API | 参考=app/main.py, app/store.py
3. 状态=已实现 | 条款=legal hold/retention cleanup 阻断。 | 证据=cleanup 阻断 | 参考=app/store.py
4. 状态=已实现 | 条款=新增错误码需更新 spec。 | 证据=DOC_STORAGE_* 已更新 | 参考=docs/design/2026-02-21-error-handling-and-dlq-spec.md

**文件：docs/design/2026-02-21-data-model-and-storage-spec.md**
1. 状态=部分实现 | 条款=核心表结构定义。 | 证据=仓储与表创建存在，但非全量 | 参考=app/repositories/*
2. 状态=部分实现 | 条款=索引与唯一约束。 | 证据=部分表索引实现 | 参考=app/repositories/*
3. 状态=部分实现 | 条款=RLS 全覆盖。 | 证据=RLS manager 有，未默认启用 | 参考=app/db/rls.py
4. 状态=已实现 | 条款=storage_uri/manifest_uri/report_uri 语义。 | 证据=store 持久化 | 参考=app/store.py
5. 状态=已实现 | 条款=legal hold/retention。 | 证据=WORM 实现 | 参考=app/object_storage.py
6. 状态=未实现 | 条款=迁移/回滚流程与脚本。 | 证据=缺 | 参考=-

**文件：docs/design/2026-02-21-security-design.md**
1. 状态=部分实现 | 条款=API 层 tenant 注入与阻断。 | 证据=header 注入 | 参考=app/main.py
2. 状态=部分实现 | 条款=DB 层 RLS 强隔离。 | 证据=RLS manager 可选 | 参考=app/db/rls.py
3. 状态=部分实现 | 条款=审计完整性（prev_hash/audit_hash）。 | 证据=审计字段 | 参考=app/store.py
4. 状态=已实现 | 条款=高风险动作双人复核。 | 证据=DLQ/hold release | 参考=app/store.py

**文件：docs/design/2026-02-21-testing-strategy.md**
1. 状态=部分实现 | 条款=契约/集成/E2E/门禁覆盖。 | 证据=pytest + E2E + gate tests | 参考=tests/*, docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=部分实现 | 条款=性能/安全/质量回归。 | 证据=门禁接口有，未见压测报告 | 参考=app/quality_gates.py

**文件：docs/design/2026-02-21-frontend-interaction-spec.md**
1. 状态=已实现 | 条款=评估详情页字段展示。 | 证据=report view | 参考=frontend/src/views/EvaluationReportView.vue
2. 状态=已实现 | 条款=citation 回跳与 bbox 高亮。 | 证据=PDF.js + bbox 映射 | 参考=frontend/src/views/EvaluationReportView.vue
3. 状态=已实现 | 条款=人工复核页与 resume_token。 | 证据=review form | 参考=frontend/src/views/EvaluationReportView.vue
4. 状态=部分实现 | 条款=SSE -> polling 回退。 | 证据=当前仅 polling | 参考=frontend/src/views/JobsView.vue
5. 状态=已实现 | 条款=DLQ 管理页与双人复核输入。 | 证据=DLQ view | 参考=frontend/src/views/DlqView.vue

**精校批次 4（条款级复核完成）**
覆盖：`docs/design/2026-02-21-rest-api-specification.md`、`docs/design/2026-02-21-openapi-v1.yaml`、`docs/design/2026-02-21-retrieval-and-scoring-spec.md`、`docs/design/2026-02-21-mineru-ingestion-spec.md`、`docs/design/2026-02-21-job-system-and-retry-spec.md`、`docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md`

**文件：docs/design/2026-02-21-rest-api-specification.md**
1. 状态=已实现 | 条款=REST 路由与响应 envelope。 | 证据=main.py | 参考=app/main.py
2. 状态=已实现 | 条款=POST /evaluations/{id}/resume 返回 202 + job_id。 | 证据=API | 参考=app/main.py
3. 状态=已实现 | 条款=GET /evaluations/{id}/report。 | 证据=API | 参考=app/main.py
4. 状态=已实现 | 条款=GET /documents/{id}/raw。 | 证据=API | 参考=app/main.py
5. 状态=已实现 | 条款=citation source schema。 | 证据=API | 参考=app/main.py
6. 状态=部分实现 | 条款=所有写接口 tenant_id 仅从 JWT。 | 证据=header 注入 | 参考=app/main.py

**文件：docs/design/2026-02-21-openapi-v1.yaml**
1. 状态=已实现 | 条款=OpenAPI schema 与 REST 对齐。 | 证据=OpenAPI | 参考=docs/design/2026-02-21-openapi-v1.yaml
2. 状态=已实现 | 条款=EvaluationCriteriaResult 扩展字段。 | 证据=已补齐 | 参考=docs/design/2026-02-21-openapi-v1.yaml

**文件：docs/design/2026-02-21-retrieval-and-scoring-spec.md**
1. 状态=已实现 | 条款=criteria 输出字段与总分公式。 | 证据=评分实现 | 参考=app/store.py
2. 状态=已实现 | 条款=confidence 公式。 | 证据=评分实现 | 参考=app/store.py
3. 状态=已实现 | 条款=HITL 触发条件。 | 证据=评分实现 | 参考=app/store.py
4. 状态=部分实现 | 条款=检索/重排策略真实化。 | 证据=stub | 参考=app/store.py
5. 状态=部分实现 | 条款=claim -> citation 校验。 | 证据=stub | 参考=app/store.py

**文件：docs/design/2026-02-21-mineru-ingestion-spec.md**
1. 状态=部分实现 | 条款=解析输出 content_list/full.md 真值。 | 证据=parser stub | 参考=app/parser_adapters.py
2. 状态=部分实现 | 条款=bbox 归一化与 chunk 元数据。 | 证据=引用结构 | 参考=app/store.py

**文件：docs/design/2026-02-21-job-system-and-retry-spec.md**
1. 状态=已实现 | 条款=job 状态机/重试/DLQ。 | 证据=store/workers | 参考=app/store.py, app/worker_runtime.py
2. 状态=已实现 | 条款=指数退避与重试上限。 | 证据=worker config | 参考=app/store.py

**文件：docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md**
1. 状态=已实现 | 条款=契约与骨架实现要求。 | 证据=API 骨架 | 参考=app/main.py, tests/*

**精校批次 5（条款级复核完成）**
覆盖：`docs/design/2026-02-21-agent-tool-governance.md`、`docs/design/2026-02-21-agent-evals-observability.md`、`docs/design/2026-02-21-agent-development-lifecycle.md`、`docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md`、`docs/design/2026-02-21-api-contract-test-samples.md`、`docs/design/2026-02-21-legacy-detail-triage.md`、`docs/plans/2026-02-21-gate-c-api-skeleton-design.md`、`docs/plans/2026-02-21-gate-c-api-skeleton-implementation.md`、`docs/plans/2026-02-23-session-handoff.md`、`docs/design/2026-02-21-implementation-plan.md`

**文件：docs/design/2026-02-21-agent-tool-governance.md**
1. 状态=已实现 | 条款=工具注册表与风险分级表。 | 证据=ToolSpec + registry | 参考=app/tools_registry.py, tests/test_tool_registry.py
2. 状态=部分实现 | 条款=审批拦截器/工具调用审计中间件。 | 证据=审批+tool_call 审计 | 参考=app/main.py, app/tools_registry.py
3. 状态=部分实现 | 条款=MCP/A2A 接入与安全基线。 | 证据=baseline 校验器 | 参考=app/mcp_a2a.py, tests/test_mcp_a2a.py

**文件：docs/design/2026-02-21-agent-evals-observability.md**
1. 状态=部分实现 | 条款=质量/轨迹/工具调用/citation 指标体系。 | 证据=gates 存在，缺完整评估闭环 | 参考=app/quality_gates.py
2. 状态=部分实现 | 条款=漂移检测/失败样本回流。 | 证据=缺完整实现 | 参考=-
3. 状态=部分实现 | 条款=告警与回滚联动。 | 证据=runbook 有，自动化缺失 | 参考=docs/ops/2026-02-22-backend-rollback-runbook.md

**文件：docs/design/2026-02-21-agent-development-lifecycle.md**
1. 状态=未实现 | 条款=Agent 生命周期与发布流程编排。 | 证据=缺 | 参考=-
2. 状态=未实现 | 条款=门禁/审批/回滚流程联动。 | 证据=缺 | 参考=-

**文件：docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md**
1. 状态=部分实现 | 条款=副作用边界矩阵映射与验证。 | 证据=outbox/节点存在，但矩阵未绑定 | 参考=app/store.py

**文件：docs/design/2026-02-21-api-contract-test-samples.md**
1. 状态=部分实现 | 条款=契约样例覆盖全部列举接口。 | 证据=部分测试覆盖 | 参考=tests/*
2. 状态=已实现 | 条款=统一响应模型/幂等/异步/恢复/citation 契约。 | 证据=API + tests | 参考=app/main.py, tests/*

**文件：docs/design/2026-02-21-legacy-detail-triage.md**
1. 状态=未验证 | 条款=旧需求与现状兼容性清单。 | 证据=未进行明确映射 | 参考=-

**文件：docs/plans/2026-02-21-gate-c-api-skeleton-design.md**
1. 状态=已实现 | 条款=202+job_id, resume, citation, jobs 查询。 | 证据=API | 参考=app/main.py

**文件：docs/plans/2026-02-21-gate-c-api-skeleton-implementation.md**
1. 状态=已实现 | 条款=healthz/响应封装/idempotency/核心路由。 | 证据=API + tests | 参考=app/main.py, tests/*

**文件：docs/plans/2026-02-23-session-handoff.md**
1. 状态=已实现 | 条款=阶段完成与问题清单更新。 | 证据=当前实现/证据已补齐 | 参考=docs/ops/2026-02-23-ssot-gap-closure.md

**文件：docs/design/2026-02-21-implementation-plan.md**
1. 状态=部分实现 | 条款=Gate A-F 完整实现路径。 | 证据=部分执行与证据 | 参考=docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/datasets/eval-dataset-governance.md**
文件级结论：部分实现 | 说明: 已落地数据集 schema/校验/冻结脚本与发布门禁 dataset_version，样本覆盖与回流未落地
1. 状态=未实现 | 条款=保证评估结果可复现、可比较、可持续演进。 | 参考行=9 | 说明: 评估回流与全量数据集尚未落地
2. 状态=已实现 | 条款=让数据集版本成为发布门禁的一部分。 | 参考行=10 | 说明: release readiness/pipeline 强制 dataset_version
3. 状态=未实现 | 条款=建立线上失败样本到离线改进的闭环。 | 参考行=11 | 说明: 失败样本回流未落地
4. 状态=未实现 | 条款=覆盖核心业务场景。 | 参考行=17 | 说明: 全量样本未落地
5. 状态=未实现 | 条款=每次发布必须跑全量。 | 参考行=18 | 说明: 全量评估未落地
6. 状态=未实现 | 条款=幻觉诱导。 | 参考行=22 | 说明: 对抗样本未落地
7. 状态=未实现 | 条款=引用缺失。 | 参考行=23 | 说明: 对抗样本未落地
8. 状态=未实现 | 条款=冲突信息。 | 参考行=24 | 说明: 对抗样本未落地
9. 状态=未实现 | 条款=越权诱导。 | 参考行=25 | 说明: 对抗样本未落地
10. 状态=未实现 | 条款=新模板文档。 | 参考行=29 | 说明: 漂移样本未落地
11. 状态=未实现 | 条款=扫描噪声。 | 参考行=30 | 说明: 漂移样本未落地
12. 状态=未实现 | 条款=版式变化。 | 参考行=31 | 说明: 漂移样本未落地
13. 状态=未实现 | 条款=跨语种样本。 | 参考行=32 | 说明: 漂移样本未落地
14. 状态=未实现 | 条款=DLQ 典型失败样本。 | 参考行=36 | 说明: 回流样本未落地
15. 状态=未实现 | 条款=人审改判样本。 | 参考行=37 | 说明: 回流样本未落地
16. 状态=未实现 | 条款=线上投诉样本。 | 参考行=38 | 说明: 回流样本未落地
17. 状态=部分实现 | 条款=`sample_id` | 参考行=44 | 说明: schema + validate 脚本已落地
18. 状态=部分实现 | 条款=`dataset_version` | 参考行=45 | 说明: schema + validate 脚本已落地
19. 状态=部分实现 | 条款=`tenant_scope` | 参考行=46 | 说明: schema + validate 脚本已落地
20. 状态=部分实现 | 条款=`task_type` | 参考行=47 | 说明: schema + validate 脚本已落地
21. 状态=部分实现 | 条款=`input_payload_ref` | 参考行=48 | 说明: schema + validate 脚本已落地
22. 状态=部分实现 | 条款=`expected_output_or_constraints` | 参考行=49 | 说明: schema + validate 脚本已落地
23. 状态=部分实现 | 条款=`expected_citations` | 参考行=50 | 说明: schema + validate 脚本已落地
24. 状态=部分实现 | 条款=`risk_label` | 参考行=51 | 说明: schema + validate 脚本已落地
25. 状态=部分实现 | 条款=`source`（golden/adversarial/drift/online_feedback） | 参考行=52 | 说明: schema + validate 脚本已落地
26. 状态=部分实现 | 条款=`created_at` | 参考行=53 | 说明: schema + validate 脚本已落地
27. 状态=未实现 | 条款=`major`：标签语义或评估口径变更。 | 参考行=63 | 说明: 版本治理流程未落地
28. 状态=未实现 | 条款=`minor`：新增样本或新增场景。 | 参考行=64 | 说明: 版本治理流程未落地
29. 状态=未实现 | 条款=`patch`：标注修复与元数据修正。 | 参考行=65 | 说明: 版本治理流程未落地
30. 状态=未实现 | 条款=核心样本双人标注复核。 | 参考行=69 | 说明: 标注流程未落地
31. 状态=未实现 | 条款=不一致样本进入仲裁流程。 | 参考行=70 | 说明: 标注流程未落地
32. 状态=未实现 | 条款=每次发布前抽检不少于 10%。 | 参考行=71 | 说明: 质控流程未落地
33. 状态=未实现 | 条款=高风险样本必须有人审解释记录。 | 参考行=72 | 说明: 质控流程未落地
34. 状态=未实现 | 条款=允许使用 DeepEval Synthesizer 生成候选样本。 | 参考行=76 | 说明: 自动样本未落地
35. 状态=未实现 | 条款=自动样本必须通过人工抽检后才能入库。 | 参考行=77 | 说明: 自动样本未落地
36. 状态=未实现 | 条款=自动样本需标记 `generated=true` 与生成策略。 | 参考行=78 | 说明: 自动样本未落地
37. 状态=未实现 | 条款=连续两个版本无代表性的样本可退役。 | 参考行=88 | 说明: 退役流程未落地
38. 状态=未实现 | 条款=退役样本保留索引与原因记录。 | 参考行=89 | 说明: 退役流程未落地
39. 状态=未实现 | 条款=涉及事故复盘的样本不得删除。 | 参考行=90 | 说明: 退役流程未落地
40. 状态=部分实现 | 条款=没有冻结数据集版本，不允许发布。 | 参考行=94 | 说明: 有冻结脚本，发布未校验冻结状态
41. 状态=已实现 | 条款=数据集版本必须写入发布记录。 | 参考行=95 | 说明: release readiness/pipeline 写入 dataset_version
42. 状态=未实现 | 条款=发布后发现问题必须补回归样本。 | 参考行=96 | 说明: 回流未落地
43. 状态=部分实现 | 条款=数据集版本可追溯。 | 参考行=100 | 说明: 冻结 manifest 产出 checksum
44. 状态=未实现 | 条款=标注质量可抽检验证。 | 参考行=101 | 说明: 标注/质控流程未落地
45. 状态=未实现 | 条款=线上失败样本能稳定回流。 | 参考行=102 | 说明: 回流未落地
46. 状态=未实现 | 条款=RAGAS: https://github.com/explodinggradients/ragas | 参考行=106 | 说明: 评估链路未落地
47. 状态=未实现 | 条款=DeepEval: https://github.com/confident-ai/deepeval | 参考行=107 | 说明: 评估链路未落地

**文件：docs/design/2026-02-21-agent-development-lifecycle.md**
文件级结论：未实现 | 说明: 缺发布流程编排与审批流水线实现
1. 状态=未实现 | 条款=关注流程与证据，不展开函数级代码实现。 | 参考行=13 | 说明: 缺发布流程编排与审批流水线实现
2. 状态=未实现 | 条款=约束多 Agent 协作方式与发布门禁。 | 参考行=14 | 说明: 缺发布流程编排与审批流水线实现
3. 状态=未实现 | 条款=与 SSOT 和专项设计文档保持一致。 | 参考行=15 | 说明: 缺发布流程编排与审批流水线实现
4. 状态=未实现 | 条款=从简单可控工作流开始，避免一上来全自治多 Agent。 | 参考行=19 | 说明: 缺发布流程编排与审批流水线实现
5. 状态=未实现 | 条款=Agent 必须是可观测状态机，而非纯 Prompt 黑箱。 | 参考行=20 | 说明: 缺发布流程编排与审批流水线实现
6. 状态=未实现 | 条款=工具契约必须标准化（输入/输出/副作用/权限）。 | 参考行=21 | 说明: 缺发布流程编排与审批流水线实现
7. 状态=未实现 | 条款=高风险动作必须人类介入（interrupt/approval）。 | 参考行=22 | 说明: 缺发布流程编排与审批流水线实现
8. 状态=未实现 | 条款=发布依赖 eval + trace + 回滚能力，不依赖时间节点。 | 参考行=23 | 说明: 缺发布流程编排与审批流水线实现
9. 状态=未实现 | 条款=先建立高性能基线，再做成本优化（模型降配）。 | 参考行=24 | 说明: 缺发布流程编排与审批流水线实现
10. 状态=未实现 | 条款=每个子任务必须可在单次会话内验证。 | 参考行=85 | 说明: 缺发布流程编排与审批流水线实现
11. 状态=未实现 | 条款=子任务必须明确输入文件与输出文件。 | 参考行=86 | 说明: 缺发布流程编排与审批流水线实现
12. 状态=未实现 | 条款=子任务必须附验收命令或检查项。 | 参考行=87 | 说明: 缺发布流程编排与审批流水线实现
13. 状态=未实现 | 条款=文档/代码变更执行。 | 参考行=98 | 说明: 缺发布流程编排与审批流水线实现
14. 状态=未实现 | 条款=测试、回归、指标对比。 | 参考行=99 | 说明: 缺发布流程编排与审批流水线实现
15. 状态=未实现 | 条款=变更影响分析与草案。 | 参考行=100 | 说明: 缺发布流程编排与审批流水线实现
16. 状态=未实现 | 条款=需求优先级与风险裁量。 | 参考行=104 | 说明: 缺发布流程编排与审批流水线实现
17. 状态=未实现 | 条款=高风险动作审批。 | 参考行=105 | 说明: 缺发布流程编排与审批流水线实现
18. 状态=未实现 | 条款=发布/回滚决策。 | 参考行=106 | 说明: 缺发布流程编排与审批流水线实现
19. 状态=未实现 | 条款=变更前：契约检查。 | 参考行=110 | 说明: 缺发布流程编排与审批流水线实现
20. 状态=未实现 | 条款=变更中：局部验证 + 回归。 | 参考行=111 | 说明: 缺发布流程编排与审批流水线实现
21. 状态=未实现 | 条款=变更后：门禁评估 + 安全检查。 | 参考行=112 | 说明: 缺发布流程编排与审批流水线实现
22. 状态=未实现 | 条款=发布前：灰度准入审查。 | 参考行=113 | 说明: 缺发布流程编排与审批流水线实现
23. 状态=未实现 | 条款=`brainstorming`：需求澄清与方案分解。 | 参考行=117 | 说明: 缺发布流程编排与审批流水线实现
24. 状态=未实现 | 条款=`writing-plans`：生成可执行任务计划。 | 参考行=118 | 说明: 缺发布流程编排与审批流水线实现
25. 状态=未实现 | 条款=`subagent-driven-development`：并行执行独立任务。 | 参考行=119 | 说明: 缺发布流程编排与审批流水线实现
26. 状态=未实现 | 条款=`verification-before-completion`：交付前证据验证。 | 参考行=120 | 说明: 缺发布流程编排与审批流水线实现
27. 状态=未实现 | 条款=`requesting-code-review`：合并前问题收敛。 | 参考行=121 | 说明: 缺发布流程编排与审批流水线实现
28. 状态=未实现 | 条款=先冻结 SSOT 与专项规范。 | 参考行=125 | 说明: 缺发布流程编排与审批流水线实现
29. 状态=未实现 | 条款=再执行 Gate B-C 骨架与主链路打通。 | 参考行=126 | 说明: 缺发布流程编排与审批流水线实现
30. 状态=未实现 | 条款=然后执行 Gate D 四门禁强化。 | 参考行=127 | 说明: 缺发布流程编排与审批流水线实现
31. 状态=未实现 | 条款=最后做灰度发布与回滚演练。 | 参考行=128 | 说明: 缺发布流程编排与审批流水线实现
32. 状态=未实现 | 条款=任务粒度过大：拆分为可验证小任务。 | 参考行=132 | 说明: 缺发布流程编排与审批流水线实现
33. 状态=未实现 | 条款=只改实现不改契约：阻断合并。 | 参考行=133 | 说明: 缺发布流程编排与审批流水线实现
34. 状态=未实现 | 条款=指标回归但未发现：补 trace 观测与门禁用例。 | 参考行=134 | 说明: 缺发布流程编排与审批流水线实现
35. 状态=未实现 | 条款=频繁回滚：缩小灰度范围并提高 HITL 比例。 | 参考行=135 | 说明: 缺发布流程编排与审批流水线实现
36. 状态=未实现 | 条款=生命周期流程可复述且可执行。 | 参考行=139 | 说明: 缺发布流程编排与审批流水线实现
37. 状态=未实现 | 条款=每个 Gate 都有对应证据产物。 | 参考行=140 | 说明: 缺发布流程编排与审批流水线实现
38. 状态=未实现 | 条款=变更流程与门禁流程联动可运行。 | 参考行=141 | 说明: 缺发布流程编排与审批流水线实现
39. 状态=未实现 | 条款=Anthropic: Building effective agents | 参考行=145 | 说明: 缺发布流程编排与审批流水线实现
40. 状态=未实现 | 条款=OpenAI: A practical guide to building agents | 参考行=147 | 说明: 缺发布流程编排与审批流水线实现
41. 状态=未实现 | 条款=OpenAI Agent Builder & safety docs | 参考行=149 | 说明: 缺发布流程编排与审批流水线实现
42. 状态=未实现 | 条款=superpowers | 参考行=151 | 说明: 缺发布流程编排与审批流水线实现

**文件：docs/design/2026-02-21-agent-evals-observability.md**
文件级结论：部分实现 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
1. 状态=部分实现 | 条款=发布前可评估，发布后可监控，异常时可快速回滚。 | 参考行=9 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
2. 状态=部分实现 | 条款=评估不只看最终答案，还覆盖轨迹质量。 | 参考行=10 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
3. 状态=部分实现 | 条款=线上问题可定位到具体节点、工具、模型与版本。 | 参考行=11 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
4. 状态=部分实现 | 条款=最终输出质量。 | 参考行=26 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
5. 状态=部分实现 | 条款=轨迹步骤正确性（state transition correctness）。 | 参考行=27 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
6. 状态=部分实现 | 条款=工具调用正确性（schema + side effect）。 | 参考行=28 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
7. 状态=部分实现 | 条款=citation 可回跳性。 | 参考行=29 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
8. 状态=部分实现 | 条款=使用历史真实样本回放候选版本。 | 参考行=33 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
9. 状态=部分实现 | 条款=与基线版本做差异分析。 | 参考行=34 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
10. 状态=部分实现 | 条款=任一核心指标劣化超阈值即阻断。 | 参考行=35 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
11. 状态=部分实现 | 条款=按租户/项目分层采样。 | 参考行=39 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
12. 状态=部分实现 | 条款=高风险任务提高人工抽检比例。 | 参考行=40 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
13. 状态=部分实现 | 条款=线上失败样本回流到离线数据集。 | 参考行=41 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
14. 状态=部分实现 | 条款=RAGAS（precision/recall/faithfulness/relevancy）。 | 参考行=47 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
15. 状态=部分实现 | 条款=DeepEval（hallucination）。 | 参考行=48 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
16. 状态=部分实现 | 条款=citation resolvable rate。 | 参考行=49 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
17. 状态=部分实现 | 条款=人审后改判率。 | 参考行=50 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
18. 状态=部分实现 | 条款=非法状态流转率。 | 参考行=54 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
19. 状态=部分实现 | 条款=interrupt 触发准确率。 | 参考行=55 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
20. 状态=部分实现 | 条款=resume 成功率。 | 参考行=56 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
21. 状态=部分实现 | 条款=副作用重复执行率。 | 参考行=57 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
22. 状态=部分实现 | 条款=API/检索/解析/评估 P95。 | 参考行=61 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
23. 状态=部分实现 | 条款=队列等待时延。 | 参考行=62 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
24. 状态=部分实现 | 条款=DLQ 日增长率。 | 参考行=63 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
25. 状态=部分实现 | 条款=单任务成本 P95。 | 参考行=67 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
26. 状态=部分实现 | 条款=租户预算偏差率。 | 参考行=68 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
27. 状态=部分实现 | 条款=模型降级触发率。 | 参考行=69 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
28. 状态=部分实现 | 条款=`trace_id` | 参考行=75 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
29. 状态=部分实现 | 条款=`request_id` | 参考行=76 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
30. 状态=部分实现 | 条款=`job_id` | 参考行=77 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
31. 状态=部分实现 | 条款=`thread_id` | 参考行=78 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
32. 状态=部分实现 | 条款=`tenant_id` | 参考行=79 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
33. 状态=部分实现 | 条款=`evaluation_id` | 参考行=80 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
34. 状态=部分实现 | 条款=`node_name` | 参考行=84 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
35. 状态=部分实现 | 条款=`input_hash/output_hash` | 参考行=85 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
36. 状态=部分实现 | 条款=`latency_ms` | 参考行=86 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
37. 状态=部分实现 | 条款=`tool_calls[]` | 参考行=87 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
38. 状态=部分实现 | 条款=`error_code` | 参考行=88 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
39. 状态=部分实现 | 条款=质量核心指标跌破阈值。 | 参考行=98 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
40. 状态=部分实现 | 条款=citation 回跳率低于 98%。 | 参考行=99 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
41. 状态=部分实现 | 条款=安全回归失败。 | 参考行=100 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
42. 状态=部分实现 | 条款=文档分布漂移（版式、语言、噪声）。 | 参考行=104 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
43. 状态=部分实现 | 条款=查询分布漂移（查询意图变化）。 | 参考行=105 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
44. 状态=部分实现 | 条款=结果漂移（评分分布异常）。 | 参考行=106 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
45. 状态=部分实现 | 条款=触发快速回放验证。 | 参考行=110 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
46. 状态=部分实现 | 条款=调整 selector/评分阈值。 | 参考行=111 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
47. 状态=部分实现 | 条款=更新数据集版本。 | 参考行=112 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
48. 状态=部分实现 | 条款=质量看板：RAGAS/DeepEval/citation。 | 参考行=118 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
49. 状态=部分实现 | 条款=流程看板：状态机、HITL、DLQ。 | 参考行=119 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
50. 状态=部分实现 | 条款=成本看板：任务成本、模型分布。 | 参考行=120 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
51. 状态=部分实现 | 条款=P0：越权、主链路不可用。 | 参考行=124 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
52. 状态=部分实现 | 条款=P1：质量显著劣化、DLQ 激增。 | 参考行=125 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
53. 状态=部分实现 | 条款=P2：性能退化与成本异常。 | 参考行=126 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
54. 状态=部分实现 | 条款=每次发布必须附评估报告链接。 | 参考行=130 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
55. 状态=部分实现 | 条款=灰度期间启用加严告警阈值。 | 参考行=131 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
56. 状态=部分实现 | 条款=触发回滚后自动创建复盘任务。 | 参考行=132 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
57. 状态=部分实现 | 条款=指标采集 SDK 与日志规范。 | 参考行=136 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
58. 状态=部分实现 | 条款=评估流水线（离线 + 预发 + 灰度）。 | 参考行=137 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
59. 状态=部分实现 | 条款=漂移检测作业。 | 参考行=138 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
60. 状态=部分实现 | 条款=失败样本回流机制。 | 参考行=139 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
61. 状态=部分实现 | 条款=统一评估报告模板。 | 参考行=140 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
62. 状态=部分实现 | 条款=可从任一结果追溯到完整执行轨迹。 | 参考行=144 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
63. 状态=部分实现 | 条款=门禁阻断逻辑可自动执行。 | 参考行=145 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
64. 状态=部分实现 | 条款=告警触发到处置流程闭环可验证。 | 参考行=146 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
65. 状态=部分实现 | 条款=LangSmith/LangChain eval docs: https://docs.langchain.com/ | 参考行=150 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
66. 状态=部分实现 | 条款=RAGAS: https://github.com/explodinggradients/ragas | 参考行=151 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
67. 状态=部分实现 | 条款=DeepEval: https://github.com/confident-ai/deepeval | 参考行=152 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测
68. 状态=部分实现 | 条款=RAGChecker: https://github.com/amazon-science/RAGChecker | 参考行=153 | 说明: 有门禁与基础指标，但缺完整评估闭环与漂移检测

**文件：docs/design/2026-02-21-agent-tool-governance.md**
文件级结论：部分实现 | 说明: 工具注册表/审批/审计/MCP-A2A 基线已落地，但工具统一超时/重试/断路器、feature flag、终审发布与外部提交仍缺
1. 状态=部分实现 | 条款=工具调用可控：权限、审批、限流、回滚明确。 | 参考行=9 | 说明: 审批与注册表已落地，限流/回滚策略未固化
2. 状态=部分实现 | 条款=工具调用可追溯：输入、输出、副作用全记录。 | 参考行=10 | 说明: tool_call 审计含失败 + 输出校验，未覆盖全部工具
3. 状态=部分实现 | 条款=工具接入可扩展：支持 MCP 与 A2A 协作。 | 参考行=11 | 说明: 基线校验已落地，真实 MCP/A2A 接入未落地
4. 状态=已实现 | 条款=`name` | 参考行=17 | 说明: ToolSpec 注册表
5. 状态=已实现 | 条款=`description` | 参考行=18 | 说明: ToolSpec 注册表
6. 状态=已实现 | 条款=`input_schema`（JSON Schema） | 参考行=19 | 说明: ToolSpec + jsonschema 校验
7. 状态=已实现 | 条款=`output_schema` | 参考行=20 | 说明: ToolSpec 注册表
8. 状态=已实现 | 条款=`side_effect_level`（`read_only/state_write/external_commit`） | 参考行=21 | 说明: ToolSpec 注册表
9. 状态=已实现 | 条款=`idempotency_policy` | 参考行=22 | 说明: ToolSpec 注册表
10. 状态=已实现 | 条款=`timeout/retry_policy` | 参考行=23 | 说明: ToolSpec 注册表
11. 状态=已实现 | 条款=`owner` | 参考行=24 | 说明: ToolSpec 注册表
12. 状态=已实现 | 条款=`risk_level` | 参考行=25 | 说明: ToolSpec 注册表
13. 状态=部分实现 | 条款=`L0`：只读查询（默认可用） | 参考行=31 | 说明: 风险分级存在，尚未覆盖 L0-L2 工具
14. 状态=部分实现 | 条款=`L1`：租户内写操作（角色授权） | 参考行=32 | 说明: 风险分级存在，尚未覆盖 L0-L2 工具
15. 状态=部分实现 | 条款=`L2`：高风险写操作（二次确认） | 参考行=33 | 说明: 已覆盖 strategy_tuning_apply，其它 L2 工具未覆盖
16. 状态=已实现 | 条款=`L3`：外部提交/删除（双人复核） | 参考行=34 | 说明: dlq_discard/legal_hold_release 为 L3
17. 状态=未实现 | 条款=终审发布。 | 参考行=38 | 说明: 终审发布工具未落地
18. 状态=已实现 | 条款=DLQ discard。 | 参考行=39 | 说明: 工具+审批+审计已落地
19. 状态=已实现 | 条款=legal hold 解除。 | 参考行=40 | 说明: 工具+审批+审计已落地
20. 状态=未实现 | 条款=外部系统正式提交。 | 参考行=41 | 说明: 外部提交工具未落地
21. 状态=已实现 | 条款=必填 `reason`。 | 参考行=45 | 说明: dlq_discard/legal_hold_release 强制
22. 状态=已实现 | 条款=操作人与复核人分离。 | 参考行=46 | 说明: 双 reviewer 强制
23. 状态=已实现 | 条款=全量审计可追溯。 | 参考行=47 | 说明: tool_call 审计日志
24. 状态=已实现 | 条款=工具输入做 schema + allowlist 校验。 | 参考行=51 | 说明: jsonschema 校验
25. 状态=部分实现 | 条款=工具调用超时、重试、断路器策略统一。 | 参考行=52 | 说明: execute_tool 已落地，未覆盖全部工具
26. 状态=已实现 | 条款=高风险工具可被 feature flag 一键关闭。 | 参考行=53 | 说明: TOOL_DISABLED/TOOL_DISABLED_RISK_LEVELS
27. 状态=部分实现 | 条款=工具异常统一映射错误码。 | 参考行=54 | 说明: execute_tool 统一映射，未全链路覆盖
28. 状态=部分实现 | 条款=文档内容视为非可信输入。 | 参考行=58 | 说明: 基线规则存在，未全链路固化
29. 状态=部分实现 | 条款=禁止模型通过自然语言直接触发高风险副作用。 | 参考行=59 | 说明: 高风险动作仅走工具路径
30. 状态=部分实现 | 条款=高风险副作用必须走受控工具调用路径。 | 参考行=60 | 说明: dlq/hold 已受控，终审/外部提交未落地
31. 状态=已实现 | 条款=工具调用前执行“权限 + 上下文 + 审批”三重校验。 | 参考行=61 | 说明: 审批 + tenant 校验 + schema 校验
32. 状态=部分实现 | 条款=每个 MCP 服务声明最小权限。 | 参考行=69 | 说明: 基线校验已落地，未接入真实 MCP
33. 状态=部分实现 | 条款=会话隔离，禁止跨租户上下文复用。 | 参考行=70 | 说明: tenant 校验在 baseline
34. 状态=部分实现 | 条款=工具响应必须可审计。 | 参考行=71 | 说明: tool_call 审计记录结果摘要与失败码
35. 状态=部分实现 | 条款=明确任务状态与责任边界。 | 参考行=77 | 说明: A2A 基线校验存在，未接入
36. 状态=部分实现 | 条款=异步交付必须有回执与超时策略。 | 参考行=78 | 说明: A2A 基线校验存在，未接入
37. 状态=部分实现 | 条款=不可信外部 Agent 输出需二次校验。 | 参考行=79 | 说明: A2A 结果校验器已落地
38. 状态=已实现 | 条款=`trace_id` | 参考行=85 | 说明: tool_call 审计字段
39. 状态=已实现 | 条款=`tenant_id` | 参考行=86 | 说明: tool_call 审计字段
40. 状态=已实现 | 条款=`agent_id` | 参考行=87 | 说明: tool_call 审计字段
41. 状态=已实现 | 条款=`tool_name` | 参考行=88 | 说明: tool_call 审计字段
42. 状态=已实现 | 条款=`risk_level` | 参考行=89 | 说明: tool_call 审计字段
43. 状态=已实现 | 条款=`input_hash` | 参考行=90 | 说明: tool_call 审计字段
44. 状态=已实现 | 条款=`result_summary` | 参考行=91 | 说明: tool_call 审计字段
45. 状态=已实现 | 条款=`status` | 参考行=92 | 说明: tool_call 审计字段
46. 状态=已实现 | 条款=`latency_ms` | 参考行=93 | 说明: tool_call 审计字段
47. 状态=未实现 | 条款=工具 schema 变更需契约回归。 | 参考行=97 | 说明: 流程未固化
48. 状态=未实现 | 条款=高风险工具变更需安全评审。 | 参考行=98 | 说明: 流程未固化
49. 状态=未实现 | 条款=互操作变更需灰度验证。 | 参考行=99 | 说明: 流程未固化
50. 状态=未实现 | 条款=所有变更必须有回滚策略。 | 参考行=100 | 说明: 流程未固化
51. 状态=已实现 | 条款=工具注册表与风险分级表。 | 参考行=104 | 说明: tools_registry 已落地
52. 状态=部分实现 | 条款=高风险动作审批拦截器。 | 参考行=105 | 说明: dlq/hold 已强制，终审/外部提交未落地
53. 状态=部分实现 | 条款=工具调用审计中间件。 | 参考行=106 | 说明: tool_call 审计含失败记录，未覆盖全部工具
54. 状态=部分实现 | 条款=MCP 接入安全基线。 | 参考行=107 | 说明: enforce_mcp_baseline 已落地
55. 状态=部分实现 | 条款=A2A 外部结果校验器。 | 参考行=108 | 说明: validate_a2a_result 已落地
56. 状态=部分实现 | 条款=所有生产工具均有完整契约。 | 参考行=112 | 说明: 现有工具具备，新增工具需扩展
57. 状态=部分实现 | 条款=高风险动作无审批不可执行。 | 参考行=113 | 说明: dlq/hold 覆盖
58. 状态=部分实现 | 条款=工具调用链路可完整追溯。 | 参考行=114 | 说明: tool_call 审计覆盖已有工具
59. 状态=部分实现 | 条款=Model Context Protocol: https://modelcontextprotocol.io/ | 参考行=118 | 说明: 基线校验落地，未接入真实 MCP
60. 状态=部分实现 | 条款=Google A2A protocol: https://google.github.io/A2A/ | 参考行=119 | 说明: 基线校验落地，未接入真实 A2A
61. 状态=部分实现 | 条款=LangChain/LangGraph docs: https://docs.langchain.com/ | 参考行=120 | 说明: 基线校验落地，未接入真实互操作

**文件：docs/design/2026-02-21-api-contract-test-samples.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=为 Gate B-1/B-2 提供“可执行的契约测试样例”基线。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=覆盖统一响应模型、幂等、异步任务、HITL 恢复、citation 返回。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=为后续自动化契约测试提供最小样例集合。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=`POST /api/v1/documents/upload` | 参考行=17 | 证据: 待补
5. 状态=未验证 | 条款=`POST /api/v1/documents/{document_id}/parse` | 参考行=18 | 证据: 待补
6. 状态=未验证 | 条款=`POST /api/v1/evaluations` | 参考行=19 | 证据: 待补
7. 状态=未验证 | 条款=`POST /api/v1/evaluations/{evaluation_id}/resume` | 参考行=20 | 证据: 待补
8. 状态=未验证 | 条款=`GET /api/v1/jobs/{job_id}` | 参考行=21 | 证据: 待补
9. 状态=未验证 | 条款=`POST /api/v1/jobs/{job_id}/cancel` | 参考行=22 | 证据: 待补
10. 状态=未验证 | 条款=`GET /api/v1/jobs?status=&type=&cursor=&limit=` | 参考行=23 | 证据: 待补
11. 状态=未验证 | 条款=`GET /api/v1/citations/{chunk_id}/source` | 参考行=24 | 证据: 待补
12. 状态=未验证 | 条款=`GET /api/v1/dlq/items` | 参考行=25 | 证据: 待补
13. 状态=未验证 | 条款=`POST /api/v1/dlq/items/{item_id}/requeue` | 参考行=26 | 证据: 待补
14. 状态=未验证 | 条款=`POST /api/v1/dlq/items/{item_id}/discard` | 参考行=27 | 证据: 待补
15. 状态=未验证 | 条款=`POST /api/v1/retrieval/query` | 参考行=28 | 证据: 待补
16. 状态=未验证 | 条款=`POST /api/v1/retrieval/preview` | 参考行=29 | 证据: 待补
17. 状态=未验证 | 条款=`GET /api/v1/evaluations/{evaluation_id}/report` | 参考行=30 | 证据: 待补
18. 状态=未验证 | 条款=`GET /api/v1/documents/{document_id}` | 参考行=31 | 证据: 待补
19. 状态=未验证 | 条款=`GET /api/v1/documents/{document_id}/chunks` | 参考行=32 | 证据: 待补
20. 状态=未验证 | 条款=`GET /api/v1/evaluations/{evaluation_id}/audit-logs` | 参考行=33 | 证据: 待补
21. 状态=未验证 | 条款=`POST /api/v1/internal/quality-gates/evaluate` | 参考行=34 | 证据: 待补
22. 状态=未验证 | 条款=`POST /api/v1/internal/performance-gates/evaluate` | 参考行=35 | 证据: 待补
23. 状态=未验证 | 条款=`POST /api/v1/internal/security-gates/evaluate` | 参考行=36 | 证据: 待补
24. 状态=未验证 | 条款=`POST /api/v1/internal/cost-gates/evaluate` | 参考行=37 | 证据: 待补
25. 状态=未验证 | 条款=`POST /api/v1/internal/release/rollout/plan` | 参考行=38 | 证据: 待补
26. 状态=未验证 | 条款=`POST /api/v1/internal/release/rollout/decision` | 参考行=39 | 证据: 待补
27. 状态=未验证 | 条款=`POST /api/v1/internal/release/rollback/execute` | 参考行=40 | 证据: 待补
28. 状态=未验证 | 条款=`POST /api/v1/internal/ops/data-feedback/run` | 参考行=41 | 证据: 待补
29. 状态=未验证 | 条款=`POST /api/v1/internal/ops/strategy-tuning/apply` | 参考行=42 | 证据: 待补
30. 状态=未验证 | 条款=所有响应必须包含 `meta.trace_id`。 | 参考行=46 | 证据: 待补
31. 状态=未验证 | 条款=所有写接口必须携带 `Idempotency-Key`。 | 参考行=47 | 证据: 待补
32. 状态=未验证 | 条款=客户端不得传 `tenant_id`；租户从 JWT 注入。 | 参考行=48 | 证据: 待补
33. 状态=未验证 | 条款=校验顺序：HTTP 状态 -> `success` 字段 -> `error.code`/`data` 字段。 | 参考行=49 | 证据: 待补
34. 状态=未验证 | 条款=`success == true` | 参考行=133 | 证据: 待补
35. 状态=未验证 | 条款=`meta.trace_id` 非空 | 参考行=134 | 证据: 待补
36. 状态=未验证 | 条款=`data` 字段包含接口定义的最小集合 | 参考行=135 | 证据: 待补
37. 状态=未验证 | 条款=`success == false` | 参考行=139 | 证据: 待补
38. 状态=未验证 | 条款=`error.code/message/retryable/class` 全存在 | 参考行=140 | 证据: 待补
39. 状态=未验证 | 条款=`meta.trace_id` 非空 | 参考行=141 | 证据: 待补
40. 状态=未验证 | 条款=`queued` | 参考行=147 | 证据: 待补
41. 状态=未验证 | 条款=`running` | 参考行=148 | 证据: 待补
42. 状态=未验证 | 条款=`retrying` | 参考行=149 | 证据: 待补
43. 状态=未验证 | 条款=`succeeded` | 参考行=150 | 证据: 待补
44. 状态=未验证 | 条款=`failed` | 参考行=151 | 证据: 待补
45. 状态=未验证 | 条款=`needs_manual_decision` | 参考行=152 | 证据: 待补
46. 状态=未验证 | 条款=`dlq_pending` | 参考行=153 | 证据: 待补
47. 状态=未验证 | 条款=`dlq_recorded` | 参考行=154 | 证据: 待补
48. 状态=未验证 | 条款=`case_id` | 参考行=160 | 证据: 待补
49. 状态=未验证 | 条款=`request_id` | 参考行=161 | 证据: 待补
50. 状态=未验证 | 条款=`trace_id` | 参考行=162 | 证据: 待补
51. 状态=未验证 | 条款=`http_status` | 参考行=163 | 证据: 待补
52. 状态=未验证 | 条款=`assertion_result`（pass/fail） | 参考行=164 | 证据: 待补
53. 状态=未验证 | 条款=`captured_at` | 参考行=165 | 证据: 待补
54. 状态=未验证 | 条款=统一响应模型与错误对象：`CT-001/006/010/014/016/019/024/025`。 | 参考行=169 | 证据: 待补
55. 状态=未验证 | 条款=幂等策略：`CT-002/003/027/028/029`。 | 参考行=170 | 证据: 待补
56. 状态=未验证 | 条款=异步任务契约：`CT-001/005/007/009/011/013/018/021/023/048`。 | 参考行=171 | 证据: 待补
57. 状态=未验证 | 条款=`resume_token` 与 citation schema：`CT-013/014/015`。 | 参考行=172 | 证据: 待补
58. 状态=未验证 | 条款=B-2 状态机运维动作（cancel/DLQ）：`CT-011/012/017/018/019/020/022`。 | 参考行=173 | 证据: 待补
59. 状态=未验证 | 条款=多租户隔离：`CT-024/025/026/032`。 | 参考行=174 | 证据: 待补
60. 状态=未验证 | 条款=Gate E 灰度与回滚：`CT-064/065/066/067/068/069/070`。 | 参考行=175 | 证据: 待补
61. 状态=未验证 | 条款=Gate F 运行优化：`CT-071/072/073`。 | 参考行=176 | 证据: 待补
62. 状态=未验证 | 条款=将本样例映射为契约测试脚本（pytest/newman）。 | 参考行=180 | 证据: 待补
63. 状态=未验证 | 条款=每次 API 字段变更必须同步更新样例矩阵。 | 参考行=181 | 证据: 待补
64. 状态=未验证 | 条款=Gate C 前至少完成一次全量样例回放并归档结果。 | 参考行=182 | 证据: 待补

**文件：docs/design/2026-02-21-data-model-and-storage-spec.md**
文件级结论：部分实现 | 证据: app/repositories/*; app/db/rls.py
1. 状态=部分实现 | 条款=固化权威数据与索引数据边界。 | 参考行=9 | 证据: app/repositories/*; app/db/rls.py
2. 状态=部分实现 | 条款=固化多租户强隔离（字段、索引、RLS）。 | 参考行=10 | 证据: app/repositories/*; app/db/rls.py
3. 状态=部分实现 | 条款=固化工作流恢复、DLQ、审计、留存模型。 | 参考行=11 | 证据: app/repositories/*; app/db/rls.py
4. 状态=部分实现 | 条款=支持可追溯与可回滚运维。 | 参考行=12 | 证据: app/repositories/*; app/db/rls.py
5. 状态=部分实现 | 条款=`tenants(tenant_id, tenant_code, name, status, created_at)` | 参考行=44 | 证据: app/repositories/*; app/db/rls.py
6. 状态=部分实现 | 条款=`users(user_id, tenant_id, email, role, is_active, created_at)` | 参考行=45 | 证据: app/repositories/*; app/db/rls.py
7. 状态=部分实现 | 条款=`projects(project_id, tenant_id, project_code, name, ruleset_version, status, created_at, updated_at)` | 参考行=46 | 证据: app/repositories/*; app/db/rls.py
8. 状态=部分实现 | 条款=`suppliers(supplier_id, tenant_id, supplier_code, name, qualification_json, risk_flags_json)` | 参考行=47 | 证据: app/repositories/*; app/db/rls.py
9. 状态=部分实现 | 条款=`project_suppliers(tenant_id, project_id, supplier_id, join_status, created_at)` | 参考行=48 | 证据: app/repositories/*; app/db/rls.py
10. 状态=部分实现 | 条款=`rule_packs(rule_pack_version, tenant_id, name, status, payload, created_at, updated_at)` | 参考行=49 | 证据: app/repositories/*; app/db/rls.py
11. 状态=部分实现 | 条款=`documents(document_id, tenant_id, project_id, supplier_id, doc_type, filename, sha256, storage_uri, parse_status, created_at)` | 参考行=53 | 证据: app/repositories/*; app/db/rls.py
12. 状态=部分实现 | 条款=`document_parse_runs(run_id, tenant_id, document_id, parser, parser_version, manifest_uri, status, error_code, started_at, ended_at)` | 参考行=54 | 证据: app/repositories/*; app/db/rls.py
13. 状态=部分实现 | 条款=`document_chunks(chunk_id, tenant_id, project_id, document_id, supplier_id, chunk_index, content, chunk_type, section, heading_path_json, token_count, created_at)` | 参考行=55 | 证据: app/repositories/*; app/db/rls.py
14. 状态=部分实现 | 条款=`chunk_positions(position_id, tenant_id, chunk_id, page_no, x0, y0, x1, y1, text_start, text_end)` | 参考行=56 | 证据: app/repositories/*; app/db/rls.py
15. 状态=部分实现 | 条款=`evaluation_sessions(evaluation_id, tenant_id, project_id, supplier_id, status, total_score, confidence, risk_level, report_uri, created_by, created_at, updated_at)` | 参考行=60 | 证据: app/repositories/*; app/db/rls.py
16. 状态=部分实现 | 条款=`evaluation_items(item_id, tenant_id, evaluation_id, criteria_id, hard_pass, score, max_score, reason, confidence)` | 参考行=61 | 证据: app/repositories/*; app/db/rls.py
17. 状态=部分实现 | 条款=`evaluation_results(result_id, tenant_id, evaluation_id, score_json, summary, needs_human_review, approved_by, approved_at)` | 参考行=62 | 证据: app/repositories/*; app/db/rls.py
18. 状态=部分实现 | 条款=`citations(citation_id, tenant_id, evaluation_id, item_id, chunk_id, page_no, bbox_json, quote, created_at)` | 参考行=63 | 证据: app/repositories/*; app/db/rls.py
19. 状态=部分实现 | 条款=`jobs(job_id, tenant_id, job_type, resource_type, resource_id, status, retry_count, trace_id, idempotency_key, payload_json, error_code, created_at, updated_at)` | 参考行=67 | 证据: app/repositories/*; app/db/rls.py
20. 状态=部分实现 | 条款=`workflow_checkpoints(checkpoint_id, tenant_id, thread_id, evaluation_id, state_json, status, created_at, updated_at)` | 参考行=68 | 证据: app/repositories/*; app/db/rls.py
21. 状态=部分实现 | 条款=`dlq_items(dlq_id, tenant_id, job_id, error_class, error_code, payload_json, context_json, status, first_failed_at, created_at, updated_at)` | 参考行=69 | 证据: app/repositories/*; app/db/rls.py
22. 状态=部分实现 | 条款=`audit_logs(audit_id, tenant_id, actor_id, actor_role, action, resource_type, resource_id, request_id, trace_id, reason, ip, user_agent, payload_json, created_at)` | 参考行=73 | 证据: app/repositories/*; app/db/rls.py
23. 状态=部分实现 | 条款=`domain_events_outbox(event_id, tenant_id, event_type, aggregate_type, aggregate_id, payload_json, status, published_at, created_at)` | 参考行=74 | 证据: app/repositories/*; app/db/rls.py
24. 状态=部分实现 | 条款=`legal_hold_objects(hold_id, tenant_id, object_type, object_id, reason, imposed_by, imposed_at, released_by, released_at, status)` | 参考行=75 | 证据: app/repositories/*; app/db/rls.py
25. 状态=部分实现 | 条款=`documents.storage_uri`：原始文档对象存储 URI。 | 参考行=79 | 证据: app/repositories/*; app/db/rls.py
26. 状态=部分实现 | 条款=`document_parse_runs.manifest_uri`：解析产物 manifest 的对象存储 URI。 | 参考行=80 | 证据: app/repositories/*; app/db/rls.py
27. 状态=部分实现 | 条款=`evaluation_sessions.report_uri`：评估报告对象存储 URI。 | 参考行=81 | 证据: app/repositories/*; app/db/rls.py
28. 状态=部分实现 | 条款=`documents(tenant_id, project_id, supplier_id, created_at DESC)` | 参考行=89 | 证据: app/repositories/*; app/db/rls.py
29. 状态=部分实现 | 条款=`document_chunks(tenant_id, document_id, chunk_index)` | 参考行=90 | 证据: app/repositories/*; app/db/rls.py
30. 状态=部分实现 | 条款=`chunk_positions(tenant_id, chunk_id, page_no)` | 参考行=91 | 证据: app/repositories/*; app/db/rls.py
31. 状态=部分实现 | 条款=`evaluation_sessions(tenant_id, project_id, status, created_at DESC)` | 参考行=92 | 证据: app/repositories/*; app/db/rls.py
32. 状态=部分实现 | 条款=`jobs(tenant_id, status, created_at DESC)` | 参考行=93 | 证据: app/repositories/*; app/db/rls.py
33. 状态=部分实现 | 条款=`dlq_items(tenant_id, status, created_at DESC)` | 参考行=94 | 证据: app/repositories/*; app/db/rls.py
34. 状态=部分实现 | 条款=`workflow_checkpoints(tenant_id, thread_id, updated_at DESC)` | 参考行=95 | 证据: app/repositories/*; app/db/rls.py
35. 状态=部分实现 | 条款=`audit_logs(tenant_id, action, created_at DESC)` | 参考行=96 | 证据: app/repositories/*; app/db/rls.py
36. 状态=部分实现 | 条款=`projects(tenant_id, project_code)` | 参考行=100 | 证据: app/repositories/*; app/db/rls.py
37. 状态=部分实现 | 条款=`suppliers(tenant_id, supplier_code)` | 参考行=101 | 证据: app/repositories/*; app/db/rls.py
38. 状态=部分实现 | 条款=`project_suppliers(tenant_id, project_id, supplier_id)` | 参考行=102 | 证据: app/repositories/*; app/db/rls.py
39. 状态=部分实现 | 条款=`jobs(tenant_id, idempotency_key)`（可空，空值不参与） | 参考行=103 | 证据: app/repositories/*; app/db/rls.py
40. 状态=部分实现 | 条款=核心业务表全部启用 RLS。 | 参考行=191 | 证据: app/repositories/*; app/db/rls.py
41. 状态=部分实现 | 条款=连接会话必须先设置 `app.current_tenant`。 | 参考行=192 | 证据: app/repositories/*; app/db/rls.py
42. 状态=部分实现 | 条款=无 tenant 上下文时拒绝查询。 | 参考行=193 | 证据: app/repositories/*; app/db/rls.py
43. 状态=部分实现 | 条款=`tenant_id` | 参考行=206 | 证据: app/repositories/*; app/db/rls.py
44. 状态=部分实现 | 条款=`project_id` | 参考行=207 | 证据: app/repositories/*; app/db/rls.py
45. 状态=部分实现 | 条款=`document_id` | 参考行=208 | 证据: app/repositories/*; app/db/rls.py
46. 状态=部分实现 | 条款=`supplier_id` | 参考行=209 | 证据: app/repositories/*; app/db/rls.py
47. 状态=部分实现 | 条款=`chunk_id` | 参考行=210 | 证据: app/repositories/*; app/db/rls.py
48. 状态=部分实现 | 条款=`chunk_type` | 参考行=211 | 证据: app/repositories/*; app/db/rls.py
49. 状态=部分实现 | 条款=`page_span` | 参考行=212 | 证据: app/repositories/*; app/db/rls.py
50. 状态=部分实现 | 条款=`audit_logs` 超大表按月分区。 | 参考行=225 | 证据: app/repositories/*; app/db/rls.py
51. 状态=部分实现 | 条款=报告与原始证据进入 WORM 存储。 | 参考行=226 | 证据: app/repositories/*; app/db/rls.py
52. 状态=部分实现 | 条款=常规对象 180 天留存，可按租户策略调整。 | 参考行=227 | 证据: app/repositories/*; app/db/rls.py
53. 状态=部分实现 | 条款=legal hold 对象不参与自动清理。 | 参考行=228 | 证据: app/repositories/*; app/db/rls.py
54. 状态=部分实现 | 条款=每日增量 + 每周全量备份。 | 参考行=229 | 证据: app/repositories/*; app/db/rls.py
55. 状态=部分实现 | 条款=新字段优先向后兼容，避免破坏性变更。 | 参考行=233 | 证据: app/repositories/*; app/db/rls.py
56. 状态=部分实现 | 条款=迁移采用“双写+回填+切换”流程。 | 参考行=234 | 证据: app/repositories/*; app/db/rls.py
57. 状态=部分实现 | 条款=schema 变更必须附回滚 SQL。 | 参考行=235 | 证据: app/repositories/*; app/db/rls.py
58. 状态=部分实现 | 条款=准备阶段： | 参考行=239 | 证据: app/repositories/*; app/db/rls.py
59. 状态=部分实现 | 条款=基础域迁移： | 参考行=242 | 证据: app/repositories/*; app/db/rls.py
60. 状态=部分实现 | 条款=文档域迁移： | 参考行=244 | 证据: app/repositories/*; app/db/rls.py
61. 状态=部分实现 | 条款=评估域迁移： | 参考行=246 | 证据: app/repositories/*; app/db/rls.py
62. 状态=部分实现 | 条款=任务与治理迁移： | 参考行=248 | 证据: app/repositories/*; app/db/rls.py
63. 状态=部分实现 | 条款=索引与约束补全： | 参考行=250 | 证据: app/repositories/*; app/db/rls.py
64. 状态=部分实现 | 条款=RLS 启用与策略下发： | 参考行=252 | 证据: app/repositories/*; app/db/rls.py
65. 状态=部分实现 | 条款=回填与校验： | 参考行=254 | 证据: app/repositories/*; app/db/rls.py
66. 状态=部分实现 | 条款=发布切换： | 参考行=257 | 证据: app/repositories/*; app/db/rls.py
67. 状态=部分实现 | 条款=回滚预案： | 参考行=259 | 证据: app/repositories/*; app/db/rls.py
68. 状态=部分实现 | 条款=跨租户访问在 API 与 DB 层均被阻断。 | 参考行=265 | 证据: app/repositories/*; app/db/rls.py
69. 状态=部分实现 | 条款=关键查询索引命中率达到目标。 | 参考行=266 | 证据: app/repositories/*; app/db/rls.py
70. 状态=部分实现 | 条款=checkpoint 恢复可定位到最新状态。 | 参考行=267 | 证据: app/repositories/*; app/db/rls.py
71. 状态=部分实现 | 条款=审计与 legal hold 数据可完整追溯。 | 参考行=268 | 证据: app/repositories/*; app/db/rls.py
72. 状态=部分实现 | 条款=PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html | 参考行=272 | 证据: app/repositories/*; app/db/rls.py
73. 状态=部分实现 | 条款=历史融合提交：`beef3e9`, `7f05f7e` | 参考行=273 | 证据: app/repositories/*; app/db/rls.py

**文件：docs/design/2026-02-21-deployment-config.md**
文件级结论：部分实现 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
1. 状态=部分实现 | 条款=保障主链路生产可用。 | 参考行=9 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
2. 状态=部分实现 | 条款=支持异步任务弹性扩缩容。 | 参考行=10 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
3. 状态=部分实现 | 条款=支持全链路可观测与故障回滚。 | 参考行=11 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
4. 状态=部分实现 | 条款=支持租户隔离与证据留存。 | 参考行=12 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
5. 状态=部分实现 | 条款=`dev`：最小组件，本地联调。 | 参考行=51 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
6. 状态=部分实现 | 条款=`staging`：与 prod 同拓扑，用于预发回放。 | 参考行=52 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
7. 状态=部分实现 | 条款=`prod`：多副本 API/Worker，完整监控与告警。 | 参考行=53 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
8. 状态=部分实现 | 条款=`frontend` | 参考行=61 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
9. 状态=部分实现 | 条款=`api` | 参考行=62 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
10. 状态=部分实现 | 条款=`worker` | 参考行=63 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
11. 状态=部分实现 | 条款=`postgres` | 参考行=64 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
12. 状态=部分实现 | 条款=`redis` | 参考行=65 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
13. 状态=部分实现 | 条款=`chroma` | 参考行=66 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
14. 状态=部分实现 | 条款=`object-storage`（本地可用 MinIO 兼容接口） | 参考行=67 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
15. 状态=部分实现 | 条款=`GET /api/v1/health` 返回 200。 | 参考行=71 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
16. 状态=部分实现 | 条款=队列可入队并被 worker 消费。 | 参考行=72 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
17. 状态=部分实现 | 条款=文档上传后能拿到 `job_id` 并完成到 `indexed`。 | 参考行=73 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
18. 状态=部分实现 | 条款=与 `prod` 同拓扑（单副本可接受）。 | 参考行=77 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
19. 状态=部分实现 | 条款=启用完整观测与告警。 | 参考行=78 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
20. 状态=部分实现 | 条款=启用灰度发布与回滚剧本演练。 | 参考行=79 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
21. 状态=部分实现 | 条款=API 至少 2 副本，worker 至少 2 副本。 | 参考行=83 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
22. 状态=部分实现 | 条款=数据与对象存储开启备份。 | 参考行=84 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
23. 状态=部分实现 | 条款=关键指标告警与事故通知链路有效。 | 参考行=85 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
24. 状态=部分实现 | 条款=`API_WORKERS` | 参考行=91 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
25. 状态=部分实现 | 条款=`REQUEST_TIMEOUT_MS` | 参考行=92 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
26. 状态=部分实现 | 条款=`JWT_ISSUER/JWT_AUDIENCE` | 参考行=93 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
27. 状态=部分实现 | 条款=`IDEMPOTENCY_TTL_HOURS=24` | 参考行=94 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
28. 状态=部分实现 | 条款=`TRACE_ID_STRICT_REQUIRED=true`（staging/prod） | 参考行=95 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
29. 状态=部分实现 | 条款=`WORKER_CONCURRENCY` | 参考行=99 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
30. 状态=部分实现 | 条款=`JOB_MAX_RETRY=3` | 参考行=100 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
31. 状态=部分实现 | 条款=`JOB_BACKOFF_BASE_MS` | 参考行=101 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
32. 状态=部分实现 | 条款=`DLQ_ENABLED=true` | 参考行=102 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
33. 状态=部分实现 | 条款=`LIGHTRAG_WORKDIR` | 参考行=106 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
34. 状态=部分实现 | 条款=`RERANK_ENABLED` | 参考行=107 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
35. 状态=部分实现 | 条款=`RERANK_TIMEOUT_MS` | 参考行=108 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
36. 状态=部分实现 | 条款=`MODEL_ROUTER_PROFILE` | 参考行=109 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
37. 状态=部分实现 | 条款=`POSTGRES_DSN` | 参考行=113 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
38. 状态=部分实现 | 条款=`REDIS_DSN` | 参考行=114 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
39. 状态=部分实现 | 条款=`CHROMA_PERSIST_DIR` | 参考行=115 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
40. 状态=部分实现 | 条款=`OBJECT_STORAGE_BUCKET` | 参考行=116 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
41. 状态=部分实现 | 条款=`WORM_RETENTION_DAYS` | 参考行=117 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
42. 状态=部分实现 | 条款=`BEA_REQUIRE_TRUESTACK=true`（staging/prod） | 参考行=118 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
43. 状态=部分实现 | 条款=按 CPU/延迟双指标扩容。 | 参考行=124 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
44. 状态=部分实现 | 条款=目标：查询接口 P95 <= 1.5s。 | 参考行=125 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
45. 状态=部分实现 | 条款=按队列积压与处理时延扩容。 | 参考行=129 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
46. 状态=部分实现 | 条款=高峰期优先扩容解析队列与评估队列。 | 参考行=130 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
47. 状态=部分实现 | 条款=租户级速率限制。 | 参考行=134 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
48. 状态=部分实现 | 条款=高风险写接口单独限流。 | 参考行=135 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
49. 状态=部分实现 | 条款=API QPS、错误率、P95。 | 参考行=141 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
50. 状态=部分实现 | 条款=队列深度、重试率、DLQ 新增率。 | 参考行=142 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
51. 状态=部分实现 | 条款=解析/检索/评估耗时分布。 | 参考行=143 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
52. 状态=部分实现 | 条款=质量指标（幻觉率、citation 回跳率）。 | 参考行=144 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
53. 状态=部分实现 | 条款=`trace_id` | 参考行=148 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
54. 状态=部分实现 | 条款=`request_id` | 参考行=149 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
55. 状态=部分实现 | 条款=`job_id` | 参考行=150 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
56. 状态=部分实现 | 条款=`tenant_id` | 参考行=151 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
57. 状态=部分实现 | 条款=`node_name` | 参考行=152 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
58. 状态=部分实现 | 条款=`error_code` | 参考行=153 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
59. 状态=部分实现 | 条款=P0：越权风险、主链路不可用。 | 参考行=157 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
60. 状态=部分实现 | 条款=P1：DLQ 激增、幻觉率超阈值。 | 参考行=158 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
61. 状态=部分实现 | 条款=P2：性能退化与成本异常。 | 参考行=159 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
62. 状态=部分实现 | 条款=密钥通过安全配置中心注入。 | 参考行=163 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
63. 状态=部分实现 | 条款=生产配置不可硬编码在仓库。 | 参考行=164 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
64. 状态=部分实现 | 条款=发布前执行配置差异检查。 | 参考行=165 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
65. 状态=部分实现 | 条款=审计日志与报告归档进入受控存储。 | 参考行=166 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
66. 状态=部分实现 | 条款=`staging/prod` 禁止静默回退到 `memory/sqlite`（通过 `BEA_REQUIRE_TRUESTACK=true` 强制约束）。 | 参考行=167 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
67. 状态=部分实现 | 条款=`staging/prod` 强制要求请求显式携带 `x-trace-id`（通过 `TRACE_ID_STRICT_REQUIRED=true`）。 | 参考行=168 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
68. 状态=部分实现 | 条款=触发条件：任一门禁连续超阈值。 | 参考行=184 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
69. 状态=部分实现 | 条款=回滚级别： | 参考行=185 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
70. 状态=部分实现 | 条款=回滚后强制执行回放验证。 | 参考行=189 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
71. 状态=部分实现 | 条款=RPO <= 15min，RTO <= 60min。 | 参考行=236 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
72. 状态=部分实现 | 条款=每日增量、每周全量备份。 | 参考行=237 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
73. 状态=部分实现 | 条款=定期恢复演练（至少每月一次）。 | 参考行=238 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
74. 状态=部分实现 | 条款=staging 与 prod 配置差异可追踪。 | 参考行=242 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
75. 状态=部分实现 | 条款=可观测指标完整，告警可触发。 | 参考行=243 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
76. 状态=部分实现 | 条款=灰度与回滚流程可实测执行。 | 参考行=244 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
77. 状态=部分实现 | 条款=FastAPI deployment docs: https://fastapi.tiangolo.com/deployment/ | 参考行=248 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md
78. 状态=部分实现 | 条款=历史融合提交：`beef3e9`, `7f05f7e` | 参考行=249 | 证据: docs/ops/2026-02-23-observability-deploy-evidence.md

**文件：docs/design/2026-02-21-error-handling-and-dlq-spec.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=API/Worker/Workflow 使用同一错误语义。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=明确可重试与不可重试边界。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=固化 `failed` 与 `DLQ` 的先后关系。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=支持降级、回滚、审计闭环。 | 参考行=12 | 证据: 待补
5. 状态=未验证 | 条款=`code` | 参考行=18 | 证据: 待补
6. 状态=未验证 | 条款=`message` | 参考行=19 | 证据: 待补
7. 状态=未验证 | 条款=`class` | 参考行=20 | 证据: 待补
8. 状态=未验证 | 条款=`http_status` | 参考行=21 | 证据: 待补
9. 状态=未验证 | 条款=`retryable` | 参考行=22 | 证据: 待补
10. 状态=未验证 | 条款=`trace_id` | 参考行=23 | 证据: 待补
11. 状态=未验证 | 条款=`job_id` | 参考行=24 | 证据: 待补
12. 状态=未验证 | 条款=`details` | 参考行=25 | 证据: 待补
13. 状态=未验证 | 条款=`occurred_at` | 参考行=26 | 证据: 待补
14. 状态=未验证 | 条款=`validation` | 参考行=30 | 证据: 待补
15. 状态=未验证 | 条款=`business_rule` | 参考行=31 | 证据: 待补
16. 状态=未验证 | 条款=`transient` | 参考行=32 | 证据: 待补
17. 状态=未验证 | 条款=`permanent` | 参考行=33 | 证据: 待补
18. 状态=未验证 | 条款=`security_sensitive` | 参考行=34 | 证据: 待补
19. 状态=未验证 | 条款=`AUTH_UNAUTHORIZED` | 参考行=40 | 证据: 待补
20. 状态=未验证 | 条款=`AUTH_FORBIDDEN` | 参考行=41 | 证据: 待补
21. 状态=未验证 | 条款=`TENANT_SCOPE_VIOLATION` | 参考行=42 | 证据: 待补
22. 状态=未验证 | 条款=`REQ_VALIDATION_FAILED` | 参考行=46 | 证据: 待补
23. 状态=未验证 | 条款=`IDEMPOTENCY_CONFLICT` | 参考行=47 | 证据: 待补
24. 状态=未验证 | 条款=`IDEMPOTENCY_MISSING` | 参考行=48 | 证据: 待补
25. 状态=未验证 | 条款=`DOC_PARSE_OUTPUT_NOT_FOUND` | 参考行=52 | 证据: 待补
26. 状态=未验证 | 条款=`DOC_PARSE_SCHEMA_INVALID` | 参考行=53 | 证据: 待补
27. 状态=未验证 | 条款=`MINERU_BBOX_FORMAT_INVALID` | 参考行=54 | 证据: 待补
28. 状态=未验证 | 条款=`TEXT_ENCODING_UNSUPPORTED` | 参考行=55 | 证据: 待补
29. 状态=未验证 | 条款=`PARSER_FALLBACK_EXHAUSTED` | 参考行=56 | 证据: 待补
30. 状态=未验证 | 条款=`RAG_RETRIEVAL_TIMEOUT` | 参考行=57 | 证据: 待补
31. 状态=未验证 | 条款=`RAG_UPSTREAM_UNAVAILABLE` | 参考行=58 | 证据: 待补
32. 状态=未验证 | 条款=`WF_STATE_TRANSITION_INVALID` | 参考行=62 | 证据: 待补
33. 状态=未验证 | 条款=`WF_INTERRUPT_RESUME_INVALID` | 参考行=63 | 证据: 待补
34. 状态=未验证 | 条款=`WF_CHECKPOINT_NOT_FOUND` | 参考行=64 | 证据: 待补
35. 状态=未验证 | 条款=`DLQ_ITEM_NOT_FOUND` | 参考行=68 | 证据: 待补
36. 状态=未验证 | 条款=`DLQ_REQUEUE_CONFLICT` | 参考行=69 | 证据: 待补
37. 状态=未验证 | 条款=`APPROVAL_REQUIRED` | 参考行=70 | 证据: 待补
38. 状态=未验证 | 条款=`PROJECT_NOT_FOUND` | 参考行=74 | 证据: 待补
39. 状态=未验证 | 条款=`SUPPLIER_NOT_FOUND` | 参考行=75 | 证据: 待补
40. 状态=未验证 | 条款=`RULE_PACK_NOT_FOUND` | 参考行=76 | 证据: 待补
41. 状态=未验证 | 条款=`LEGAL_HOLD_ACTIVE` | 参考行=80 | 证据: 待补
42. 状态=未验证 | 条款=`RETENTION_ACTIVE` | 参考行=81 | 证据: 待补
43. 状态=未验证 | 条款=`DOC_STORAGE_URI_MISSING` | 参考行=85 | 证据: 待补
44. 状态=未验证 | 条款=`DOC_STORAGE_MISSING` | 参考行=86 | 证据: 待补
45. 状态=未验证 | 条款=生产环境不返回堆栈。 | 参考行=90 | 证据: 待补
46. 状态=未验证 | 条款=必须带 `trace_id`。 | 参考行=91 | 证据: 待补
47. 状态=未验证 | 条款=`retryable=true` 时返回 `retry_after_seconds`（可选）。 | 参考行=92 | 证据: 待补
48. 状态=未验证 | 条款=4xx 不自动重试，5xx 由客户端按策略重试。 | 参考行=93 | 证据: 待补
49. 状态=未验证 | 条款=最大重试 3 次。 | 参考行=99 | 证据: 待补
50. 状态=未验证 | 条款=指数退避 + 抖动。 | 参考行=100 | 证据: 待补
51. 状态=未验证 | 条款=默认：`transient` 才可重试。 | 参考行=101 | 证据: 待补
52. 状态=未验证 | 条款=连续失败阈值：5（60 秒窗口）。 | 参考行=105 | 证据: 待补
53. 状态=未验证 | 条款=Open 状态维持：30 秒。 | 参考行=106 | 证据: 待补
54. 状态=未验证 | 条款=Half-open 探测通过后恢复。 | 参考行=107 | 证据: 待补
55. 状态=未验证 | 条款=rerank 失败降级为原检索排序。 | 参考行=111 | 证据: 待补
56. 状态=未验证 | 条款=非关键外部服务失败时切换为只读/低风险模式。 | 参考行=112 | 证据: 待补
57. 状态=未验证 | 条款=降级动作必须写审计事件。 | 参考行=113 | 证据: 待补
58. 状态=未验证 | 条款=先写 `dlq_items`。 | 参考行=129 | 证据: 待补
59. 状态=未验证 | 条款=再把 `jobs.status` 改为 `failed`。 | 参考行=130 | 证据: 待补
60. 状态=未验证 | 条款=任一步失败都不能跳过重试/补偿。 | 参考行=131 | 证据: 待补
61. 状态=未验证 | 条款=`dlq_id` | 参考行=135 | 证据: 待补
62. 状态=未验证 | 条款=`tenant_id` | 参考行=136 | 证据: 待补
63. 状态=未验证 | 条款=`job_id` | 参考行=137 | 证据: 待补
64. 状态=未验证 | 条款=`error_class` | 参考行=138 | 证据: 待补
65. 状态=未验证 | 条款=`error_code` | 参考行=139 | 证据: 待补
66. 状态=未验证 | 条款=`payload_snapshot` | 参考行=140 | 证据: 待补
67. 状态=未验证 | 条款=`context_snapshot` | 参考行=141 | 证据: 待补
68. 状态=未验证 | 条款=`status`（`open/requeued/discarded`） | 参考行=142 | 证据: 待补
69. 状态=未验证 | 条款=`created_at` | 参考行=143 | 证据: 待补
70. 状态=未验证 | 条款=条件：问题可修复、依赖恢复、幂等安全。 | 参考行=149 | 证据: 待补
71. 状态=未验证 | 条款=动作：生成新 job，关联原 dlq_id。 | 参考行=150 | 证据: 待补
72. 状态=未验证 | 条款=审计：记录 requeue 原因与操作者。 | 参考行=151 | 证据: 待补
73. 状态=未验证 | 条款=条件：确认无需重放或已人工替代处理。 | 参考行=155 | 证据: 待补
74. 状态=未验证 | 条款=约束：双人复核 + 必填 reason。 | 参考行=156 | 证据: 待补
75. 状态=未验证 | 条款=审计：记录 `reviewer_id/reviewer_id_2/approval_reviewers`。 | 参考行=157 | 证据: 待补
76. 状态=未验证 | 条款=`security_sensitive` 错误即时告警。 | 参考行=161 | 证据: 待补
77. 状态=未验证 | 条款=同类错误 5 分钟内超阈值触发事故流程。 | 参考行=162 | 证据: 待补
78. 状态=未验证 | 条款=DLQ 日增量超阈值触发 P1 排查。 | 参考行=163 | 证据: 待补
79. 状态=未验证 | 条款=P0/P1 事故必须包含错误码分布图。 | 参考行=167 | 证据: 待补
80. 状态=未验证 | 条款=runbook 止损动作优先关闭高风险写路径。 | 参考行=168 | 证据: 待补
81. 状态=未验证 | 条款=事故后必须回补测试用例。 | 参考行=169 | 证据: 待补
82. 状态=未验证 | 条款=全链路错误对象字段完整。 | 参考行=173 | 证据: 待补
83. 状态=未验证 | 条款=retry 与 DLQ 时序严格符合规范。 | 参考行=174 | 证据: 待补
84. 状态=未验证 | 条款=`discard` 无审批不可执行。 | 参考行=175 | 证据: 待补
85. 状态=未验证 | 条款=告警与审计联动可验证。 | 参考行=176 | 证据: 待补
86. 状态=未验证 | 条款=FastAPI exception handling: https://fastapi.tiangolo.com/ | 参考行=180 | 证据: 待补
87. 状态=未验证 | 条款=历史融合提交：`beef3e9`, `53e3d92` | 参考行=181 | 证据: 待补

**文件：docs/design/2026-02-21-frontend-interaction-spec.md**
文件级结论：部分实现 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
1. 状态=部分实现 | 条款=用户可沿主链路完成 `上传 -> 评估 -> 复核 -> 报告`。 | 参考行=9 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
2. 状态=部分实现 | 条款=长任务状态全程可见，可追溯到 `job_id/trace_id`。 | 参考行=10 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
3. 状态=部分实现 | 条款=每个评分结论可回跳到原文页内高亮位置。 | 参考行=11 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
4. 状态=部分实现 | 条款=权限边界与租户边界在 UI 层显式可感知。 | 参考行=12 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
5. 状态=部分实现 | 条款=批量上传与断点续传提示。 | 参考行=52 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
6. 状态=部分实现 | 条款=上传后立即展示 `job_id` 与状态入口。 | 参考行=53 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
7. 状态=部分实现 | 条款=解析状态实时刷新（polling 或 SSE）。 | 参考行=54 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
8. 状态=部分实现 | 条款=失败项可查看错误码与 trace。 | 参考行=55 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
9. 状态=部分实现 | 条款=客户端自行判断“成功”；必须以 `/jobs/{job_id}` 为准。 | 参考行=59 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
10. 状态=部分实现 | 条款=未完成 `indexed` 前禁止发起正式评估。 | 参考行=60 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
11. 状态=部分实现 | 条款=`criteria_id`（若存在 `criteria_name`，优先展示 `criteria_name`） | 参考行=80 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
12. 状态=部分实现 | 条款=`requirement_text`（可选，来自规则包或解析提取） | 参考行=81 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
13. 状态=部分实现 | 条款=`response_text`（可选，来自解析提取） | 参考行=82 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
14. 状态=部分实现 | 条款=`hard_pass` | 参考行=83 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
15. 状态=部分实现 | 条款=`score/max_score` | 参考行=84 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
16. 状态=部分实现 | 条款=`reason` | 参考行=85 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
17. 状态=部分实现 | 条款=`confidence` | 参考行=86 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
18. 状态=部分实现 | 条款=`citations_count`（由 `citations.length` 计算） | 参考行=87 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
19. 状态=部分实现 | 条款=展示触发原因（低置信、低覆盖、偏差过高、红线冲突）。 | 参考行=91 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
20. 状态=部分实现 | 条款=展示建议动作：`approve/reject/edit_scores`。 | 参考行=92 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
21. 状态=部分实现 | 条款=提交时必须包含 `resume_token + comment`。 | 参考行=93 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
22. 状态=部分实现 | 条款=提交结果展示新的 `job_id`。 | 参考行=94 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
23. 状态=部分实现 | 条款=筛选：`status/error_code/job_type/tenant/project`。 | 参考行=98 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
24. 状态=部分实现 | 条款=操作：`requeue/discard`。 | 参考行=99 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
25. 状态=部分实现 | 条款=discard 必须显示双人复核状态与原因。 | 参考行=100 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
26. 状态=部分实现 | 条款=输入 bbox 统一 `[x0,y0,x1,y1]`。 | 参考行=130 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
27. 状态=部分实现 | 条款=由前端根据当前缩放比转换坐标。 | 参考行=131 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
28. 状态=部分实现 | 条款=bbox 缺失时回退到页内文本定位。 | 参考行=132 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
29. 状态=部分实现 | 条款=`auth_state` | 参考行=138 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
30. 状态=部分实现 | 条款=`project_state` | 参考行=139 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
31. 状态=部分实现 | 条款=`job_state` | 参考行=140 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
32. 状态=部分实现 | 条款=`evaluation_state` | 参考行=141 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
33. 状态=部分实现 | 条款=`citation_state` | 参考行=142 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
34. 状态=部分实现 | 条款=SSE 通道断开后自动切 polling。 | 参考行=148 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
35. 状态=部分实现 | 条款=polling 默认 3 秒，失败后指数退避到 15 秒。 | 参考行=149 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
36. 状态=部分实现 | 条款=任务结束后停止轮询。 | 参考行=150 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
37. 状态=部分实现 | 条款=不在 `localStorage/sessionStorage` 保存高敏 token。 | 参考行=154 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
38. 状态=部分实现 | 条款=refresh token 仅 HttpOnly Cookie。 | 参考行=155 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
39. 状态=部分实现 | 条款=每个请求附带 CSRF token（对需要的端点）。 | 参考行=156 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
40. 状态=部分实现 | 条款=403/401 自动触发重认证流程。 | 参考行=157 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
41. 状态=部分实现 | 条款=每个长任务显示状态、耗时、重试次数。 | 参考行=161 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
42. 状态=部分实现 | 条款=错误提示包含 `error_code` 与建议动作。 | 参考行=162 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
43. 状态=部分实现 | 条款=关键操作（复核、discard）使用二次确认弹窗。 | 参考行=163 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
44. 状态=部分实现 | 条款=导出报告支持“可追溯证据摘要”附录。 | 参考行=164 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
45. 状态=部分实现 | 条款=首屏可交互时间 `<= 2.5s`（常规网络）。 | 参考行=168 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
46. 状态=部分实现 | 条款=评估页切换响应 `<= 1.0s`（缓存命中）。 | 参考行=169 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
47. 状态=部分实现 | 条款=citation 点击到高亮出现 `<= 1.5s`。 | 参考行=170 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
48. 状态=部分实现 | 条款=上传成功并进入 indexed。 | 参考行=174 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
49. 状态=部分实现 | 条款=发起评估并生成报告。 | 参考行=175 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
50. 状态=部分实现 | 条款=触发 HITL 并恢复。 | 参考行=176 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
51. 状态=部分实现 | 条款=citation 回跳与高亮。 | 参考行=177 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
52. 状态=部分实现 | 条款=DLQ requeue 与状态闭环。 | 参考行=178 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
53. 状态=部分实现 | 条款=跨角色权限限制验证。 | 参考行=179 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
54. 状态=部分实现 | 条款=主链路页面全部可用。 | 参考行=183 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
55. 状态=部分实现 | 条款=证据回跳成功率 >= 98%。 | 参考行=184 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
56. 状态=部分实现 | 条款=高风险操作前端交互符合审批约束。 | 参考行=185 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
57. 状态=部分实现 | 条款=无敏感信息泄露到浏览器持久存储。 | 参考行=186 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
58. 状态=部分实现 | 条款=ProposalLLM（点对点结构借鉴） | 参考行=190 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
59. 状态=部分实现 | 条款=kotaemon（citation 回跳交互借鉴） | 参考行=191 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
60. 状态=部分实现 | 条款=历史融合提交：`53e3d92`, `beef3e9` | 参考行=192 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
61. 状态=部分实现 | 条款=新增前端最小工程：`frontend/`（Vue3 + Vite + vue-router + pinia）。 | 参考行=196 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
62. 状态=部分实现 | 条款=已落地路由骨架：`/dashboard /documents /evaluations /jobs /dlq`，其余路由预留占位页。 | 参考行=197 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
63. 状态=部分实现 | 条款=已接通核心 API： | 参考行=198 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
64. 状态=部分实现 | 条款=前端启动说明见：`frontend/README.md`。 | 参考行=207 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
65. 状态=部分实现 | 条款=新增评估报告页与证据面板，支持 citation 回跳与 bbox 高亮。 | 参考行=208 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue
66. 状态=部分实现 | 条款=引入角色门控 UI（上传/评估/复核/DLQ 操作）。 | 参考行=209 | 证据: docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; frontend/src/views/EvaluationReportView.vue

**文件：docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=冻结模块职责边界，避免后续实现阶段跨模块写入。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=固化副作用唯一归属，防止重复提交与状态错乱。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=给 Gate B-C 的实现与测试提供可执行边界表。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=检索与评分模块只产出“计算结果”，不直接提交持久化副作用。 | 参考行=27 | 证据: 待补
5. 状态=未验证 | 条款=终态提交必须经 `workflow` 的受控节点统一落库。 | 参考行=28 | 证据: 待补
6. 状态=未验证 | 条款=任一模块发现租户上下文缺失，必须立即失败并上报错误码。 | 参考行=29 | 证据: 待补
7. 状态=未验证 | 条款=`failed` 必须晚于 `dlq_recorded`。 | 参考行=71 | 证据: 待补
8. 状态=未验证 | 条款=`discard`、终审发布、legal hold 解除必须走审批流并写审计。 | 参考行=72 | 证据: 待补
9. 状态=未验证 | 条款=`interrupt` 负载必须 JSON 可序列化，恢复必须校验最新 `resume_token`。 | 参考行=73 | 证据: 待补
10. 状态=未验证 | 条款=模块内可同步调用；模块间优先 outbox 事件。 | 参考行=77 | 证据: 待补
11. 状态=未验证 | 条款=事件最小字段：`event_id/tenant_id/aggregate_type/aggregate_id/trace_id/occurred_at`。 | 参考行=78 | 证据: 待补
12. 状态=未验证 | 条款=禁止直接依赖下游内部表结构；跨模块只依赖契约对象。 | 参考行=79 | 证据: 待补
13. 状态=未验证 | 条款=每个副作用动作都可定位到唯一模块和唯一节点。 | 参考行=83 | 证据: 待补
14. 状态=未验证 | 条款=不存在“两个模块都可提交同一副作用”的定义。 | 参考行=84 | 证据: 待补
15. 状态=未验证 | 条款=实施任务若违反本表边界，应在评审阶段阻断进入 Gate B-C。 | 参考行=85 | 证据: 待补
16. 状态=未验证 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=89 | 证据: 待补
17. 状态=未验证 | 条款=`docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 参考行=90 | 证据: 待补
18. 状态=未验证 | 条款=`docs/design/2026-02-21-data-model-and-storage-spec.md` | 参考行=91 | 证据: 待补
19. 状态=未验证 | 条款=`docs/design/2026-02-21-agent-tool-governance.md` | 参考行=92 | 证据: 待补
20. 状态=未验证 | 条款=`docs/design/2026-02-21-security-design.md` | 参考行=93 | 证据: 待补

**文件：docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=冻结 Gate A 的核心术语：状态、错误码、角色、引用对象。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=消除同义混用，给出跨文档统一命名规则。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=为 Gate B 契约实现提供唯一字段基线。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=`tenant_id` | 参考行=19 | 证据: 待补
5. 状态=未验证 | 条款=`project_id` | 参考行=20 | 证据: 待补
6. 状态=未验证 | 条款=`supplier_id` | 参考行=21 | 证据: 待补
7. 状态=未验证 | 条款=`document_id` | 参考行=22 | 证据: 待补
8. 状态=未验证 | 条款=`evaluation_id` | 参考行=23 | 证据: 待补
9. 状态=未验证 | 条款=`job_id` | 参考行=24 | 证据: 待补
10. 状态=未验证 | 条款=`trace_id` | 参考行=25 | 证据: 待补
11. 状态=未验证 | 条款=`thread_id` | 参考行=26 | 证据: 待补
12. 状态=未验证 | 条款=`resume_token` | 参考行=27 | 证据: 待补
13. 状态=未验证 | 条款=`confidence` | 参考行=31 | 证据: 待补
14. 状态=未验证 | 条款=`citation_coverage` | 参考行=32 | 证据: 待补
15. 状态=未验证 | 条款=`needs_manual_decision`（状态） | 参考行=33 | 证据: 待补
16. 状态=未验证 | 条款=`needs_human_review`（布尔字段，仅用于结果对象） | 参考行=34 | 证据: 待补
17. 状态=未验证 | 条款=`queued` | 参考行=49 | 证据: 待补
18. 状态=未验证 | 条款=`running` | 参考行=50 | 证据: 待补
19. 状态=未验证 | 条款=`retrying` | 参考行=51 | 证据: 待补
20. 状态=未验证 | 条款=`succeeded` | 参考行=52 | 证据: 待补
21. 状态=未验证 | 条款=`dlq_pending` | 参考行=53 | 证据: 待补
22. 状态=未验证 | 条款=`dlq_recorded` | 参考行=54 | 证据: 待补
23. 状态=未验证 | 条款=`failed` | 参考行=55 | 证据: 待补
24. 状态=未验证 | 条款=`failed` 只能在 `dlq_recorded` 之后出现。 | 参考行=59 | 证据: 待补
25. 状态=未验证 | 条款=`needs_manual_decision` 不是 `jobs.status` 值。 | 参考行=60 | 证据: 待补
26. 状态=未验证 | 条款=`upload_received` | 参考行=71 | 证据: 待补
27. 状态=未验证 | 条款=`parse_queued` | 参考行=72 | 证据: 待补
28. 状态=未验证 | 条款=`parsing` | 参考行=73 | 证据: 待补
29. 状态=未验证 | 条款=`parsed` | 参考行=74 | 证据: 待补
30. 状态=未验证 | 条款=`indexing` | 参考行=75 | 证据: 待补
31. 状态=未验证 | 条款=`indexed` | 参考行=76 | 证据: 待补
32. 状态=未验证 | 条款=`evaluating` | 参考行=77 | 证据: 待补
33. 状态=未验证 | 条款=`needs_manual_decision` | 参考行=78 | 证据: 待补
34. 状态=未验证 | 条款=`approved` | 参考行=79 | 证据: 待补
35. 状态=未验证 | 条款=`report_generated` | 参考行=80 | 证据: 待补
36. 状态=未验证 | 条款=`archived` | 参考行=81 | 证据: 待补
37. 状态=未验证 | 条款=`needs_manual_decision` 仅由质量门触发。 | 参考行=85 | 证据: 待补
38. 状态=未验证 | 条款=`resume` 成功后恢复到 `finalize_report` 路径，不回跳任意节点。 | 参考行=86 | 证据: 待补
39. 状态=未验证 | 条款=`open` | 参考行=90 | 证据: 待补
40. 状态=未验证 | 条款=`requeued` | 参考行=91 | 证据: 待补
41. 状态=未验证 | 条款=`discarded` | 参考行=92 | 证据: 待补
42. 状态=未验证 | 条款=`AUTH_UNAUTHORIZED` | 参考行=100 | 证据: 待补
43. 状态=未验证 | 条款=`AUTH_FORBIDDEN` | 参考行=101 | 证据: 待补
44. 状态=未验证 | 条款=`TENANT_SCOPE_VIOLATION` | 参考行=102 | 证据: 待补
45. 状态=未验证 | 条款=`REQ_VALIDATION_FAILED` | 参考行=106 | 证据: 待补
46. 状态=未验证 | 条款=`IDEMPOTENCY_CONFLICT` | 参考行=107 | 证据: 待补
47. 状态=未验证 | 条款=`IDEMPOTENCY_MISSING` | 参考行=108 | 证据: 待补
48. 状态=未验证 | 条款=`DOC_PARSE_OUTPUT_NOT_FOUND` | 参考行=112 | 证据: 待补
49. 状态=未验证 | 条款=`DOC_PARSE_SCHEMA_INVALID` | 参考行=113 | 证据: 待补
50. 状态=未验证 | 条款=`MINERU_BBOX_FORMAT_INVALID` | 参考行=114 | 证据: 待补
51. 状态=未验证 | 条款=`TEXT_ENCODING_UNSUPPORTED` | 参考行=115 | 证据: 待补
52. 状态=未验证 | 条款=`PARSER_FALLBACK_EXHAUSTED` | 参考行=116 | 证据: 待补
53. 状态=未验证 | 条款=`RAG_RETRIEVAL_TIMEOUT` | 参考行=117 | 证据: 待补
54. 状态=未验证 | 条款=`RAG_UPSTREAM_UNAVAILABLE` | 参考行=118 | 证据: 待补
55. 状态=未验证 | 条款=`WF_STATE_TRANSITION_INVALID` | 参考行=122 | 证据: 待补
56. 状态=未验证 | 条款=`WF_INTERRUPT_RESUME_INVALID` | 参考行=123 | 证据: 待补
57. 状态=未验证 | 条款=`WF_CHECKPOINT_NOT_FOUND` | 参考行=124 | 证据: 待补
58. 状态=未验证 | 条款=`DLQ_ITEM_NOT_FOUND` | 参考行=128 | 证据: 待补
59. 状态=未验证 | 条款=`DLQ_REQUEUE_CONFLICT` | 参考行=129 | 证据: 待补
60. 状态=未验证 | 条款=`APPROVAL_REQUIRED` | 参考行=130 | 证据: 待补
61. 状态=未验证 | 条款=`PROJECT_NOT_FOUND` | 参考行=134 | 证据: 待补
62. 状态=未验证 | 条款=`SUPPLIER_NOT_FOUND` | 参考行=135 | 证据: 待补
63. 状态=未验证 | 条款=`RULE_PACK_NOT_FOUND` | 参考行=136 | 证据: 待补
64. 状态=未验证 | 条款=错误码命名统一使用 `UPPER_SNAKE_CASE`。 | 参考行=140 | 证据: 待补
65. 状态=未验证 | 条款=新错误码必须先更新 `docs/design/2026-02-21-error-handling-and-dlq-spec.md` 再更新调用文档。 | 参考行=141 | 证据: 待补
66. 状态=未验证 | 条款=高风险动作（终审发布、DLQ discard、legal hold 解除、外部正式提交）必须双人复核。 | 参考行=156 | 证据: 待补
67. 状态=未验证 | 条款=操作人与复核人必须不同。 | 参考行=157 | 证据: 待补
68. 状态=未验证 | 条款=存储层 `page_no` 对外转换为 `page`。 | 参考行=185 | 证据: 待补
69. 状态=未验证 | 条款=`bbox` 统一 `[x0,y0,x1,y1]`，禁止返回 `xywh`。 | 参考行=186 | 证据: 待补
70. 状态=未验证 | 条款=至少返回一条可回跳位置；多位置时提供 `primary_position`。 | 参考行=187 | 证据: 待补
71. 状态=未验证 | 条款=状态、错误码、角色、引用对象四类术语均有唯一定义。 | 参考行=199 | 证据: 待补
72. 状态=未验证 | 条款=文档中不存在同一语义的多种 canonical 命名。 | 参考行=200 | 证据: 待补
73. 状态=未验证 | 条款=所有新增术语先更新本字典，再扩散到专项文档。 | 参考行=201 | 证据: 待补
74. 状态=未验证 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=205 | 证据: 待补
75. 状态=未验证 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=206 | 证据: 待补
76. 状态=未验证 | 条款=`docs/design/2026-02-21-error-handling-and-dlq-spec.md` | 参考行=207 | 证据: 待补
77. 状态=未验证 | 条款=`docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 参考行=208 | 证据: 待补
78. 状态=未验证 | 条款=`docs/design/2026-02-21-security-design.md` | 参考行=209 | 证据: 待补

**文件：docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=将 Gate B（B-1~B-4）验收证据集中到单文档。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=区分“文档冻结完成”和“运行验证完成”。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=为进入 Gate C 提供明确前置检查项。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=OpenAPI 与契约样例同步一致。 | 参考行=52 | 证据: 待补
5. 状态=未验证 | 条款=状态机与错误码字典一致（含 `dlq_pending/dlq_recorded/failed` 时序）。 | 参考行=53 | 证据: 待补
6. 状态=未验证 | 条款=B-3/B-4 的运行验证任务已进入开发待办并分配执行责任。 | 参考行=54 | 证据: 待补
7. 状态=未验证 | 条款=Gate B 的“文档契约与骨架冻结”已具备入 Gate C 条件。 | 参考行=58 | 证据: 待补
8. 状态=未验证 | 条款=Gate B 的“运行验证”需在代码仓库完成后补齐证据。 | 参考行=59 | 证据: 待补
9. 状态=未验证 | 条款=运行命令：`pytest -v` | 参考行=65 | 证据: 待补
10. 状态=未验证 | 条款=测试结果：`76 passed` | 参考行=66 | 证据: 待补
11. 状态=未验证 | 条款=覆盖范围： | 参考行=67 | 证据: 待补
12. 状态=未验证 | 条款=证据测试文件： | 参考行=84 | 证据: 待补
13. 状态=未验证 | 条款=B-1 运行验证：已在本分支完成最小闭环验证（含 retrieval/report 与 HITL resume 契约）。 | 参考行=107 | 证据: 待补
14. 状态=未验证 | 条款=B-2 运行验证：已在本分支完成核心状态查询、状态机和取消语义验证。 | 参考行=108 | 证据: 待补
15. 状态=未验证 | 条款=B-4 运行验证：已完成 parse 受理、文档分块读取、检索模式选择/过滤/降级和基础 DLQ 运维契约验证（内存实现）。 | 参考行=109 | 证据: 待补
16. 状态=未验证 | 条款=B-3 运行验证：已完成接口层跨租户阻断验证；真实存储层 RLS 验证待后续接入 DB 补齐。 | 参考行=110 | 证据: 待补

**文件：docs/design/2026-02-21-implementation-plan.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=不按周排期，按 Gate + 证据推进。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=每个任务必须定义：输入、产出、验收、失败回退。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=先收敛契约，再推进实现。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=可并行任务交给 Codex/Claude Code 执行，最后统一回归。 | 参考行=12 | 证据: 待补
5. 状态=未验证 | 条款=`T1` API 与任务系统 | 参考行=27 | 证据: 待补
6. 状态=未验证 | 条款=`T2` 解析与建库 | 参考行=28 | 证据: 待补
7. 状态=未验证 | 条款=`T3` 检索与评分 | 参考行=29 | 证据: 待补
8. 状态=未验证 | 条款=`T4` LangGraph 工作流 | 参考行=30 | 证据: 待补
9. 状态=未验证 | 条款=`T5` 数据与安全 | 参考行=31 | 证据: 待补
10. 状态=未验证 | 条款=`T6` 前端交互 | 参考行=32 | 证据: 待补
11. 状态=未验证 | 条款=`T7` 测试与观测 | 参考行=33 | 证据: 待补
12. 状态=未验证 | 条款=`T8` 部署与运维 | 参考行=34 | 证据: 待补
13. 状态=未验证 | 条款=A-1：`docs/design/2026-02-21-gate-a-terminology-and-state-dictionary.md` | 参考行=58 | 证据: 待补
14. 状态=未验证 | 条款=A-2：`docs/design/2026-02-21-gate-a-boundary-and-side-effect-matrix.md` | 参考行=59 | 证据: 待补
15. 状态=未验证 | 条款=A-3：`docs/design/2026-02-21-legacy-detail-triage.md` | 参考行=60 | 证据: 待补
16. 状态=未验证 | 条款=定稿统一响应模型与错误对象。 | 参考行=68 | 证据: 待补
17. 状态=未验证 | 条款=定稿写接口幂等策略（`Idempotency-Key`）。 | 参考行=69 | 证据: 待补
18. 状态=未验证 | 条款=定稿异步任务契约（`202 + job_id` + 状态查询）。 | 参考行=70 | 证据: 待补
19. 状态=未验证 | 条款=定稿 `resume_token` 与 citation schema。 | 参考行=71 | 证据: 待补
20. 状态=未验证 | 条款=`docs/design/2026-02-21-openapi-v1.yaml` | 参考行=77 | 证据: 待补
21. 状态=未验证 | 条款=`docs/design/2026-02-21-api-contract-test-samples.md` | 参考行=78 | 证据: 待补
22. 状态=未验证 | 条款=定义任务状态机：`queued/running/retrying/succeeded/failed`。 | 参考行=84 | 证据: 待补
23. 状态=未验证 | 条款=落地重试策略：3 次重试 + 指数退避。 | 参考行=85 | 证据: 待补
24. 状态=未验证 | 条款=打通 DLQ 子流程入口。 | 参考行=86 | 证据: 待补
25. 状态=未验证 | 条款=`docs/design/2026-02-21-job-system-and-retry-spec.md` | 参考行=92 | 证据: 待补
26. 状态=未验证 | 条款=核心表建模：`jobs/workflow_checkpoints/dlq_items/audit_logs`。 | 参考行=98 | 证据: 待补
27. 状态=未验证 | 条款=RLS 策略与 `app.current_tenant` 注入策略落地。 | 参考行=99 | 证据: 待补
28. 状态=未验证 | 条款=outbox 事件表与消费幂等键建模。 | 参考行=100 | 证据: 待补
29. 状态=未验证 | 条款=解析器路由骨架：`mineru -> docling -> ocr`。 | 参考行=108 | 证据: 待补
30. 状态=未验证 | 条款=检索模式选择器骨架：`local/global/hybrid/mix`。 | 参考行=109 | 证据: 待补
31. 状态=未验证 | 条款=引用对象最小字段打通。 | 参考行=110 | 证据: 待补
32. 状态=未验证 | 条款=`docs/design/2026-02-21-openapi-v1.yaml` | 参考行=116 | 证据: 待补
33. 状态=未验证 | 条款=`docs/design/2026-02-21-api-contract-test-samples.md` | 参考行=117 | 证据: 待补
34. 状态=未验证 | 条款=`docs/design/2026-02-21-job-system-and-retry-spec.md` | 参考行=118 | 证据: 待补
35. 状态=未验证 | 条款=`docs/design/2026-02-21-gate-b-contract-and-skeleton-checklist.md` | 参考行=119 | 证据: 待补
36. 状态=未验证 | 条款=上传后异步投递 parse 任务。 | 参考行=127 | 证据: 待补
37. 状态=未验证 | 条款=parse run manifest 记录输入文件 hash 与解析路由。 | 参考行=128 | 证据: 待补
38. 状态=未验证 | 条款=解析失败按错误码分类。 | 参考行=129 | 证据: 待补
39. 状态=未验证 | 条款=支持 `content_list.json` 与 `context_list.json` 兼容读取。 | 参考行=137 | 证据: 待补
40. 状态=未验证 | 条款=`full.md` 用于 heading_path 结构补全。 | 参考行=138 | 证据: 待补
41. 状态=未验证 | 条款=bbox 归一化（支持 xyxy/xywh）。 | 参考行=139 | 证据: 待补
42. 状态=未验证 | 条款=编码回退（`utf-8 -> gb18030`）与错误码落地。 | 参考行=140 | 证据: 待补
43. 状态=未验证 | 条款=查询标准化 + 约束保持改写。 | 参考行=148 | 证据: 待补
44. 状态=未验证 | 条款=selector 选择 LightRAG 模式。 | 参考行=149 | 证据: 待补
45. 状态=未验证 | 条款=检索结果 metadata 过滤（tenant/project/doc_type）。 | 参考行=150 | 证据: 待补
46. 状态=未验证 | 条款=rerank 失败降级策略（原分数排序）。 | 参考行=151 | 证据: 待补
47. 状态=未验证 | 条款=规则引擎先做硬约束判定。 | 参考行=159 | 证据: 待补
48. 状态=未验证 | 条款=LLM 仅在规则允许范围输出软评分与说明。 | 参考行=160 | 证据: 待补
49. 状态=未验证 | 条款=评分项绑定 citation 列表。 | 参考行=161 | 证据: 待补
50. 状态=未验证 | 条款=生成总分、置信度、风险标签。 | 参考行=162 | 证据: 待补
51. 状态=未验证 | 条款=命中阈值进入 `needs_manual_decision`。 | 参考行=170 | 证据: 待补
52. 状态=未验证 | 条款=人工提交 `resume_token + decision` 恢复执行。 | 参考行=171 | 证据: 待补
53. 状态=未验证 | 条款=恢复操作写审计日志。 | 参考行=172 | 证据: 待补
54. 状态=未验证 | 条款=第 4 次失败触发 `dlq_pending`。 | 参考行=180 | 证据: 待补
55. 状态=未验证 | 条款=DLQ 写入成功后再置 `failed`。 | 参考行=181 | 证据: 待补
56. 状态=未验证 | 条款=提供 `requeue/discard` 运维接口。 | 参考行=182 | 证据: 待补
57. 状态=未验证 | 条款=RAGAS 指标门禁。 | 参考行=192 | 证据: 待补
58. 状态=未验证 | 条款=DeepEval 幻觉率门禁。 | 参考行=193 | 证据: 待补
59. 状态=未验证 | 条款=citation 回跳率门禁。 | 参考行=194 | 证据: 待补
60. 状态=未验证 | 条款=P1：RAGChecker 细粒度诊断触发流程。 | 参考行=195 | 证据: 待补
61. 状态=未验证 | 条款=API、检索、解析、评估压测。 | 参考行=203 | 证据: 待补
62. 状态=未验证 | 条款=高并发任务队列稳定性测试。 | 参考行=204 | 证据: 待补
63. 状态=未验证 | 条款=关键路径缓存命中率验证。 | 参考行=205 | 证据: 待补
64. 状态=未验证 | 条款=租户越权回归测试。 | 参考行=213 | 证据: 待补
65. 状态=未验证 | 条款=权限绕过与高风险动作审批测试。 | 参考行=214 | 证据: 待补
66. 状态=未验证 | 条款=日志脱敏与密钥扫描。 | 参考行=215 | 证据: 待补
67. 状态=未验证 | 条款=任务级成本统计。 | 参考行=223 | 证据: 待补
68. 状态=未验证 | 条款=模型路由与降级策略验证。 | 参考行=224 | 证据: 待补
69. 状态=未验证 | 条款=租户预算告警验证。 | 参考行=225 | 证据: 待补
70. 状态=未验证 | 条款=`docs/design/2026-02-22-gate-d-four-gates-checklist.md` | 参考行=231 | 证据: 待补
71. 状态=未验证 | 条款=先按租户白名单灰度。 | 参考行=237 | 证据: 待补
72. 状态=未验证 | 条款=再按项目规模分层放量。 | 参考行=238 | 证据: 待补
73. 状态=未验证 | 条款=高风险任务始终保留 HITL。 | 参考行=239 | 证据: 待补
74. 状态=未验证 | 条款=触发条件：任一门禁指标连续超阈值。 | 参考行=243 | 证据: 待补
75. 状态=未验证 | 条款=回滚顺序：模型配置 -> 检索参数 -> 工作流版本 -> 发布版本。 | 参考行=244 | 证据: 待补
76. 状态=未验证 | 条款=回滚后必须触发一次回放验证。 | 参考行=245 | 证据: 待补
77. 状态=未验证 | 条款=`docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md` | 参考行=251 | 证据: 待补
78. 状态=未验证 | 条款=DLQ 样本回流到反例集。 | 参考行=257 | 证据: 待补
79. 状态=未验证 | 条款=人审改判样本回流到黄金集候选。 | 参考行=258 | 证据: 待补
80. 状态=未验证 | 条款=每次版本迭代更新评估数据集版本号。 | 参考行=259 | 证据: 待补
81. 状态=未验证 | 条款=调整 selector 规则与阈值。 | 参考行=263 | 证据: 待补
82. 状态=未验证 | 条款=调整评分校准参数。 | 参考行=264 | 证据: 待补
83. 状态=未验证 | 条款=更新工具权限与审批策略。 | 参考行=265 | 证据: 待补
84. 状态=未验证 | 条款=`docs/design/2026-02-22-gate-f-operations-optimization-checklist.md` | 参考行=271 | 证据: 待补
85. 状态=未验证 | 条款=统一响应模型与错误模型。 | 参考行=277 | 证据: 待补
86. 状态=未验证 | 条款=幂等键中间件。 | 参考行=278 | 证据: 待补
87. 状态=未验证 | 条款=`jobs` 查询接口。 | 参考行=279 | 证据: 待补
88. 状态=未验证 | 条款=写接口异步化改造。 | 参考行=280 | 证据: 待补
89. 状态=未验证 | 条款=trace/request_id 贯穿。 | 参考行=281 | 证据: 待补
90. 状态=未验证 | 条款=任务重试策略实现。 | 参考行=282 | 证据: 待补
91. 状态=未验证 | 条款=任务取消策略实现。 | 参考行=283 | 证据: 待补
92. 状态=未验证 | 条款=状态事件发布。 | 参考行=284 | 证据: 待补
93. 状态=未验证 | 条款=任务审计落库。 | 参考行=285 | 证据: 待补
94. 状态=未验证 | 条款=并发冲突处理。 | 参考行=286 | 证据: 待补
95. 状态=未验证 | 条款=限流策略。 | 参考行=287 | 证据: 待补
96. 状态=未验证 | 条款=回放测试接口（内部）。 | 参考行=288 | 证据: 待补
97. 状态=未验证 | 条款=运维查询接口。 | 参考行=289 | 证据: 待补
98. 状态=未验证 | 条款=API 契约回归测试。 | 参考行=290 | 证据: 待补
99. 状态=未验证 | 条款=解析器路由器。 | 参考行=294 | 证据: 待补
100. 状态=未验证 | 条款=文件探测与 manifest。 | 参考行=295 | 证据: 待补
101. 状态=未验证 | 条款=MinerU 文件发现链。 | 参考行=296 | 证据: 待补
102. 状态=未验证 | 条款=`context_list` 兼容。 | 参考行=297 | 证据: 待补
103. 状态=未验证 | 条款=bbox 归一化。 | 参考行=298 | 证据: 待补
104. 状态=未验证 | 条款=heading_path 提取。 | 参考行=299 | 证据: 待补
105. 状态=未验证 | 条款=chunk 切分器。 | 参考行=300 | 证据: 待补
106. 状态=未验证 | 条款=chunk 合并规则。 | 参考行=301 | 证据: 待补
107. 状态=未验证 | 条款=chunk 去重策略。 | 参考行=302 | 证据: 待补
108. 状态=未验证 | 条款=metadata 最小字段校验。 | 参考行=303 | 证据: 待补
109. 状态=未验证 | 条款=PG chunks 入库。 | 参考行=304 | 证据: 待补
110. 状态=未验证 | 条款=Chroma 索引写入。 | 参考行=305 | 证据: 待补
111. 状态=未验证 | 条款=parse 错误分类。 | 参考行=306 | 证据: 待补
112. 状态=未验证 | 条款=fallback OCR 路径。 | 参考行=307 | 证据: 待补
113. 状态=未验证 | 条款=解析耗时指标。 | 参考行=308 | 证据: 待补
114. 状态=未验证 | 条款=样本回放脚本。 | 参考行=309 | 证据: 待补
115. 状态=未验证 | 条款=引用可回跳验证。 | 参考行=310 | 证据: 待补
116. 状态=未验证 | 条款=解析链路集成测试。 | 参考行=311 | 证据: 待补
117. 状态=未验证 | 条款=查询标准化。 | 参考行=315 | 证据: 待补
118. 状态=未验证 | 条款=约束抽取器。 | 参考行=316 | 证据: 待补
119. 状态=未验证 | 条款=约束保持改写器。 | 参考行=317 | 证据: 待补
120. 状态=未验证 | 条款=mode selector。 | 参考行=318 | 证据: 待补
121. 状态=未验证 | 条款=LightRAG 参数适配。 | 参考行=319 | 证据: 待补
122. 状态=未验证 | 条款=include references 开关。 | 参考行=320 | 证据: 待补
123. 状态=未验证 | 条款=metadata 过滤器。 | 参考行=321 | 证据: 待补
124. 状态=未验证 | 条款=SQL 白名单支路。 | 参考行=322 | 证据: 待补
125. 状态=未验证 | 条款=rerank 组件。 | 参考行=323 | 证据: 待补
126. 状态=未验证 | 条款=rerank 降级策略。 | 参考行=324 | 证据: 待补
127. 状态=未验证 | 条款=evidence packing。 | 参考行=325 | 证据: 待补
128. 状态=未验证 | 条款=规则引擎。 | 参考行=326 | 证据: 待补
129. 状态=未验证 | 条款=LLM 评分器。 | 参考行=327 | 证据: 待补
130. 状态=未验证 | 条款=置信度计算器。 | 参考行=328 | 证据: 待补
131. 状态=未验证 | 条款=评分校准（P1）。 | 参考行=329 | 证据: 待补
132. 状态=未验证 | 条款=citation coverage 检查器。 | 参考行=330 | 证据: 待补
133. 状态=未验证 | 条款=幻觉保护检查器。 | 参考行=331 | 证据: 待补
134. 状态=未验证 | 条款=评分结果 schema。 | 参考行=332 | 证据: 待补
135. 状态=未验证 | 条款=检索评分集成测试。 | 参考行=333 | 证据: 待补
136. 状态=未验证 | 条款=状态对象定义。 | 参考行=337 | 证据: 待补
137. 状态=未验证 | 条款=节点边界定义。 | 参考行=338 | 证据: 待补
138. 状态=未验证 | 条款=条件路由。 | 参考行=339 | 证据: 待补
139. 状态=未验证 | 条款=checkpoint 持久化。 | 参考行=340 | 证据: 待补
140. 状态=未验证 | 条款=`thread_id` 策略。 | 参考行=341 | 证据: 待补
141. 状态=未验证 | 条款=interrupt 节点。 | 参考行=342 | 证据: 待补
142. 状态=未验证 | 条款=resume API 适配。 | 参考行=343 | 证据: 待补
143. 状态=未验证 | 条款=side effect 提交节点。 | 参考行=344 | 证据: 待补
144. 状态=未验证 | 条款=幂等保护。 | 参考行=345 | 证据: 待补
145. 状态=未验证 | 条款=错误路由 DLQ。 | 参考行=346 | 证据: 待补
146. 状态=未验证 | 条款=状态观测埋点。 | 参考行=347 | 证据: 待补
147. 状态=未验证 | 条款=回放测试场景。 | 参考行=348 | 证据: 待补
148. 状态=未验证 | 条款=恢复演练脚本。 | 参考行=349 | 证据: 待补
149. 状态=未验证 | 条款=核心表与索引落地。 | 参考行=353 | 证据: 待补
150. 状态=未验证 | 条款=RLS 全量策略。 | 参考行=354 | 证据: 待补
151. 状态=未验证 | 条款=tenant 注入中间件。 | 参考行=355 | 证据: 待补
152. 状态=未验证 | 条款=Redis key 规范。 | 参考行=356 | 证据: 待补
153. 状态=未验证 | 条款=密钥与配置治理。 | 参考行=357 | 证据: 待补
154. 状态=未验证 | 条款=审计日志落地。 | 参考行=358 | 证据: 待补
155. 状态=未验证 | 条款=legal hold 控制。 | 参考行=359 | 证据: 待补
156. 状态=未验证 | 条款=高风险动作审批。 | 参考行=360 | 证据: 待补
157. 状态=未验证 | 条款=安全扫描基线。 | 参考行=361 | 证据: 待补
158. 状态=未验证 | 条款=安全集成回归。 | 参考行=362 | 证据: 待补
159. 状态=未验证 | 条款=路由与权限门控。 | 参考行=366 | 证据: 待补
160. 状态=未验证 | 条款=上传页任务状态。 | 参考行=367 | 证据: 待补
161. 状态=未验证 | 条款=评估页点对点表格。 | 参考行=368 | 证据: 待补
162. 状态=未验证 | 条款=证据面板。 | 参考行=369 | 证据: 待补
163. 状态=未验证 | 条款=PDF 页码跳转。 | 参考行=370 | 证据: 待补
164. 状态=未验证 | 条款=bbox 高亮层。 | 参考行=371 | 证据: 待补
165. 状态=未验证 | 条款=人审操作面板。 | 参考行=372 | 证据: 待补
166. 状态=未验证 | 条款=DLQ 管理页。 | 参考行=373 | 证据: 待补
167. 状态=未验证 | 条款=错误与重试提示。 | 参考行=374 | 证据: 待补
168. 状态=未验证 | 条款=E2E 场景覆盖。 | 参考行=375 | 证据: 待补
169. 状态=未验证 | 条款=单元测试基线。 | 参考行=379 | 证据: 待补
170. 状态=未验证 | 条款=集成测试基线。 | 参考行=380 | 证据: 待补
171. 状态=未验证 | 条款=E2E 测试基线。 | 参考行=381 | 证据: 待补
172. 状态=未验证 | 条款=RAGAS 脚本。 | 参考行=382 | 证据: 待补
173. 状态=未验证 | 条款=DeepEval 脚本。 | 参考行=383 | 证据: 待补
174. 状态=未验证 | 条款=RAGChecker 触发器（P1）。 | 参考行=384 | 证据: 待补
175. 状态=未验证 | 条款=指标看板定义。 | 参考行=385 | 证据: 待补
176. 状态=未验证 | 条款=Trace 关联规则。 | 参考行=386 | 证据: 待补
177. 状态=未验证 | 条款=告警策略。 | 参考行=387 | 证据: 待补
178. 状态=未验证 | 条款=压测脚本。 | 参考行=388 | 证据: 待补
179. 状态=未验证 | 条款=漂移检测作业。 | 参考行=389 | 证据: 待补
180. 状态=未验证 | 条款=周期复盘模板。 | 参考行=390 | 证据: 待补
181. 状态=未验证 | 条款=环境配置模板。 | 参考行=394 | 证据: 待补
182. 状态=未验证 | 条款=灰度发布剧本。 | 参考行=395 | 证据: 待补
183. 状态=未验证 | 条款=回滚剧本。 | 参考行=396 | 证据: 待补
184. 状态=未验证 | 条款=DLQ 处置剧本。 | 参考行=397 | 证据: 待补
185. 状态=未验证 | 条款=事故 runbook 演练。 | 参考行=398 | 证据: 待补
186. 状态=未验证 | 条款=变更审批流。 | 参考行=399 | 证据: 待补
187. 状态=未验证 | 条款=发布门禁流水线。 | 参考行=400 | 证据: 待补
188. 状态=未验证 | 条款=用周计划替代 Gate 证据机制。 | 参考行=404 | 证据: 待补
189. 状态=未验证 | 条款=在主链路引入未验证的重检索框架。 | 参考行=405 | 证据: 待补
190. 状态=未验证 | 条款=跳过人审直接自动终审。 | 参考行=406 | 证据: 待补
191. 状态=未验证 | 条款=SSOT 与专项文档一致。 | 参考行=412 | 证据: 待补
192. 状态=未验证 | 条款=主链路 E2E 可运行。 | 参考行=413 | 证据: 待补
193. 状态=未验证 | 条款=四门禁报告可复核。 | 参考行=414 | 证据: 待补
194. 状态=未验证 | 条款=灰度和回滚演练通过。 | 参考行=415 | 证据: 待补
195. 状态=未验证 | 条款=运维与事故流程可执行。 | 参考行=416 | 证据: 待补
196. 状态=未验证 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=420 | 证据: 待补
197. 状态=未验证 | 条款=LangGraph docs: https://docs.langchain.com/oss/python/langgraph/ | 参考行=421 | 证据: 待补
198. 状态=未验证 | 条款=LangChain docs: https://docs.langchain.com/oss/python/langchain/ | 参考行=422 | 证据: 待补
199. 状态=未验证 | 条款=FastAPI docs: https://fastapi.tiangolo.com/ | 参考行=423 | 证据: 待补
200. 状态=未验证 | 条款=`docs/plans/2026-02-22-production-capability-plan.md` | 参考行=431 | 证据: 待补
201. 状态=未验证 | 条款=`docs/design/2026-02-22-persistence-and-queue-production-spec.md` | 参考行=435 | 证据: 待补
202. 状态=未验证 | 条款=`docs/design/2026-02-22-parser-and-retrieval-production-spec.md` | 参考行=436 | 证据: 待补
203. 状态=未验证 | 条款=`docs/design/2026-02-22-workflow-and-worker-production-spec.md` | 参考行=437 | 证据: 待补
204. 状态=未验证 | 条款=`docs/design/2026-02-22-security-and-multitenancy-production-spec.md` | 参考行=438 | 证据: 待补
205. 状态=未验证 | 条款=`docs/design/2026-02-22-observability-and-deploy-production-spec.md` | 参考行=439 | 证据: 待补
206. 状态=未验证 | 条款=先更新文档契约，再替换实现。 | 参考行=443 | 证据: 待补
207. 状态=未验证 | 条款=每条轨道独立验收，最后统一真栈回放收口。 | 参考行=444 | 证据: 待补
208. 状态=未验证 | 条款=任一轨道故障可独立回退，不破坏整体骨架契约。 | 参考行=445 | 证据: 待补

**文件：docs/design/2026-02-21-job-system-and-retry-spec.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=固化异步任务状态机与合法流转。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=固化 3 次重试 + 指数退避 + 抖动策略。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=固化 DLQ 入列时序与失败终态规则。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=提供“可回放验证”的最小测试场景集合。 | 参考行=12 | 证据: 待补
5. 状态=未验证 | 条款=`job_id` | 参考行=20 | 证据: 待补
6. 状态=未验证 | 条款=`tenant_id` | 参考行=21 | 证据: 待补
7. 状态=未验证 | 条款=`job_type` | 参考行=22 | 证据: 待补
8. 状态=未验证 | 条款=`status` | 参考行=23 | 证据: 待补
9. 状态=未验证 | 条款=`retry_count` | 参考行=24 | 证据: 待补
10. 状态=未验证 | 条款=`idempotency_key` | 参考行=25 | 证据: 待补
11. 状态=未验证 | 条款=`trace_id` | 参考行=26 | 证据: 待补
12. 状态=未验证 | 条款=`error_code` | 参考行=27 | 证据: 待补
13. 状态=未验证 | 条款=`payload_json` | 参考行=28 | 证据: 待补
14. 状态=未验证 | 条款=`created_at/updated_at` | 参考行=29 | 证据: 待补
15. 状态=未验证 | 条款=`queued` | 参考行=53 | 证据: 待补
16. 状态=未验证 | 条款=`running` | 参考行=54 | 证据: 待补
17. 状态=未验证 | 条款=`retrying` | 参考行=55 | 证据: 待补
18. 状态=未验证 | 条款=`succeeded` | 参考行=56 | 证据: 待补
19. 状态=未验证 | 条款=`dlq_pending` | 参考行=57 | 证据: 待补
20. 状态=未验证 | 条款=`dlq_recorded` | 参考行=58 | 证据: 待补
21. 状态=未验证 | 条款=`failed` | 参考行=59 | 证据: 待补
22. 状态=未验证 | 条款=`failed` 只能出现在 `dlq_recorded` 之后。 | 参考行=63 | 证据: 待补
23. 状态=未验证 | 条款=`succeeded` 与 `failed` 为互斥终态。 | 参考行=64 | 证据: 待补
24. 状态=未验证 | 条款=非法流转返回 `WF_STATE_TRANSITION_INVALID`。 | 参考行=65 | 证据: 待补
25. 状态=未验证 | 条款=仅 `retryable=true` 错误允许重试。 | 参考行=71 | 证据: 待补
26. 状态=未验证 | 条款=最大重试次数：3（第 4 次失败进入 DLQ）。 | 参考行=72 | 证据: 待补
27. 状态=未验证 | 条款=`base_ms = 1000` | 参考行=83 | 证据: 待补
28. 状态=未验证 | 条款=`max_backoff_ms = 30000` | 参考行=84 | 证据: 待补
29. 状态=未验证 | 条款=`retry_count` 从 1 开始计数 | 参考行=85 | 证据: 待补
30. 状态=未验证 | 条款=同一任务重试不得改变 `job_id`。 | 参考行=89 | 证据: 待补
31. 状态=未验证 | 条款=同一次重试执行必须有幂等键：`job_id + retry_count`。 | 参考行=90 | 证据: 待补
32. 状态=未验证 | 条款=已提交副作用节点禁止重复提交。 | 参考行=91 | 证据: 待补
33. 状态=未验证 | 条款=`requeue`：创建新 job，关联原 `dlq_id`。 | 参考行=107 | 证据: 待补
34. 状态=未验证 | 条款=`discard`：双人复核 + 必填 reason。 | 参考行=108 | 证据: 待补
35. 状态=未验证 | 条款=每次回放记录 `trace_id/job_id/retry_count/status_transition`。 | 参考行=122 | 证据: 待补
36. 状态=未验证 | 条款=任一案例失败，Gate B-2 不通过。 | 参考行=123 | 证据: 待补
37. 状态=未验证 | 条款=`POST /api/v1/internal/jobs/{job_id}/run`：成功路径（`queued/running -> succeeded`）。 | 参考行=129 | 证据: 待补
38. 状态=未验证 | 条款=`POST /api/v1/internal/jobs/{job_id}/run?force_fail=true`：直接进入 DLQ 终态路径。 | 参考行=130 | 证据: 待补
39. 状态=未验证 | 条款=`POST /api/v1/internal/jobs/{job_id}/run?transient_fail=true`： | 参考行=131 | 证据: 待补
40. 状态=未验证 | 条款=`retrying` 比例超过阈值触发告警。 | 参考行=137 | 证据: 待补
41. 状态=未验证 | 条款=单租户 `dlq_pending` 增速异常触发告警。 | 参考行=138 | 证据: 待补
42. 状态=未验证 | 条款=`WF_STATE_TRANSITION_INVALID` 连续出现触发 P1 排查。 | 参考行=139 | 证据: 待补
43. 状态=未验证 | 条款=状态机定义与 `jobs.status` 字段一致。 | 参考行=143 | 证据: 待补
44. 状态=未验证 | 条款=重试次数与退避规则可回放复现。 | 参考行=144 | 证据: 待补
45. 状态=未验证 | 条款=第 4 次失败严格进入 `dlq_pending -> dlq_recorded -> failed`。 | 参考行=145 | 证据: 待补
46. 状态=未验证 | 条款=回放样例 `RP-001` 至 `RP-005` 全通过。 | 参考行=146 | 证据: 待补
47. 状态=未验证 | 条款=`docs/design/2026-02-21-error-handling-and-dlq-spec.md` | 参考行=150 | 证据: 待补
48. 状态=未验证 | 条款=`docs/design/2026-02-21-data-model-and-storage-spec.md` | 参考行=151 | 证据: 待补
49. 状态=未验证 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=152 | 证据: 待补
50. 状态=未验证 | 条款=`docs/design/2026-02-21-testing-strategy.md` | 参考行=153 | 证据: 待补

**文件：docs/design/2026-02-21-langgraph-agent-workflow-spec.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
1. 状态=已实现 | 条款=将评标流程固化为可执行状态机。 | 参考行=9 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
2. 状态=已实现 | 条款=保证中断恢复、幂等与副作用边界可控。 | 参考行=10 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
3. 状态=已实现 | 条款=异常路径可追踪、可重试、可落 DLQ。 | 参考行=11 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
4. 状态=已实现 | 条款=保持与 LangGraph 官方 checkpoint/interrupt 模式一致。 | 参考行=12 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
5. 状态=已实现 | 条款=`tenant_id` | 参考行=37 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
6. 状态=已实现 | 条款=`evaluation_id` | 参考行=38 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
7. 状态=已实现 | 条款=`thread_id` | 参考行=39 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
8. 状态=已实现 | 条款=`quality_gate == pass` -> `finalize_report`。 | 参考行=81 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
9. 状态=已实现 | 条款=`quality_gate == hitl` -> `human_review_interrupt`。 | 参考行=82 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
10. 状态=已实现 | 条款=`retryable=true && retry_count<3` -> `retry`。 | 参考行=86 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
11. 状态=已实现 | 条款=否则 -> `dlq_pending -> dlq_recorded -> failed`。 | 参考行=87 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
12. 状态=已实现 | 条款=收到合法 `resume_token` -> `finalize_report`。 | 参考行=91 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
13. 状态=已实现 | 条款=token 过期/不匹配 -> `WF_INTERRUPT_RESUME_INVALID`。 | 参考行=92 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
14. 状态=已实现 | 条款=启用持久化 checkpointer（PostgreSQL 后端）。 | 参考行=96 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
15. 状态=已实现 | 条款=每次 `invoke` 必须传 `configurable.thread_id`。 | 参考行=97 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
16. 状态=已实现 | 条款=相同 `thread_id` 表示恢复同一工作流；新 `thread_id` 表示新线程。 | 参考行=98 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
17. 状态=已实现 | 条款=`interrupt` payload 必须 JSON 可序列化。 | 参考行=99 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
18. 状态=已实现 | 条款=中断信息统一通过 `__interrupt__` 返回给 API 层。 | 参考行=100 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
19. 状态=已实现 | 条款=`resume_token` 单次有效。 | 参考行=131 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
20. 状态=已实现 | 条款=恢复请求必须带操作者身份。 | 参考行=132 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
21. 状态=已实现 | 条款=恢复行为写入 `audit_logs`。 | 参考行=133 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
22. 状态=已实现 | 条款=`persist_result` 幂等键：`evaluation_id + report_version`。 | 参考行=137 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
23. 状态=已实现 | 条款=`retry_or_dlq` 幂等键：`job_id + retry_count`。 | 参考行=138 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
24. 状态=已实现 | 条款=副作用失败时只重试当前节点，不回放已成功副作用。 | 参考行=139 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
25. 状态=已实现 | 条款=并发恢复请求以 `resume_token` 乐观锁处理。 | 参考行=140 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
26. 状态=已实现 | 条款=节点抛错先分类：`validation/business/transient/permanent/security`。 | 参考行=144 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
27. 状态=已实现 | 条款=transient 可重试，其他直接进入 DLQ 子流程。 | 参考行=145 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
28. 状态=已实现 | 条款=所有错误落 `errors[]`，并带 `trace_id`。 | 参考行=146 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
29. 状态=已实现 | 条款=`trace_id` | 参考行=152 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
30. 状态=已实现 | 条款=`thread_id` | 参考行=153 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
31. 状态=已实现 | 条款=`node_name` | 参考行=154 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
32. 状态=已实现 | 条款=`started_at/ended_at` | 参考行=155 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
33. 状态=已实现 | 条款=`latency_ms` | 参考行=156 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
34. 状态=已实现 | 条款=`input_size/output_size` | 参考行=157 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
35. 状态=已实现 | 条款=`error_code`（若有） | 参考行=158 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
36. 状态=已实现 | 条款=interrupt 后可在 24h 内恢复。 | 参考行=162 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
37. 状态=已实现 | 条款=checkpoint 恢复后不重复执行已完成节点。 | 参考行=163 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
38. 状态=已实现 | 条款=非法状态流转被 100% 拦截。 | 参考行=164 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
39. 状态=已实现 | 条款=failed 状态都可关联到 DLQ 记录。 | 参考行=165 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
40. 状态=已实现 | 条款=LangGraph interrupts/persistence/durable execution: | 参考行=169 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py
41. 状态=已实现 | 条款=历史融合提交：`7f05f7e`, `72a64da` | 参考行=171 | 证据: docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; app/langgraph_runtime.py

**文件：docs/design/2026-02-21-legacy-detail-triage.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=`保留`：可直接落地到现行设计。 | 参考行=10 | 证据: 待补
2. 状态=未验证 | 条款=`修正后保留`：思路可用，但字段/流程/边界需纠偏。 | 参考行=11 | 证据: 待补
3. 状态=未验证 | 条款=`废弃`：与现行目标、风险控制或维护成本冲突。 | 参考行=12 | 证据: 待补
4. 状态=未验证 | 条款=`7f05f7e`（架构设计 v5.3） | 参考行=45 | 证据: 待补
5. 状态=未验证 | 条款=`7f07ad6`（架构验证报告） | 参考行=46 | 证据: 待补
6. 状态=未验证 | 条款=`53e3d92`（点对点应答/溯源引用/RAGChecker） | 参考行=47 | 证据: 待补
7. 状态=未验证 | 条款=`184a6ac`（GitHub 项目详细分析） | 参考行=48 | 证据: 待补
8. 状态=未验证 | 条款=`72a64da`（Agentic-Procure-Audit-AI 分析） | 参考行=49 | 证据: 待补
9. 状态=未验证 | 条款=`a21fa09`（MinerU 相关项目研究） | 参考行=50 | 证据: 待补
10. 状态=未验证 | 条款=`76f898d`（MinerU 输出处理研究） | 参考行=51 | 证据: 待补
11. 状态=未验证 | 条款=`beef3e9`（旧版设计文档集合） | 参考行=52 | 证据: 待补
12. 状态=未验证 | 条款=开发执行只以 SSOT 与 `docs/design/` 现行文档为准。 | 参考行=56 | 证据: 待补
13. 状态=未验证 | 条款=任何新细节先写入现行文档，再更新本判定表。 | 参考行=57 | 证据: 待补
14. 状态=未验证 | 条款=不再维护历史目录作为并行规范源。 | 参考行=58 | 证据: 待补
15. 状态=未验证 | 条款=历史细节已按“保留/修正后保留/废弃”完成归类。 | 参考行=62 | 证据: 待补
16. 状态=未验证 | 条款=所有“修正后保留”均已明确现行落点文档。 | 参考行=63 | 证据: 待补
17. 状态=未验证 | 条款=后续若新增历史融合项，必须同步更新本表与落点文档。 | 参考行=64 | 证据: 待补

**文件：docs/design/2026-02-21-mineru-ingestion-spec.md**
文件级结论：部分实现 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
1. 状态=部分实现 | 条款=保留原文定位能力：`page + bbox`。 | 参考行=9 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
2. 状态=部分实现 | 条款=保留结构语义：`section + heading_path`。 | 参考行=10 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
3. 状态=部分实现 | 条款=产出稳定 chunk，支持检索、评分与引用回跳。 | 参考行=11 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
4. 状态=部分实现 | 条款=明确异常分类、重试边界、失败落库策略。 | 参考行=12 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
5. 状态=部分实现 | 条款=`*_content_list.json`（定位主来源） | 参考行=18 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
6. 状态=部分实现 | 条款=`full.md`（结构主来源） | 参考行=19 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
7. 状态=部分实现 | 条款=`*_middle.json`（调试辅助，可选） | 参考行=20 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
8. 状态=部分实现 | 条款=`*context_list.json`（旧命名兼容） | 参考行=24 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
9. 状态=部分实现 | 条款=`*.md`（当 `full.md` 缺失时回退） | 参考行=25 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
10. 状态=部分实现 | 条款=主解析失败才允许 fallback。 | 参考行=48 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
11. 状态=部分实现 | 条款=fallback 链最多 2 跳，避免无限回退。 | 参考行=49 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
12. 状态=部分实现 | 条款=每次路由决策都写入 parse manifest。 | 参考行=50 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
13. 状态=部分实现 | 条款=`document_id` | 参考行=56 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
14. 状态=部分实现 | 条款=`tenant_id` | 参考行=57 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
15. 状态=部分实现 | 条款=`selected_parser` | 参考行=58 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
16. 状态=部分实现 | 条款=`fallback_chain` | 参考行=59 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
17. 状态=部分实现 | 条款=`input_files[{name, sha256, size}]` | 参考行=60 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
18. 状态=部分实现 | 条款=`started_at` | 参考行=61 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
19. 状态=部分实现 | 条款=`ended_at` | 参考行=62 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
20. 状态=部分实现 | 条款=`status` | 参考行=63 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
21. 状态=部分实现 | 条款=`error_code` | 参考行=64 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
22. 状态=部分实现 | 条款=`text` | 参考行=70 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
23. 状态=部分实现 | 条款=`type` | 参考行=71 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
24. 状态=部分实现 | 条款=`page_idx` | 参考行=72 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
25. 状态=部分实现 | 条款=`bbox` | 参考行=73 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
26. 状态=部分实现 | 条款=`[x0,y0,x1,y1]`（xyxy） | 参考行=79 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
27. 状态=部分实现 | 条款=`[x,y,w,h]`（xywh） | 参考行=80 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
28. 状态=部分实现 | 条款=若 `x1>x0 && y1>y0` 直接视为 xyxy。 | 参考行=86 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
29. 状态=部分实现 | 条款=若 `w>0 && h>0` 且不满足上条，视为 xywh 转换。 | 参考行=87 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
30. 状态=部分实现 | 条款=无法判定 -> `MINERU_BBOX_FORMAT_INVALID`。 | 参考行=88 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
31. 状态=部分实现 | 条款=编码读取优先 `utf-8`，失败尝试 `gb18030`。 | 参考行=92 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
32. 状态=部分实现 | 条款=换行统一为 `\n`。 | 参考行=93 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
33. 状态=部分实现 | 条款=移除非法控制字符（保留 `\t`）。 | 参考行=94 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
34. 状态=部分实现 | 条款=失败错误码：`TEXT_ENCODING_UNSUPPORTED`。 | 参考行=95 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
35. 状态=部分实现 | 条款=以 JSON item 顺序构建定位片段。 | 参考行=99 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
36. 状态=部分实现 | 条款=用 `full.md` 构建 heading 树。 | 参考行=100 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
37. 状态=部分实现 | 条款=将 heading_path 映射回 JSON 片段，生成结构化 chunk。 | 参考行=101 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
38. 状态=部分实现 | 条款=定位冲突：以 JSON 为准。 | 参考行=105 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
39. 状态=部分实现 | 条款=结构冲突：以 `full.md` 为准，但必须记录冲突标记。 | 参考行=106 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
40. 状态=部分实现 | 条款=两者均缺失：标注 `structure_missing=true`。 | 参考行=107 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
41. 状态=部分实现 | 条款=`target_size_tokens = 450` | 参考行=113 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
42. 状态=部分实现 | 条款=`max_size_tokens = 700` | 参考行=114 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
43. 状态=部分实现 | 条款=`overlap_tokens = 80` | 参考行=115 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
44. 状态=部分实现 | 条款=`min_size_tokens = 120` | 参考行=116 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
45. 状态=部分实现 | 条款=标题层级变化 | 参考行=122 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
46. 状态=部分实现 | 条款=表格块边界 | 参考行=123 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
47. 状态=部分实现 | 条款=列表块边界 | 参考行=124 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
48. 状态=部分实现 | 条款=页面跳转边界 | 参考行=125 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
49. 状态=部分实现 | 条款=把同一表格切成多段（除超大表格）。 | 参考行=129 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
50. 状态=部分实现 | 条款=把同一句跨 chunk 截断且无 overlap。 | 参考行=130 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
51. 状态=部分实现 | 条款=`chunk_id` | 参考行=134 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
52. 状态=部分实现 | 条款=`tenant_id` | 参考行=135 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
53. 状态=部分实现 | 条款=`project_id` | 参考行=136 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
54. 状态=部分实现 | 条款=`document_id` | 参考行=137 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
55. 状态=部分实现 | 条款=`supplier_id` | 参考行=138 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
56. 状态=部分实现 | 条款=`pages[]` | 参考行=139 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
57. 状态=部分实现 | 条款=`positions[]`（`{page,bbox,start,end}`） | 参考行=140 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
58. 状态=部分实现 | 条款=`section` | 参考行=141 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
59. 状态=部分实现 | 条款=`heading_path[]` | 参考行=142 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
60. 状态=部分实现 | 条款=`chunk_type`（`text/table/image/formula/list`） | 参考行=143 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
61. 状态=部分实现 | 条款=`parser` | 参考行=144 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
62. 状态=部分实现 | 条款=`parser_version` | 参考行=145 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
63. 状态=部分实现 | 条款=PG chunks 失败：不进入向量写入。 | 参考行=159 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
64. 状态=部分实现 | 条款=向量写入部分成功：记录待修复任务，不标记 indexed。 | 参考行=160 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
65. 状态=部分实现 | 条款=全部失败：进入任务重试/最终 DLQ。 | 参考行=161 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
66. 状态=部分实现 | 条款=可唯一定位 `chunk_id` | 参考行=167 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
67. 状态=部分实现 | 条款=至少一条 `positions[{page,bbox}]` | 参考行=168 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
68. 状态=部分实现 | 条款=`bbox` 坐标可映射到 PDF viewport | 参考行=169 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
69. 状态=部分实现 | 条款=若有多页位置，默认返回与 claim 最相关的一条作为 `primary_position` | 参考行=170 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
70. 状态=部分实现 | 条款=`DOC_PARSE_OUTPUT_NOT_FOUND`：关键输出缺失，立即失败。 | 参考行=174 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
71. 状态=部分实现 | 条款=`DOC_PARSE_SCHEMA_INVALID`：JSON 结构错误，最多重试 1 次。 | 参考行=175 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
72. 状态=部分实现 | 条款=`MINERU_BBOX_FORMAT_INVALID`：bbox 非法，不可重试。 | 参考行=176 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
73. 状态=部分实现 | 条款=`TEXT_ENCODING_UNSUPPORTED`：编码不可识别，不可重试。 | 参考行=177 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
74. 状态=部分实现 | 条款=`PARSER_FALLBACK_EXHAUSTED`：fallback 链耗尽，进入 DLQ。 | 参考行=178 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
75. 状态=部分实现 | 条款=`content_list/context_list` 均可被正确处理。 | 参考行=182 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
76. 状态=部分实现 | 条款=chunk 位置回跳成功率 >= 98%。 | 参考行=183 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
77. 状态=部分实现 | 条款=同一文档重复解析（同版本配置）产出差异 <= 1%。 | 参考行=184 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
78. 状态=部分实现 | 条款=解析失败样本均有明确错误码与 trace。 | 参考行=185 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
79. 状态=部分实现 | 条款=MinerU: https://github.com/opendatalab/MinerU | 参考行=189 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
80. 状态=部分实现 | 条款=Docling: https://github.com/docling-project/docling | 参考行=190 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
81. 状态=部分实现 | 条款=历史融合提交：`76f898d`, `a21fa09`, `7f05f7e` | 参考行=191 | 证据: app/parser_adapters.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md

**文件：docs/design/2026-02-21-rest-api-specification.md**
文件级结论：部分实现 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
1. 状态=部分实现 | 条款=基础路径：`/api/v1` | 参考行=9 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
2. 状态=部分实现 | 条款=鉴权：JWT Bearer（租户从 token 注入） | 参考行=10 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
3. 状态=部分实现 | 条款=写接口：强制 `Idempotency-Key` | 参考行=11 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
4. 状态=部分实现 | 条款=长任务：返回 `202 Accepted + job_id` | 参考行=12 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
5. 状态=部分实现 | 条款=所有响应：包含 `trace_id` | 参考行=13 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
6. 状态=部分实现 | 条款=所有响应头：包含 `x-trace-id` 与 `x-request-id` | 参考行=14 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
7. 状态=部分实现 | 条款=当 `TRACE_ID_STRICT_REQUIRED=true` 时，`/api/v1/*` 请求必须显式携带 `x-trace-id`，缺失返回 `400 TRACE_ID_REQUIRED` | 参考行=15 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
8. 状态=部分实现 | 条款=`POST /auth/login` | 参考行=53 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
9. 状态=部分实现 | 条款=`POST /auth/refresh` | 参考行=54 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
10. 状态=部分实现 | 条款=`POST /auth/logout` | 参考行=55 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
11. 状态=部分实现 | 条款=`GET /auth/me` | 参考行=56 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
12. 状态=部分实现 | 条款=refresh token 走 HttpOnly Cookie。 | 参考行=60 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
13. 状态=部分实现 | 条款=refresh 接口启用 CSRF 校验。 | 参考行=61 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
14. 状态=部分实现 | 条款=`GET /projects` | 参考行=67 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
15. 状态=部分实现 | 条款=`POST /projects` | 参考行=68 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
16. 状态=部分实现 | 条款=`GET /projects/{project_id}` | 参考行=69 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
17. 状态=部分实现 | 条款=`PUT /projects/{project_id}` | 参考行=70 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
18. 状态=部分实现 | 条款=`DELETE /projects/{project_id}` | 参考行=71 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
19. 状态=部分实现 | 条款=`GET /suppliers` | 参考行=75 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
20. 状态=部分实现 | 条款=`POST /suppliers` | 参考行=76 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
21. 状态=部分实现 | 条款=`GET /suppliers/{supplier_id}` | 参考行=77 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
22. 状态=部分实现 | 条款=`PUT /suppliers/{supplier_id}` | 参考行=78 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
23. 状态=部分实现 | 条款=`GET /rules` | 参考行=82 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
24. 状态=部分实现 | 条款=`POST /rules` | 参考行=83 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
25. 状态=部分实现 | 条款=`GET /rules/{rule_pack_version}` | 参考行=84 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
26. 状态=部分实现 | 条款=`PUT /rules/{rule_pack_version}` | 参考行=85 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
27. 状态=部分实现 | 条款=`DELETE /rules/{rule_pack_version}` | 参考行=86 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
28. 状态=部分实现 | 条款=`rule_pack_version` 作为唯一标识。 | 参考行=90 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
29. 状态=部分实现 | 条款=`rules` 为规则包 JSON。 | 参考行=91 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
30. 状态=部分实现 | 条款=`POST /documents/upload` -> `202 + parse job_id`（上传后自动投递 parse） | 参考行=95 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
31. 状态=部分实现 | 条款=`POST /documents/{document_id}/parse` -> `202 + job_id`（手动重投/补投） | 参考行=96 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
32. 状态=部分实现 | 条款=`GET /documents/{document_id}` | 参考行=97 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
33. 状态=部分实现 | 条款=`GET /documents/{document_id}/raw` | 参考行=98 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
34. 状态=部分实现 | 条款=`GET /documents/{document_id}/chunks` | 参考行=99 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
35. 状态=部分实现 | 条款=`POST /retrieval/query` | 参考行=103 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
36. 状态=部分实现 | 条款=`POST /retrieval/preview` | 参考行=104 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
37. 状态=部分实现 | 条款=`POST /evaluations` -> `202 + job_id` | 参考行=108 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
38. 状态=部分实现 | 条款=`GET /evaluations/{evaluation_id}`（规划，未纳入当前 v1 契约子集） | 参考行=109 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
39. 状态=部分实现 | 条款=`GET /evaluations/{evaluation_id}/report` | 参考行=110 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
40. 状态=部分实现 | 条款=`POST /evaluations/{evaluation_id}/resume` -> `202 + job_id` | 参考行=111 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
41. 状态=部分实现 | 条款=`GET /jobs/{job_id}` | 参考行=115 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
42. 状态=部分实现 | 条款=`GET /jobs`（支持查询参数：`status/type/cursor`） | 参考行=116 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
43. 状态=部分实现 | 条款=`POST /jobs/{job_id}/cancel` | 参考行=117 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
44. 状态=部分实现 | 条款=`GET /dlq/items` | 参考行=121 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
45. 状态=部分实现 | 条款=`POST /dlq/items/{item_id}/requeue` | 参考行=122 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
46. 状态=部分实现 | 条款=`POST /dlq/items/{item_id}/discard` | 参考行=123 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
47. 状态=部分实现 | 条款=`GET /citations/{chunk_id}/source` | 参考行=127 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
48. 状态=部分实现 | 条款=`POST /internal/quality-gates/evaluate` | 参考行=133 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
49. 状态=部分实现 | 条款=`POST /internal/performance-gates/evaluate` | 参考行=134 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
50. 状态=部分实现 | 条款=`POST /internal/security-gates/evaluate` | 参考行=135 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
51. 状态=部分实现 | 条款=`POST /internal/cost-gates/evaluate` | 参考行=136 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
52. 状态=部分实现 | 条款=仅内部调试与门禁流水线使用，必须携带 `x-internal-debug: true`。 | 参考行=140 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
53. 状态=部分实现 | 条款=质量门禁输入 RAGAS/DeepEval/citation 指标，返回通过/阻断结论。 | 参考行=141 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
54. 状态=部分实现 | 条款=性能门禁输入 P95、队列稳定性与缓存命中率指标。 | 参考行=142 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
55. 状态=部分实现 | 条款=安全门禁输入越权/绕过/审批/脱敏/密钥扫描结果。 | 参考行=143 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
56. 状态=部分实现 | 条款=成本门禁输入成本 P95、模型降级可用性与预算告警覆盖率。 | 参考行=144 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
57. 状态=部分实现 | 条款=当质量门禁不达标时，触发 `RAGChecker` 诊断流程标记。 | 参考行=145 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
58. 状态=部分实现 | 条款=`POST /internal/release/rollout/plan` | 参考行=149 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
59. 状态=部分实现 | 条款=`POST /internal/release/rollout/decision` | 参考行=150 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
60. 状态=部分实现 | 条款=`POST /internal/release/rollback/execute` | 参考行=151 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
61. 状态=部分实现 | 条款=`POST /internal/release/replay/e2e` | 参考行=152 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
62. 状态=部分实现 | 条款=`POST /internal/release/readiness/evaluate` | 参考行=153 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
63. 状态=部分实现 | 条款=`POST /internal/release/pipeline/execute` | 参考行=154 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
64. 状态=部分实现 | 条款=仅灰度/回滚流水线使用，必须携带 `x-internal-debug: true`。 | 参考行=158 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
65. 状态=部分实现 | 条款=灰度放量顺序固定为“租户白名单 -> 项目规模分层（small/medium/large）”。 | 参考行=159 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
66. 状态=部分实现 | 条款=`high_risk=true` 时强制 `force_hitl=true`，不可绕过。 | 参考行=160 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
67. 状态=部分实现 | 条款=回滚触发条件为“任一门禁连续超阈值（默认阈值 2 次）”。 | 参考行=161 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
68. 状态=部分实现 | 条款=回滚执行顺序固定为：`model_config -> retrieval_params -> workflow_version -> release_version`。 | 参考行=162 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
69. 状态=部分实现 | 条款=回滚执行后必须触发一次 `replay verification`。 | 参考行=163 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
70. 状态=部分实现 | 条款=`replay/e2e` 会执行上传、解析、评估与（可选）自动恢复，产出 `passed`。 | 参考行=164 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
71. 状态=部分实现 | 条款=`readiness/evaluate` 汇总 Gate D/E/F 与 replay 结果，给出发布准入结论。 | 参考行=165 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
72. 状态=部分实现 | 条款=`pipeline/execute` 将 readiness 与 canary/rollback 配置收口为单次发布决策输出。 | 参考行=166 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
73. 状态=部分实现 | 条款=`GET /internal/ops/metrics/summary` | 参考行=170 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
74. 状态=部分实现 | 条款=`POST /internal/ops/data-feedback/run` | 参考行=171 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
75. 状态=部分实现 | 条款=`POST /internal/ops/strategy-tuning/apply` | 参考行=172 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
76. 状态=部分实现 | 条款=仅运维优化流水线使用，必须携带 `x-internal-debug: true`。 | 参考行=176 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
77. 状态=部分实现 | 条款=数据回流会将 DLQ 样本写入反例集，并将人审改判样本写入黄金集候选。 | 参考行=177 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
78. 状态=部分实现 | 条款=每次回流执行都必须产出新的评估数据集版本号。 | 参考行=178 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
79. 状态=部分实现 | 条款=策略优化同步更新 selector 阈值、评分校准参数、工具权限审批策略。 | 参考行=179 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
80. 状态=部分实现 | 条款=metrics summary 按租户聚合 API/Worker/Quality/Cost/SLO 指标视图。 | 参考行=180 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
81. 状态=部分实现 | 条款=`GET /internal/audit/integrity` | 参考行=184 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
82. 状态=部分实现 | 条款=`POST /internal/legal-hold/impose` | 参考行=185 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
83. 状态=部分实现 | 条款=`GET /internal/legal-hold/items` | 参考行=186 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
84. 状态=部分实现 | 条款=`POST /internal/legal-hold/{hold_id}/release` | 参考行=187 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
85. 状态=部分实现 | 条款=`POST /internal/storage/cleanup` | 参考行=188 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
86. 状态=部分实现 | 条款=仅内部治理流程使用，必须携带 `x-internal-debug: true`。 | 参考行=192 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
87. 状态=部分实现 | 条款=`legal-hold/release` 必须满足双人复核与必填 reason。 | 参考行=193 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
88. 状态=部分实现 | 条款=`storage/cleanup` 对被 hold 对象返回 `409 LEGAL_HOLD_ACTIVE`。 | 参考行=194 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
89. 状态=部分实现 | 条款=`storage/cleanup` 对有 retention 的对象返回 `409 RETENTION_ACTIVE`。 | 参考行=195 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
90. 状态=部分实现 | 条款=审计完整性校验失败返回 `409 AUDIT_INTEGRITY_BROKEN`。 | 参考行=196 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
91. 状态=部分实现 | 条款=`GET /internal/outbox/events` | 参考行=200 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
92. 状态=部分实现 | 条款=`POST /internal/outbox/events/{event_id}/publish` | 参考行=201 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
93. 状态=部分实现 | 条款=`POST /internal/outbox/relay` | 参考行=202 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
94. 状态=部分实现 | 条款=`POST /internal/queue/{queue_name}/enqueue` | 参考行=203 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
95. 状态=部分实现 | 条款=`POST /internal/queue/{queue_name}/dequeue` | 参考行=204 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
96. 状态=部分实现 | 条款=`POST /internal/queue/{queue_name}/ack` | 参考行=205 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
97. 状态=部分实现 | 条款=`POST /internal/queue/{queue_name}/nack` | 参考行=206 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
98. 状态=部分实现 | 条款=仅内部链路联调使用，必须携带 `x-internal-debug: true`。 | 参考行=210 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
99. 状态=部分实现 | 条款=`relay` 会将 `pending` outbox 事件转为队列消息，并标记为 `published`。 | 参考行=211 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
100. 状态=部分实现 | 条款=队列消息最小字段：`event_id/job_id/tenant_id/trace_id/job_type/attempt`。 | 参考行=212 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
101. 状态=部分实现 | 条款=队列消费保持租户隔离，跨租户不可见。 | 参考行=213 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
102. 状态=部分实现 | 条款=`GET /internal/workflows/{thread_id}/checkpoints` | 参考行=217 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
103. 状态=部分实现 | 条款=`POST /internal/worker/queues/{queue_name}/drain-once` | 参考行=218 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
104. 状态=部分实现 | 条款=仅内部联调使用，必须携带 `x-internal-debug: true`。 | 参考行=222 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
105. 状态=部分实现 | 条款=checkpoint 查询按 `thread_id + tenant_id` 过滤。 | 参考行=223 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
106. 状态=部分实现 | 条款=`thread_id` 由任务创建时分配，并在 resume 任务中复用。 | 参考行=224 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
107. 状态=部分实现 | 条款=`drain-once` 每次最多消费 `max_messages` 条消息并驱动对应 job 执行。 | 参考行=225 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
108. 状态=部分实现 | 条款=当任务进入 `retrying` 时，worker 按指数退避结果执行延迟重投（`nack(delay_ms)`）。 | 参考行=226 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
109. 状态=部分实现 | 条款=`Authorization: Bearer <access_token>` | 参考行=234 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
110. 状态=部分实现 | 条款=`Idempotency-Key: idem_xxx` | 参考行=235 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
111. 状态=部分实现 | 条款=`Content-Type: multipart/form-data` | 参考行=236 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
112. 状态=部分实现 | 条款=`project_id`（string, required） | 参考行=240 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
113. 状态=部分实现 | 条款=`supplier_id`（string, required） | 参考行=241 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
114. 状态=部分实现 | 条款=`doc_type`（enum: `tender|bid|attachment`, required） | 参考行=242 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
115. 状态=部分实现 | 条款=`file`（binary, required） | 参考行=243 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
116. 状态=部分实现 | 条款=`data.job_id` 对应自动投递的 parse 任务，可直接用于 `GET /jobs/{job_id}` 查询。 | 参考行=265 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
117. 状态=部分实现 | 条款=上传受理后文档状态进入 `parse_queued`。 | 参考行=266 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
118. 状态=部分实现 | 条款=`REQ_VALIDATION_FAILED` | 参考行=270 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
119. 状态=部分实现 | 条款=`IDEMPOTENCY_CONFLICT` | 参考行=271 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
120. 状态=部分实现 | 条款=`TENANT_SCOPE_VIOLATION` | 参考行=272 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
121. 状态=部分实现 | 条款=`Authorization: Bearer <access_token>` | 参考行=278 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
122. 状态=部分实现 | 条款=`Idempotency-Key: idem_xxx` | 参考行=279 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
123. 状态=部分实现 | 条款=`Content-Type: application/json` | 参考行=280 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
124. 状态=部分实现 | 条款=评分流程先执行规则引擎硬约束判定。 | 参考行=318 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
125. 状态=部分实现 | 条款=当硬约束不通过时，报告返回 `criteria_results[*].hard_pass=false`，并阻断软评分（总分为 `0`，风险等级提升）。 | 参考行=319 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
126. 状态=部分实现 | 条款=`WF_INTERRUPT_RESUME_INVALID` | 参考行=382 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
127. 状态=部分实现 | 条款=`REQ_VALIDATION_FAILED` | 参考行=383 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
128. 状态=部分实现 | 条款=`WF_INTERRUPT_REVIEWER_REQUIRED` | 参考行=384 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
129. 状态=部分实现 | 条款=`resume_token` 单次有效。 | 参考行=388 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
130. 状态=部分实现 | 条款=`resume_token` 自签发起 24 小时内有效，超时后返回 `WF_INTERRUPT_RESUME_INVALID`。 | 参考行=389 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
131. 状态=部分实现 | 条款=`REQ_VALIDATION_FAILED` | 参考行=596 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
132. 状态=部分实现 | 条款=`TENANT_SCOPE_VIOLATION` | 参考行=597 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
133. 状态=部分实现 | 条款=rerank 降级时 `data.degraded=true`，并回退到原召回分排序 | 参考行=598 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
134. 状态=部分实现 | 条款=rerank 降级原因通过 `data.degrade_reason` 返回（例如 `rerank_failed`/`rerank_disabled`） | 参考行=599 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
135. 状态=部分实现 | 条款=若租户不在白名单，`admitted=false` 且 `reasons` 含 `TENANT_NOT_IN_WHITELIST`。 | 参考行=772 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
136. 状态=部分实现 | 条款=若项目规模未放量，`admitted=false` 且 `reasons` 含 `PROJECT_SIZE_NOT_ENABLED`。 | 参考行=773 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
137. 状态=部分实现 | 条款=若 `high_risk=true`，无条件返回 `force_hitl=true`。 | 参考行=774 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
138. 状态=部分实现 | 条款=当且仅当存在 `consecutive_failures >= consecutive_threshold` 的 breach 时触发回滚。 | 参考行=825 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
139. 状态=部分实现 | 条款=回滚完成后必须创建并执行一次回放验证任务。 | 参考行=826 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
140. 状态=部分实现 | 条款=`rollback_completed_within_30m=false` 视为 Gate E 验收失败。 | 参考行=827 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
141. 状态=部分实现 | 条款=仅内部发布准入验证使用，必须携带 `x-internal-debug: true`。 | 参考行=873 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
142. 状态=部分实现 | 条款=`force_hitl=true` 时会尝试按 `decision` 自动提交恢复动作。 | 参考行=874 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
143. 状态=部分实现 | 条款=`passed` 仅在 parse 成功且评估链路满足通过条件时为 `true`。 | 参考行=875 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
144. 状态=部分实现 | 条款=仅内部发布准入流水线使用，必须携带 `x-internal-debug: true`。 | 参考行=927 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
145. 状态=部分实现 | 条款=任一门禁为 `false` 或 `replay_passed=false`，都必须阻断发布（`admitted=false`）。 | 参考行=928 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
146. 状态=部分实现 | 条款=`failed_checks` 必须给出可审计的失败原因列表。 | 参考行=929 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
147. 状态=部分实现 | 条款=仅内部发布流水线使用，必须携带 `x-internal-debug: true`。 | 参考行=981 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
148. 状态=部分实现 | 条款=当 `readiness_required=true` 时，会先执行 readiness 判定；不通过则 `stage=release_blocked`。 | 参考行=982 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
149. 状态=部分实现 | 条款=输出中的 canary/rollback 字段来自运行时配置，用于后续自动化步骤执行。 | 参考行=983 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
150. 状态=部分实现 | 条款=`dlq_ids` 为空时按当前租户全量 DLQ 样本回流。 | 参考行=1018 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
151. 状态=部分实现 | 条款=仅 `resume_submitted` 且 `decision in {reject, edit_scores}` 的审计样本计入黄金集候选。 | 参考行=1019 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
152. 状态=部分实现 | 条款=`dataset_version_after` 必须不同于 `dataset_version_before`。 | 参考行=1020 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
153. 状态=部分实现 | 条款=每次策略变更必须生成新 `strategy_version`。 | 参考行=1073 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
154. 状态=部分实现 | 条款=高风险动作审批策略变更必须体现在 `tool_policy` 字段返回值中。 | 参考行=1074 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
155. 状态=部分实现 | 条款=`queue_name`（query，可选，默认 `jobs`） | 参考行=1080 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
156. 状态=部分实现 | 条款=`consumer_name`（query，可选，默认 `default`） | 参考行=1081 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
157. 状态=部分实现 | 条款=`limit`（query，可选，默认 `100`，范围 `1..1000`） | 参考行=1082 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
158. 状态=部分实现 | 条款=仅消费当前租户 `status=pending` 的 outbox 事件。 | 参考行=1103 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
159. 状态=部分实现 | 条款=成功入队后事件必须原子标记为 `published`。 | 参考行=1104 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
160. 状态=部分实现 | 条款=同一 `consumer_name` 对同一 `event_id` 重复 relay 不得重复入队（幂等键：`event_id + consumer_name`）。 | 参考行=1105 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
161. 状态=部分实现 | 条款=不同 `consumer_name` 可对同一事件各消费一次。 | 参考行=1106 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
162. 状态=部分实现 | 条款=`ack/nack` 仅允许操作本租户 inflight 消息。 | 参考行=1163 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
163. 状态=部分实现 | 条款=跨租户操作返回 `403 + TENANT_SCOPE_VIOLATION`。 | 参考行=1164 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
164. 状态=部分实现 | 条款=`thread_id`（path，必填） | 参考行=1170 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
165. 状态=部分实现 | 条款=`limit`（query，可选，默认 `100`，范围 `1..1000`） | 参考行=1171 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
166. 状态=部分实现 | 条款=`queue_name`（query，可选，默认 `jobs`） | 参考行=1207 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
167. 状态=部分实现 | 条款=`queue_name`（path，必填） | 参考行=1256 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
168. 状态=部分实现 | 条款=`max_messages`（query，可选，默认 `1`，范围 `1..100`） | 参考行=1257 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
169. 状态=部分实现 | 条款=`force_fail`（query，可选，默认 `false`） | 参考行=1258 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
170. 状态=部分实现 | 条款=`transient_fail`（query，可选，默认 `false`） | 参考行=1259 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
171. 状态=部分实现 | 条款=`error_code`（query，可选） | 参考行=1260 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
172. 状态=部分实现 | 条款=`requeue/discard` 成功后必须写审计日志。 | 参考行=1348 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
173. 状态=部分实现 | 条款=审计动作分别为 `dlq_requeue_submitted`、`dlq_discard_submitted`。 | 参考行=1349 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
174. 状态=部分实现 | 条款=`Idempotency-Key` 有效期 24h。 | 参考行=1355 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
175. 状态=部分实现 | 条款=同 key + 同 body 返回同结果。 | 参考行=1356 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
176. 状态=部分实现 | 条款=同 key + 异 body 返回 `409 IDEMPOTENCY_CONFLICT`。 | 参考行=1357 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
177. 状态=部分实现 | 条款=列表接口统一 cursor 分页：`cursor/limit`。 | 参考行=1361 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
178. 状态=部分实现 | 条款=默认 `limit=20`，最大 `limit=100`。 | 参考行=1362 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
179. 状态=部分实现 | 条款=必须支持 `created_at` 倒序。 | 参考行=1363 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
180. 状态=部分实现 | 条款=`AUTH_*`：认证鉴权 | 参考行=1367 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
181. 状态=部分实现 | 条款=`REQ_*`：请求验证 | 参考行=1368 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
182. 状态=部分实现 | 条款=`TENANT_*`：租户隔离 | 参考行=1369 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
183. 状态=部分实现 | 条款=`WF_*`：工作流与状态机 | 参考行=1370 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
184. 状态=部分实现 | 条款=`DLQ_*`：死信与运维 | 参考行=1371 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
185. 状态=部分实现 | 条款=`UPSTREAM_*`：上游依赖 | 参考行=1372 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
186. 状态=部分实现 | 条款=禁止客户端传 `tenant_id`。 | 参考行=1376 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
187. 状态=部分实现 | 条款=高风险接口强制二次确认信息。 | 参考行=1377 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
188. 状态=部分实现 | 条款=生产环境不返回堆栈。 | 参考行=1378 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
189. 状态=部分实现 | 条款=所有敏感接口写审计日志。 | 参考行=1379 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
190. 状态=部分实现 | 条款=所有接口必须声明 request/response schema。 | 参考行=1383 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
191. 状态=部分实现 | 条款=破坏性变更必须升级 minor 版本并提供迁移说明。 | 参考行=1384 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
192. 状态=部分实现 | 条款=废弃接口保留至少一个发布周期。 | 参考行=1385 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
193. 状态=部分实现 | 条款=OpenAPI 基线文件：`docs/design/2026-02-21-openapi-v1.yaml`。 | 参考行=1386 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
194. 状态=部分实现 | 条款=契约测试样例：`docs/design/2026-02-21-api-contract-test-samples.md`。 | 参考行=1387 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
195. 状态=部分实现 | 条款=任何接口字段变更必须同步更新上述两个文件。 | 参考行=1388 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
196. 状态=部分实现 | 条款=核心接口契约测试通过。 | 参考行=1392 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
197. 状态=部分实现 | 条款=异步接口状态流转正确。 | 参考行=1393 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
198. 状态=部分实现 | 条款=幂等冲突与重放行为符合规范。 | 参考行=1394 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
199. 状态=部分实现 | 条款=所有错误响应包含 `trace_id`。 | 参考行=1395 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
200. 状态=部分实现 | 条款=FastAPI docs: https://fastapi.tiangolo.com/ | 参考行=1399 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml
201. 状态=部分实现 | 条款=历史融合提交：`beef3e9`, `7f05f7e` | 参考行=1400 | 证据: app/main.py; docs/design/2026-02-21-openapi-v1.yaml

**文件：docs/design/2026-02-21-retrieval-and-scoring-spec.md**
文件级结论：部分实现 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
1. 状态=部分实现 | 条款=检索链路可复现、可解释、可审计。 | 参考行=9 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
2. 状态=部分实现 | 条款=评分链路可追溯、可复核、可校准。 | 参考行=10 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
3. 状态=部分实现 | 条款=规则引擎与 LLM 分工清晰，避免黑盒决策。 | 参考行=11 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
4. 状态=部分实现 | 条款=输出必须带证据引用，支持原文回跳。 | 参考行=12 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
5. 状态=部分实现 | 条款=全半角、大小写、空白归一。 | 参考行=36 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
6. 状态=部分实现 | 条款=术语同义映射（项目词典）。 | 参考行=37 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
7. 状态=部分实现 | 条款=数值/时间/金额标准化。 | 参考行=38 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
8. 状态=部分实现 | 条款=query_type 判定：`fact/relation/comparison/summary/risk`。 | 参考行=39 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
9. 状态=部分实现 | 条款=`entity_constraints` | 参考行=45 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
10. 状态=部分实现 | 条款=`numeric_constraints` | 参考行=46 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
11. 状态=部分实现 | 条款=`time_constraints` | 参考行=47 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
12. 状态=部分实现 | 条款=`must_include_terms` | 参考行=48 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
13. 状态=部分实现 | 条款=`must_exclude_terms` | 参考行=49 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
14. 状态=部分实现 | 条款=`rewritten_query` | 参考行=58 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
15. 状态=部分实现 | 条款=`rewrite_reason` | 参考行=59 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
16. 状态=部分实现 | 条款=`constraints_preserved=true` | 参考行=60 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
17. 状态=部分实现 | 条款=`constraint_diff=[]` | 参考行=61 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
18. 状态=部分实现 | 条款=`top_k=60` | 参考行=77 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
19. 状态=部分实现 | 条款=`chunk_top_k=20` | 参考行=78 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
20. 状态=部分实现 | 条款=`include_references=true` | 参考行=79 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
21. 状态=部分实现 | 条款=`enable_rerank=true` | 参考行=80 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
22. 状态=部分实现 | 条款=`max_entity_tokens=6000` | 参考行=81 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
23. 状态=部分实现 | 条款=`max_relation_tokens=8000` | 参考行=82 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
24. 状态=部分实现 | 条款=无法分类时使用 `hybrid`。 | 参考行=86 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
25. 状态=部分实现 | 条款=高风险任务强制 `mix`。 | 参考行=87 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
26. 状态=部分实现 | 条款=任何模式都必须启用租户过滤。 | 参考行=88 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
27. 状态=部分实现 | 条款=LightRAG 主召回。 | 参考行=94 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
28. 状态=部分实现 | 条款=SQL 白名单支路（结构化字段）。 | 参考行=95 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
29. 状态=部分实现 | 条款=合并去重后进入 rerank。 | 参考行=96 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
30. 状态=部分实现 | 条款=`supplier_code` | 参考行=108 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
31. 状态=部分实现 | 条款=`qualification_level` | 参考行=109 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
32. 状态=部分实现 | 条款=`registered_capital` | 参考行=110 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
33. 状态=部分实现 | 条款=`bid_price` | 参考行=111 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
34. 状态=部分实现 | 条款=`delivery_period` | 参考行=112 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
35. 状态=部分实现 | 条款=`warranty_period` | 参考行=113 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
36. 状态=部分实现 | 条款=任意 SQL 拼接。 | 参考行=117 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
37. 状态=部分实现 | 条款=跨租户 JOIN。 | 参考行=118 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
38. 状态=部分实现 | 条款=绕过 API 层租户过滤。 | 参考行=119 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
39. 状态=部分实现 | 条款=`chunk_id` | 参考行=127 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
40. 状态=部分实现 | 条款=`score_raw` | 参考行=128 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
41. 状态=部分实现 | 条款=`score_rerank` | 参考行=129 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
42. 状态=部分实现 | 条款=`reason` | 参考行=130 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
43. 状态=部分实现 | 条款=`metadata` | 参考行=131 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
44. 状态=部分实现 | 条款=按评分项分别打包证据。 | 参考行=137 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
45. 状态=部分实现 | 条款=每项最少 2 条证据，最多 8 条证据。 | 参考行=138 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
46. 状态=部分实现 | 条款=证据优先级：高相关 + 高置信 + 多样来源。 | 参考行=139 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
47. 状态=部分实现 | 条款=单项评分上下文 `<= 6k tokens`。 | 参考行=143 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
48. 状态=部分实现 | 条款=全报告上下文 `<= 24k tokens`。 | 参考行=144 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
49. 状态=部分实现 | 条款=超预算按“低相关 -> 冗余来源”顺序裁剪。 | 参考行=145 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
50. 状态=部分实现 | 条款=rerank 超时：降级到召回分排序。 | 参考行=149 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
51. 状态=部分实现 | 条款=rerank 异常：记录降级事件，不中断主流程。 | 参考行=150 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
52. 状态=部分实现 | 条款=降级比例超阈值触发告警。 | 参考行=151 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
53. 状态=部分实现 | 条款=合规红线判定（是否一票否决）。 | 参考行=157 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
54. 状态=部分实现 | 条款=明确公式项计算（价格分、交付分）。 | 参考行=158 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
55. 状态=部分实现 | 条款=缺失关键材料判定。 | 参考行=159 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
56. 状态=部分实现 | 条款=语义匹配评分。 | 参考行=163 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
57. 状态=部分实现 | 条款=方案可行性分析。 | 参考行=164 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
58. 状态=部分实现 | 条款=风险说明与建议。 | 参考行=165 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
59. 状态=部分实现 | 条款=LLM 不得覆盖规则引擎红线结论。 | 参考行=169 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
60. 状态=部分实现 | 条款=LLM 每条 claim 必须关联 citation。 | 参考行=170 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
61. 状态=部分实现 | 条款=`criteria_id` | 参考行=178 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
62. 状态=部分实现 | 条款=`score` | 参考行=179 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
63. 状态=部分实现 | 条款=`max_score` | 参考行=180 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
64. 状态=部分实现 | 条款=`hard_pass` | 参考行=181 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
65. 状态=部分实现 | 条款=`reason` | 参考行=182 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
66. 状态=部分实现 | 条款=`citations[]` | 参考行=183 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
67. 状态=部分实现 | 条款=`confidence` | 参考行=184 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
68. 状态=部分实现 | 条款=同样本多次评估波动超过阈值触发校准。 | 参考行=200 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
69. 状态=部分实现 | 条款=校准过程记录 anchor 样本与校准参数。 | 参考行=201 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
70. 状态=部分实现 | 条款=`confidence < 0.65` | 参考行=207 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
71. 状态=部分实现 | 条款=`citation_coverage < 0.90` | 参考行=208 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
72. 状态=部分实现 | 条款=`score_deviation_pct > 20%` | 参考行=209 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
73. 状态=部分实现 | 条款=红线项判定冲突 | 参考行=210 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
74. 状态=部分实现 | 条款=人工强制复核标记 | 参考行=211 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
75. 状态=部分实现 | 条款=`claim -> citation` 一一映射校验。 | 参考行=215 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
76. 状态=部分实现 | 条款=citation 必须可解析到 `chunk_id/page/bbox`。 | 参考行=216 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
77. 状态=部分实现 | 条款=无证据 claim 标记为 `unsupported_claim` 并阻断终审建议。 | 参考行=217 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
78. 状态=部分实现 | 条款=RAGAS `precision/recall >= 0.80`。 | 参考行=239 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
79. 状态=部分实现 | 条款=Faithfulness `>= 0.90`。 | 参考行=240 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
80. 状态=部分实现 | 条款=citation 回跳率 `>= 98%`。 | 参考行=241 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
81. 状态=部分实现 | 条款=检索 P95 `<= 4s`。 | 参考行=245 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
82. 状态=部分实现 | 条款=评分 P95 `<= 120s`。 | 参考行=246 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
83. 状态=部分实现 | 条款=幻觉率 `<= 5%`。 | 参考行=247 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
84. 状态=部分实现 | 条款=LightRAG: https://github.com/HKUDS/LightRAG | 参考行=251 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
85. 状态=部分实现 | 条款=RAGAS: https://github.com/explodinggradients/ragas | 参考行=252 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
86. 状态=部分实现 | 条款=RAGChecker: https://github.com/amazon-science/RAGChecker | 参考行=253 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
87. 状态=部分实现 | 条款=DeepEval: https://github.com/confident-ai/deepeval | 参考行=254 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md
88. 状态=部分实现 | 条款=历史融合提交：`7f05f7e`, `53e3d92`, `72a64da` | 参考行=255 | 证据: app/store.py; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md

**文件：docs/design/2026-02-21-security-design.md**
文件级结论：部分实现 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
1. 状态=部分实现 | 条款=零跨租户越权。 | 参考行=9 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
2. 状态=部分实现 | 条款=关键动作全审计可追溯。 | 参考行=10 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
3. 状态=部分实现 | 条款=Agent 工具调用可控且最小权限。 | 参考行=11 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
4. 状态=部分实现 | 条款=证据与报告满足留存与法律保全要求。 | 参考行=12 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
5. 状态=部分实现 | 条款=API 越权与令牌滥用。 | 参考行=16 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
6. 状态=部分实现 | 条款=Worker 丢失租户上下文造成误处理。 | 参考行=17 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
7. 状态=部分实现 | 条款=检索缺少过滤导致跨租户召回。 | 参考行=18 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
8. 状态=部分实现 | 条款=高风险动作绕过审批。 | 参考行=19 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
9. 状态=部分实现 | 条款=Prompt 注入诱导工具越权调用。 | 参考行=20 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
10. 状态=部分实现 | 条款=JWT access token（短时）+ refresh token（HttpOnly Cookie）。 | 参考行=26 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
11. 状态=部分实现 | 条款=refresh 接口启用 CSRF 防护。 | 参考行=27 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
12. 状态=部分实现 | 条款=支持 token 撤销与黑名单。 | 参考行=28 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
13. 状态=部分实现 | 条款=RBAC：`admin/agent/evaluator/viewer`。 | 参考行=32 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
14. 状态=部分实现 | 条款=ABAC：高风险动作附加资源与审批条件。 | 参考行=33 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
15. 状态=部分实现 | 条款=默认拒绝：未显式允许即拒绝。 | 参考行=34 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
16. 状态=部分实现 | 条款=`tenant_id` 只从 JWT 注入。 | 参考行=40 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
17. 状态=部分实现 | 条款=拒绝客户端提交 `tenant_id`。 | 参考行=41 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
18. 状态=部分实现 | 条款=所有资源访问二次校验资源租户归属。 | 参考行=42 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
19. 状态=部分实现 | 条款=核心表全量 `tenant_id` + RLS。 | 参考行=46 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
20. 状态=部分实现 | 条款=会话设置 `app.current_tenant`。 | 参考行=47 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
21. 状态=部分实现 | 条款=无租户上下文查询一律拒绝。 | 参考行=48 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
22. 状态=部分实现 | 条款=向量查询必须附 `tenant_id + project_id` 过滤。 | 参考行=52 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
23. 状态=部分实现 | 条款=无过滤查询直接拒绝并告警。 | 参考行=53 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
24. 状态=部分实现 | 条款=Redis key 强制 tenant 前缀。 | 参考行=57 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
25. 状态=部分实现 | 条款=job payload 强制包含 tenant 上下文。 | 参考行=58 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
26. 状态=部分实现 | 条款=Worker 执行前二次验证 tenant 一致性。 | 参考行=59 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
27. 状态=部分实现 | 条款=工具分级：`read_only/state_write/external_commit`。 | 参考行=63 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
28. 状态=部分实现 | 条款=高风险工具调用必须有人审或双人复核。 | 参考行=64 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
29. 状态=部分实现 | 条款=工具输入做 schema 校验与 allowlist 校验。 | 参考行=65 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
30. 状态=部分实现 | 条款=工具调用结果写审计日志。 | 参考行=66 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
31. 状态=部分实现 | 条款=上下文分层：系统指令 > 业务规则 > 用户输入。 | 参考行=70 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
32. 状态=部分实现 | 条款=对外部文档内容启用“非可信指令”标记。 | 参考行=71 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
33. 状态=部分实现 | 条款=禁止模型根据文档文本直接提升权限。 | 参考行=72 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
34. 状态=部分实现 | 条款=高风险动作必须通过显式工具调用，不接受纯文本隐式提交。 | 参考行=73 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
35. 状态=部分实现 | 条款=传输：TLS 1.2+。 | 参考行=77 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
36. 状态=部分实现 | 条款=存储：数据库、备份、对象存储均加密。 | 参考行=78 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
37. 状态=部分实现 | 条款=密钥：集中管理，定期轮换（90 天）。 | 参考行=79 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
38. 状态=部分实现 | 条款=日志脱敏：证件号、手机号、token、密钥字段脱敏。 | 参考行=80 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
39. 状态=部分实现 | 条款=高风险动作审计覆盖率 100%。 | 参考行=84 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
40. 状态=部分实现 | 条款=审计字段至少含：`actor/action/resource/trace_id/reason`。 | 参考行=85 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
41. 状态=部分实现 | 条款=legal hold 对象禁止自动删除。 | 参考行=86 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
42. 状态=部分实现 | 条款=报告归档进入 WORM 存储。 | 参考行=87 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
43. 状态=部分实现 | 条款=审计日志追加 `prev_hash/audit_hash` 完整性链，支持在线校验。 | 参考行=88 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
44. 状态=部分实现 | 条款=`dlq_discard` | 参考行=92 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
45. 状态=部分实现 | 条款=`legal_hold_release` | 参考行=93 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
46. 状态=部分实现 | 条款=其他动作可通过配置提升到双人复核（如 `strategy_tuning_apply`）。 | 参考行=94 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
47. 状态=部分实现 | 条款=租户越权测试（API + DB + retrieval）。 | 参考行=98 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
48. 状态=部分实现 | 条款=权限绕过测试（角色与审批链）。 | 参考行=99 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
49. 状态=部分实现 | 条款=token 重放与失效测试。 | 参考行=100 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
50. 状态=部分实现 | 条款=Prompt 注入回归测试。 | 参考行=101 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
51. 状态=部分实现 | 条款=发现越权风险立即触发 P0：关闭相关写接口。 | 参考行=105 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
52. 状态=部分实现 | 条款=开启只读降级保障可查询能力。 | 参考行=106 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
53. 状态=部分实现 | 条款=恢复前必须完成根因分析与补丁验证。 | 参考行=107 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
54. 状态=部分实现 | 条款=跨租户访问事件为 0。 | 参考行=111 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
55. 状态=部分实现 | 条款=高风险动作无审计缺口。 | 参考行=112 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
56. 状态=部分实现 | 条款=legal hold 对象无违规删除。 | 参考行=113 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
57. 状态=部分实现 | 条款=安全回归全通过。 | 参考行=114 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
58. 状态=部分实现 | 条款=FastAPI security docs: https://fastapi.tiangolo.com/ | 参考行=118 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
59. 状态=部分实现 | 条款=OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/ | 参考行=119 | 证据: app/main.py; app/security.py; docs/ops/2026-02-23-security-multitenancy-evidence.md

**文件：docs/design/2026-02-21-testing-strategy.md**
文件级结论：部分实现 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
1. 状态=部分实现 | 条款=保证主链路端到端稳定可运行。 | 参考行=9 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=部分实现 | 条款=保证多租户隔离不可绕过。 | 参考行=10 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
3. 状态=部分实现 | 条款=保证评分输出可追溯、可复核。 | 参考行=11 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
4. 状态=部分实现 | 条款=保证失败恢复、DLQ 流程可执行。 | 参考行=12 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
5. 状态=部分实现 | 条款=规则引擎判定器。 | 参考行=20 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
6. 状态=部分实现 | 条款=检索模式选择器。 | 参考行=21 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=部分实现 | 条款=评分与置信度计算器。 | 参考行=22 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=部分实现 | 条款=错误分类与重试决策。 | 参考行=23 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
9. 状态=部分实现 | 条款=bbox 归一化与引用映射。 | 参考行=24 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
10. 状态=部分实现 | 条款=API + DB + Queue。 | 参考行=30 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
11. 状态=部分实现 | 条款=解析链路（MinerU/Docling/fallback）。 | 参考行=31 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
12. 状态=部分实现 | 条款=检索链路（LightRAG + SQL 支路 + rerank）。 | 参考行=32 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
13. 状态=部分实现 | 条款=LangGraph 中断恢复与 checkpoint。 | 参考行=33 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
14. 状态=部分实现 | 条款=DLQ 子流程。 | 参考行=34 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
15. 状态=部分实现 | 条款=RAGAS: | 参考行=66 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
16. 状态=部分实现 | 条款=DeepEval: | 参考行=71 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
17. 状态=部分实现 | 条款=引用可回跳率 >= 98% | 参考行=73 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
18. 状态=部分实现 | 条款=P1：RAGChecker 输出 retriever/generator 诊断报告 | 参考行=74 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
19. 状态=部分实现 | 条款=黄金集：稳定基准。 | 参考行=78 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
20. 状态=部分实现 | 条款=反例集：冲突信息、诱导幻觉、证据缺失。 | 参考行=79 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
21. 状态=部分实现 | 条款=漂移集：新版模板、扫描噪声、版式变化。 | 参考行=80 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
22. 状态=部分实现 | 条款=回流集：线上失败与人工改判样本。 | 参考行=81 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
23. 状态=部分实现 | 条款=API P95 <= 1.5s。 | 参考行=85 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
24. 状态=部分实现 | 条款=检索 P95 <= 4.0s。 | 参考行=86 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
25. 状态=部分实现 | 条款=50 页解析 P95 <= 180s。 | 参考行=87 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
26. 状态=部分实现 | 条款=评估 P95 <= 120s。 | 参考行=88 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
27. 状态=部分实现 | 条款=并发场景下 DLQ 率 <= 1%（日均）。 | 参考行=89 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
28. 状态=部分实现 | 条款=租户越权访问测试（API/DB/retrieval）。 | 参考行=93 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
29. 状态=部分实现 | 条款=角色权限绕过测试。 | 参考行=94 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
30. 状态=部分实现 | 条款=token 重放与失效测试。 | 参考行=95 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
31. 状态=部分实现 | 条款=Prompt 注入与工具越权测试。 | 参考行=96 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
32. 状态=部分实现 | 条款=上游模型超时注入。 | 参考行=100 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
33. 状态=部分实现 | 条款=rerank 服务不可用注入。 | 参考行=101 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
34. 状态=部分实现 | 条款=队列堆积与重试风暴注入。 | 参考行=102 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
35. 状态=部分实现 | 条款=checkpoint 存储异常注入。 | 参考行=103 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
36. 状态=部分实现 | 条款=上传与状态追踪。 | 参考行=109 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
37. 状态=部分实现 | 条款=评估页点对点表格与引用联动。 | 参考行=110 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
38. 状态=部分实现 | 条款=PDF 页码跳转与 bbox 高亮。 | 参考行=111 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
39. 状态=部分实现 | 条款=HITL 提交与恢复闭环。 | 参考行=112 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
40. 状态=部分实现 | 条款=DLQ requeue/discard 受控流程。 | 参考行=113 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
41. 状态=部分实现 | 条款=每次变更至少运行：单元 + 核心集成 + E2E 冒烟。 | 参考行=117 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
42. 状态=部分实现 | 条款=触发门禁时运行：全量离线评估 + 压测 + 安全回归。 | 参考行=118 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
43. 状态=部分实现 | 条款=失败测试必须记录根因并补齐回归用例。 | 参考行=119 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
44. 状态=部分实现 | 条款=质量指标低于阈值。 | 参考行=125 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
45. 状态=部分实现 | 条款=跨租户越权。 | 参考行=126 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
46. 状态=部分实现 | 条款=性能 P95 超阈值且无可接受降级策略。 | 参考行=127 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
47. 状态=部分实现 | 条款=高风险动作审计缺失。 | 参考行=128 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
48. 状态=部分实现 | 条款=四门禁报告可复核。 | 参考行=132 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
49. 状态=部分实现 | 条款=关键路径回归稳定。 | 参考行=133 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
50. 状态=部分实现 | 条款=失败样本可定位并可复现。 | 参考行=134 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
51. 状态=部分实现 | 条款=RAGAS: https://github.com/explodinggradients/ragas | 参考行=138 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
52. 状态=部分实现 | 条款=RAGChecker: https://github.com/amazon-science/RAGChecker | 参考行=139 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
53. 状态=部分实现 | 条款=DeepEval: https://github.com/confident-ai/deepeval | 参考行=140 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
54. 状态=部分实现 | 条款=历史融合提交：`53e3d92`, `7f05f7e` | 参考行=141 | 证据: tests/*; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/design/2026-02-22-gate-d-four-gates-checklist.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
1. 状态=已实现 | 条款=为 Gate D（D-1~D-4）提供统一、可复核的运行证据。 | 参考行=9 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=已实现 | 条款=将质量/性能/安全/成本门禁阈值与接口契约绑定。 | 参考行=10 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
3. 状态=已实现 | 条款=明确“通过/阻断”判定标准与失败码。 | 参考行=11 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
4. 状态=已实现 | 条款=`context_precision >= 0.80` | 参考行=19 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
5. 状态=已实现 | 条款=`context_recall >= 0.80` | 参考行=20 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
6. 状态=已实现 | 条款=`faithfulness >= 0.90` | 参考行=21 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=已实现 | 条款=`response_relevancy >= 0.85` | 参考行=22 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=已实现 | 条款=`hallucination_rate <= 0.05` | 参考行=23 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
9. 状态=已实现 | 条款=`citation_resolvable_rate >= 0.98` | 参考行=24 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
10. 状态=已实现 | 条款=任一阈值不达标时 `passed=false` | 参考行=28 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
11. 状态=已实现 | 条款=触发 `ragchecker.triggered=true` | 参考行=29 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
12. 状态=已实现 | 条款=`api_p95_s <= 1.5` | 参考行=39 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
13. 状态=已实现 | 条款=`retrieval_p95_s <= 4.0` | 参考行=40 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
14. 状态=已实现 | 条款=`parse_50p_p95_s <= 180.0` | 参考行=41 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
15. 状态=已实现 | 条款=`evaluation_p95_s <= 120.0` | 参考行=42 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
16. 状态=已实现 | 条款=`queue_dlq_rate <= 0.01` | 参考行=43 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
17. 状态=已实现 | 条款=`cache_hit_rate >= 0.70` | 参考行=44 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
18. 状态=已实现 | 条款=任一指标越界时 `passed=false` | 参考行=48 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
19. 状态=已实现 | 条款=返回失败码（如 `API_P95_EXCEEDED`） | 参考行=49 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
20. 状态=已实现 | 条款=`tenant_scope_violations == 0` | 参考行=59 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
21. 状态=已实现 | 条款=`auth_bypass_findings == 0` | 参考行=60 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
22. 状态=已实现 | 条款=`high_risk_approval_coverage == 1.0` | 参考行=61 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
23. 状态=已实现 | 条款=`log_redaction_failures == 0` | 参考行=62 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
24. 状态=已实现 | 条款=`secret_scan_findings == 0` | 参考行=63 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
25. 状态=已实现 | 条款=任一阻断项失败时 `passed=false` | 参考行=67 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
26. 状态=已实现 | 条款=返回失败码（如 `TENANT_SCOPE_VIOLATION_FOUND`） | 参考行=68 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
27. 状态=已实现 | 条款=`task_cost_p95 / baseline_task_cost_p95 <= 1.2` | 参考行=78 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
28. 状态=已实现 | 条款=`routing_degrade_passed == true` | 参考行=79 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
29. 状态=已实现 | 条款=`degrade_availability >= 0.995` | 参考行=80 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
30. 状态=已实现 | 条款=`budget_alert_coverage == 1.0` | 参考行=81 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
31. 状态=已实现 | 条款=任一条件不满足时 `passed=false` | 参考行=85 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
32. 状态=已实现 | 条款=返回失败码（如 `TASK_COST_P95_RATIO_HIGH`） | 参考行=86 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
33. 状态=已实现 | 条款=四个门禁接口均要求 `x-internal-debug: true` | 参考行=92 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
34. 状态=已实现 | 条款=未携带内部标识统一返回 `403 + AUTH_FORBIDDEN` | 参考行=93 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
35. 状态=已实现 | 条款=请求体字段范围由 Pydantic schema 强校验 | 参考行=94 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
36. 状态=已实现 | 条款=运行命令：`pytest -v` | 参考行=98 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
37. 状态=已实现 | 条款=结果：`92 passed` | 参考行=99 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
38. 状态=已实现 | 条款=OpenAPI 校验：`openapi=3.1.0` 且四个 Gate D 接口路径存在 | 参考行=100 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
39. 状态=已实现 | 条款=文档检查：无占位残留关键字 | 参考行=101 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
40. 状态=已实现 | 条款=文档引用检查：`DOC_REFS_OK` | 参考行=102 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
41. 状态=已实现 | 条款=Gate D 四门禁接口契约、阈值判定与阻断逻辑已闭环。 | 参考行=106 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
42. 状态=已实现 | 条款=Gate D 的“门禁执行能力”在本分支已具备运行与回归证据。 | 参考行=107 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
43. 状态=已实现 | 条款=`resume_token` 增加 24h 失效约束并完成回归验证。 | 参考行=111 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
44. 状态=已实现 | 条款=`dlq requeue/discard` 成功路径增加审计日志落库并完成回归验证。 | 参考行=112 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
1. 状态=已实现 | 条款=固化 Gate E 的灰度发布策略与回滚策略契约。 | 参考行=9 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=已实现 | 条款=将“触发条件、执行顺序、回放验证”落为可测试行为。 | 参考行=10 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
3. 状态=已实现 | 条款=给出 Gate E 最小验收证据清单。 | 参考行=11 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
4. 状态=已实现 | 条款=`POST /api/v1/internal/release/rollout/plan` | 参考行=17 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
5. 状态=已实现 | 条款=`POST /api/v1/internal/release/rollout/decision` | 参考行=18 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
6. 状态=已实现 | 条款=灰度顺序固定：租户白名单 -> 项目规模分层放量。 | 参考行=22 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=已实现 | 条款=项目规模使用 `small/medium/large` 三层。 | 参考行=23 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=已实现 | 条款=`high_risk=true` 的任务始终返回 `force_hitl=true`。 | 参考行=24 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
9. 状态=已实现 | 条款=tenant 不在白名单：`TENANT_NOT_IN_WHITELIST`。 | 参考行=28 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
10. 状态=已实现 | 条款=项目规模不在已放量层级：`PROJECT_SIZE_NOT_ENABLED`。 | 参考行=29 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
11. 状态=已实现 | 条款=任一门禁 breach 满足 `consecutive_failures >= consecutive_threshold`（默认阈值 2）。 | 参考行=39 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
12. 状态=已实现 | 条款=`model_config` | 参考行=43 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
13. 状态=已实现 | 条款=`retrieval_params` | 参考行=44 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
14. 状态=已实现 | 条款=`workflow_version` | 参考行=45 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
15. 状态=已实现 | 条款=`release_version` | 参考行=46 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
16. 状态=已实现 | 条款=回滚后必须创建并执行一次回放验证任务。 | 参考行=50 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
17. 状态=已实现 | 条款=返回 `replay_verification.job_id` 与 `replay_verification.status`。 | 参考行=51 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
18. 状态=已实现 | 条款=`rollback_completed_within_30m=true` | 参考行=55 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
19. 状态=已实现 | 条款=`service_restored=true` | 参考行=56 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
20. 状态=已实现 | 条款=三个 Gate E 内部接口均要求 `x-internal-debug: true`。 | 参考行=62 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
21. 状态=已实现 | 条款=未携带内部标识统一返回 `403 + AUTH_FORBIDDEN`。 | 参考行=63 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
22. 状态=已实现 | 条款=入参字段由 schema 强校验，非法值返回 `400 + REQ_VALIDATION_FAILED`。 | 参考行=64 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
23. 状态=已实现 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=68 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
24. 状态=已实现 | 条款=`docs/design/2026-02-21-openapi-v1.yaml` | 参考行=69 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
25. 状态=已实现 | 条款=`docs/design/2026-02-21-api-contract-test-samples.md` | 参考行=70 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
26. 状态=已实现 | 条款=运行命令：`pytest -v` | 参考行=74 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
27. 状态=已实现 | 条款=OpenAPI 解析：`openapi=3.1.0` | 参考行=75 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
28. 状态=已实现 | 条款=文档禁词检查：占位词与非约定图示关键字不得出现 | 参考行=76 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
29. 状态=已实现 | 条款=文档引用检查：显式引用路径全部存在 | 参考行=77 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
30. 状态=已实现 | 条款=`pytest -q` 退出码 `0` | 参考行=81 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
31. 状态=已实现 | 条款=Gate E 新增用例 `tests/test_gate_e_rollout_and_rollback.py` 通过 | 参考行=82 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
32. 状态=已实现 | 条款=OpenAPI 新增 Gate E 三个内部路径存在并可解析 | 参考行=83 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
33. 状态=已实现 | 条款=rollout 决策满足白名单与分层放量规则，且高风险强制 HITL。 | 参考行=89 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
34. 状态=已实现 | 条款=rollback 在触发条件命中时按固定顺序执行并触发回放验证。 | 参考行=90 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
35. 状态=已实现 | 条款=rollback 输出满足 30 分钟内恢复约束字段。 | 参考行=91 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/design/2026-02-22-gate-f-operations-optimization-checklist.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
1. 状态=已实现 | 条款=将 Gate F 的数据回流与策略优化落为可执行、可回归接口。 | 参考行=9 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=已实现 | 条款=形成“数据集版本演进 + 策略版本演进”的双轨证据。 | 参考行=10 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
3. 状态=已实现 | 条款=为后续连续迭代提供最小运维优化基线。 | 参考行=11 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
4. 状态=已实现 | 条款=DLQ 样本回流到反例集。 | 参考行=19 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
5. 状态=已实现 | 条款=人审改判样本回流到黄金集候选。 | 参考行=20 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
6. 状态=已实现 | 条款=每次执行都更新评估数据集版本号。 | 参考行=21 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=已实现 | 条款=`counterexample_added >= 0` | 参考行=25 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=已实现 | 条款=`gold_candidates_added >= 0` | 参考行=26 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
9. 状态=已实现 | 条款=`dataset_version_after != dataset_version_before` | 参考行=27 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
10. 状态=已实现 | 条款=selector 阈值与规则可调整。 | 参考行=37 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
11. 状态=已实现 | 条款=评分校准参数可调整。 | 参考行=38 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
12. 状态=已实现 | 条款=工具权限与审批策略可调整。 | 参考行=39 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
13. 状态=已实现 | 条款=返回 `strategy_version` 且版本递增。 | 参考行=43 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
14. 状态=已实现 | 条款=返回体中的 selector/calibration/tool_policy 与输入一致。 | 参考行=44 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
15. 状态=已实现 | 条款=Gate F 两个接口都必须携带 `x-internal-debug: true`。 | 参考行=50 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
16. 状态=已实现 | 条款=未携带内部标识统一返回 `403 + AUTH_FORBIDDEN`。 | 参考行=51 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
17. 状态=已实现 | 条款=非法入参统一返回 `400 + REQ_VALIDATION_FAILED`。 | 参考行=52 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
18. 状态=已实现 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=56 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
19. 状态=已实现 | 条款=`docs/design/2026-02-21-openapi-v1.yaml` | 参考行=57 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
20. 状态=已实现 | 条款=`docs/design/2026-02-21-api-contract-test-samples.md` | 参考行=58 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
21. 状态=已实现 | 条款=运行命令：`pytest -v` | 参考行=62 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
22. 状态=已实现 | 条款=OpenAPI 解析：`openapi=3.1.0` | 参考行=63 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
23. 状态=已实现 | 条款=文档禁词检查：占位词与非约定图示关键字不得出现 | 参考行=64 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
24. 状态=已实现 | 条款=文档引用检查：显式引用路径全部存在 | 参考行=65 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
25. 状态=已实现 | 条款=`pytest -q` 退出码 `0` | 参考行=69 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
26. 状态=已实现 | 条款=Gate F 新增用例 `tests/test_gate_f_ops_optimization.py` 通过 | 参考行=70 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
27. 状态=已实现 | 条款=OpenAPI 新增 Gate F 两个内部路径存在并可解析 | 参考行=71 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
28. 状态=已实现 | 条款=数据回流可执行且每轮都能产出新数据集版本号。 | 参考行=77 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
29. 状态=已实现 | 条款=策略优化可执行且每轮都能产出新策略版本号。 | 参考行=78 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
30. 状态=已实现 | 条款=Gate F 接口具备稳定的鉴权与回归用例覆盖。 | 参考行=79 | 证据: docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/design/2026-02-22-observability-and-deploy-production-spec.md**
文件级结论：部分实现 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
1. 状态=部分实现 | 条款=建立可观测、可告警、可灰度、可回滚、可复盘的发布体系。 | 参考行=9 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
2. 状态=部分实现 | 条款=将 Gate D/E/F 门禁与部署流水线联动成可执行流程。 | 参考行=10 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
3. 状态=部分实现 | 条款=定义发布准入证据与回退动作，避免“凭感觉上线”。 | 参考行=11 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
4. 状态=部分实现 | 条款=Metrics/Logs/Traces 统一语义。 | 参考行=17 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
5. 状态=部分实现 | 条款=告警分级（P0/P1/P2）与 runbook 联动。 | 参考行=18 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
6. 状态=部分实现 | 条款=staging replay、canary、rollback 机制。 | 参考行=19 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
7. 状态=部分实现 | 条款=P6 准入接口与发布决策流程。 | 参考行=20 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
8. 状态=部分实现 | 条款=全栈 AIOps 自动调参。 | 参考行=24 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
9. 状态=部分实现 | 条款=多云统一发布平台。 | 参考行=25 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
10. 状态=部分实现 | 条款=`GET /api/v1/internal/ops/metrics/summary` 已提供租户级指标摘要。 | 参考行=29 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
11. 状态=部分实现 | 条款=`POST /api/v1/internal/release/replay/e2e` 已可执行最小回放。 | 参考行=30 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
12. 状态=部分实现 | 条款=`POST /api/v1/internal/release/readiness/evaluate` 已可执行准入评估。 | 参考行=31 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
13. 状态=部分实现 | 条款=无证据不发布。 | 参考行=49 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
14. 状态=部分实现 | 条款=触发阈值即回滚，不做人工拖延。 | 参考行=50 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
15. 状态=部分实现 | 条款=回滚后必须执行 replay 验证。 | 参考行=51 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
16. 状态=部分实现 | 条款=P0：越权风险、主链路不可用，5 分钟内止损。 | 参考行=93 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
17. 状态=部分实现 | 条款=P1：质量显著劣化、DLQ 激增，15 分钟内降级。 | 参考行=94 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
18. 状态=部分实现 | 条款=P2：性能或成本异常，30 分钟内修正或回退。 | 参考行=95 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
19. 状态=部分实现 | 条款=runbook 链接。 | 参考行=99 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
20. 状态=部分实现 | 条款=oncall 责任人。 | 参考行=100 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
21. 状态=部分实现 | 条款=最近变更版本。 | 参考行=101 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
22. 状态=部分实现 | 条款=发布准入要求：`quality/performance/security/cost/rollout/rollback/ops` 全部通过 + `replay_passed=true`。 | 参考行=105 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
23. 状态=部分实现 | 条款=任一项失败时 `admitted=false`，禁止发布。 | 参考行=106 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
24. 状态=部分实现 | 条款=回滚后必须再次执行 replay，成功才允许恢复流量。 | 参考行=107 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
25. 状态=部分实现 | 条款=`OTEL_EXPORTER_OTLP_ENDPOINT` | 参考行=111 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
26. 状态=部分实现 | 条款=`OBS_METRICS_NAMESPACE` | 参考行=112 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
27. 状态=部分实现 | 条款=`OBS_ALERT_WEBHOOK` | 参考行=113 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
28. 状态=部分实现 | 条款=`RELEASE_CANARY_RATIO` | 参考行=114 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
29. 状态=部分实现 | 条款=`RELEASE_CANARY_DURATION_MIN` | 参考行=115 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
30. 状态=部分实现 | 条款=`ROLLBACK_MAX_MINUTES` | 参考行=116 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
31. 状态=部分实现 | 条款=`P6_READINESS_REQUIRED` | 参考行=117 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
32. 状态=部分实现 | 条款=指标接口结构与租户隔离回归。 | 参考行=121 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
33. 状态=部分实现 | 条款=Gate D/E/F 内部接口回归。 | 参考行=122 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
34. 状态=部分实现 | 条款=P6 replay/readiness 回归。 | 参考行=123 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
35. 状态=部分实现 | 条款=全量回归。 | 参考行=124 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
36. 状态=部分实现 | 条款=指标看板截图与告警触发记录。 | 参考行=138 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
37. 状态=部分实现 | 条款=staging replay 报告。 | 参考行=139 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
38. 状态=部分实现 | 条款=canary 期间关键指标对比（before/after）。 | 参考行=140 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
39. 状态=部分实现 | 条款=回滚演练记录（触发时间、完成时间、恢复状态）。 | 参考行=141 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
40. 状态=部分实现 | 条款=readiness 准入报告（failed_checks 为空）。 | 参考行=142 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
41. 状态=部分实现 | 条款=观测三件套（metrics/logs/traces）可用于故障定位。 | 参考行=146 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
42. 状态=部分实现 | 条款=Gate D/E/F 与流水线自动联动。 | 参考行=147 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
43. 状态=部分实现 | 条款=可重复执行灰度与回滚。 | 参考行=148 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
44. 状态=部分实现 | 条款=发布前强制回放与准入评估生效。 | 参考行=149 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
45. 状态=部分实现 | 条款=风险：告警阈值配置不当导致误触发。 | 参考行=153 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
46. 状态=部分实现 | 条款=风险：canary 样本不足导致误判。 | 参考行=154 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
47. 状态=部分实现 | 条款=回退：降流量到稳定版本并冻结策略变更，待 replay 复核后再恢复。 | 参考行=155 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
48. 状态=部分实现 | 条款=[x] 指标/日志/Trace 统一语义已落地。 | 参考行=159 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
49. 状态=部分实现 | 条款=[x] Gate D/E/F 自动阻断已联动。 | 参考行=160 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
50. 状态=部分实现 | 条款=[x] canary 与 rollback 演练通过。 | 参考行=161 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
51. 状态=部分实现 | 条款=[x] P6 准入规则在流水线中强制执行。 | 参考行=162 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
52. 状态=部分实现 | 条款=[x] 复盘模板与runbook链接完备。 | 参考行=163 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
53. 状态=部分实现 | 条款=新增发布流水线执行接口：`POST /api/v1/internal/release/pipeline/execute`，统一输出 `stage/admitted/failed_checks`。 | 参考行=167 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
54. 状态=部分实现 | 条款=新增 pipeline 配置收口字段： | 参考行=168 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
55. 状态=部分实现 | 条款=`ops/metrics/summary` 新增 `observability` 视图，包含 namespace、OTEL/alert 配置状态与发布关键参数。 | 参考行=173 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
56. 状态=部分实现 | 条款=请求链路响应头统一返回 `x-trace-id` 与 `x-request-id`，便于 API/Worker/审计跨层对齐排障。 | 参考行=174 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md
57. 状态=部分实现 | 条款=新增 SLO 探针脚本 `scripts/run_slo_probe.py` 与运行手册 `docs/ops/2026-02-23-slo-capacity-validation-runbook.md`，用于 staging/prod 准入前延迟与错误率收口。 | 参考行=175 | 证据: app/ops/*; docs/ops/2026-02-23-observability-deploy-evidence.md

**文件：docs/design/2026-02-22-parser-and-retrieval-production-spec.md**
文件级结论：部分实现 | 证据: app/parser_adapters.py; app/store.py
1. 状态=部分实现 | 条款=将解析链路替换为可运行的真实适配器能力（MinerU/Docling/OCR）。 | 参考行=9 | 证据: app/parser_adapters.py; app/store.py
2. 状态=部分实现 | 条款=将检索链路替换为真实 LightRAG 索引与检索能力。 | 参考行=10 | 证据: app/parser_adapters.py; app/store.py
3. 状态=部分实现 | 条款=保持 citation 字段与检索输出契约稳定。 | 参考行=11 | 证据: app/parser_adapters.py; app/store.py
4. 状态=部分实现 | 条款=解析器路由与 fallback 执行。 | 参考行=17 | 证据: app/parser_adapters.py; app/store.py
5. 状态=部分实现 | 条款=parse manifest 与 chunk 元数据真落库。 | 参考行=18 | 证据: app/parser_adapters.py; app/store.py
6. 状态=部分实现 | 条款=LightRAG 索引构建、查询与 metadata 过滤。 | 参考行=19 | 证据: app/parser_adapters.py; app/store.py
7. 状态=部分实现 | 条款=query rewrite 约束保持与 rerank 降级。 | 参考行=20 | 证据: app/parser_adapters.py; app/store.py
8. 状态=部分实现 | 条款=多模态图像理解增强。 | 参考行=24 | 证据: app/parser_adapters.py; app/store.py
9. 状态=部分实现 | 条款=跨语言 OCR 质量优化专题。 | 参考行=25 | 证据: app/parser_adapters.py; app/store.py
10. 状态=部分实现 | 条款=复杂知识图谱增量更新优化。 | 参考行=26 | 证据: app/parser_adapters.py; app/store.py
11. 状态=部分实现 | 条款=`ParserAdapterRegistry` 与 fallback 链路已存在。 | 参考行=30 | 证据: app/parser_adapters.py; app/store.py
12. 状态=部分实现 | 条款=`BEA_DISABLED_PARSERS` 开关已支持故障注入回归。 | 参考行=31 | 证据: app/parser_adapters.py; app/store.py
13. 状态=部分实现 | 条款=检索输出已有 `index_name` 和 `tenant_id/document_id` 元数据。 | 参考行=32 | 证据: app/parser_adapters.py; app/store.py
14. 状态=部分实现 | 条款=parse 失败必须给出稳定错误码，不允许裸异常透出。 | 参考行=45 | 证据: app/parser_adapters.py; app/store.py
15. 状态=部分实现 | 条款=检索调用必须带 tenant/project 过滤，不允许全局召回。 | 参考行=46 | 证据: app/parser_adapters.py; app/store.py
16. 状态=部分实现 | 条款=rerank 失败只允许降级，不允许主链路中断。 | 参考行=47 | 证据: app/parser_adapters.py; app/store.py
17. 状态=部分实现 | 条款=MinerU：兼容 `content_list.json/context_list.json/full.md`。 | 参考行=59 | 证据: app/parser_adapters.py; app/store.py
18. 状态=部分实现 | 条款=Docling：Office/HTML/PDF 常规解析。 | 参考行=60 | 证据: app/parser_adapters.py; app/store.py
19. 状态=部分实现 | 条款=OCR：主解析失败时兜底。 | 参考行=61 | 证据: app/parser_adapters.py; app/store.py
20. 状态=部分实现 | 条款=manifest：`run_id,document_id,tenant_id,selected_parser,fallback_chain,status,error_code`。 | 参考行=71 | 证据: app/parser_adapters.py; app/store.py
21. 状态=部分实现 | 条款=chunk：`chunk_id,document_id,page,bbox,heading_path,chunk_type,parser,parser_version,text`。 | 参考行=72 | 证据: app/parser_adapters.py; app/store.py
22. 状态=部分实现 | 条款=去重键：`document_id + chunk_hash`。 | 参考行=73 | 证据: app/parser_adapters.py; app/store.py
23. 状态=部分实现 | 条款=manifest：`content_source,chunk_count`。 | 参考行=77 | 证据: app/parser_adapters.py; app/store.py
24. 状态=部分实现 | 条款=chunk：`content_source`。 | 参考行=78 | 证据: app/parser_adapters.py; app/store.py
25. 状态=部分实现 | 条款=索引名：`lightrag:{tenant_id}:{project_id}`。 | 参考行=88 | 证据: app/parser_adapters.py; app/store.py
26. 状态=部分实现 | 条款=查询过滤：`tenant_id/project_id/doc_type`。 | 参考行=89 | 证据: app/parser_adapters.py; app/store.py
27. 状态=部分实现 | 条款=查询模式：`local/global/hybrid/mix`。 | 参考行=90 | 证据: app/parser_adapters.py; app/store.py
28. 状态=部分实现 | 条款=`constraints_preserved=true/false` 与差异摘要。 | 参考行=100 | 证据: app/parser_adapters.py; app/store.py
29. 状态=部分实现 | 条款=rerank 失败时 `degraded=true`。 | 参考行=101 | 证据: app/parser_adapters.py; app/store.py
30. 状态=部分实现 | 条款=降级排序按召回分。 | 参考行=102 | 证据: app/parser_adapters.py; app/store.py
31. 状态=部分实现 | 条款=不改 `GET /documents/{document_id}/chunks` 输出语义。 | 参考行=112 | 证据: app/parser_adapters.py; app/store.py
32. 状态=部分实现 | 条款=不改 citation 最小字段：`document_id/page/bbox/text/context`。 | 参考行=113 | 证据: app/parser_adapters.py; app/store.py
33. 状态=部分实现 | 条款=新增字段仅可追加，不可破坏老字段含义。 | 参考行=114 | 证据: app/parser_adapters.py; app/store.py
34. 状态=部分实现 | 条款=citation 可追加 `heading_path/chunk_type/content_source` 以支持回跳与调试。 | 参考行=115 | 证据: app/parser_adapters.py; app/store.py
35. 状态=部分实现 | 条款=`BEA_DISABLED_PARSERS` | 参考行=119 | 证据: app/parser_adapters.py; app/store.py
36. 状态=部分实现 | 条款=`MINERU_ENDPOINT` / `MINERU_TIMEOUT_S` | 参考行=120 | 证据: app/parser_adapters.py; app/store.py
37. 状态=部分实现 | 条款=`DOCLING_ENDPOINT` / `DOCLING_TIMEOUT_S` | 参考行=121 | 证据: app/parser_adapters.py; app/store.py
38. 状态=部分实现 | 条款=`OCR_ENDPOINT` / `OCR_TIMEOUT_S` | 参考行=122 | 证据: app/parser_adapters.py; app/store.py
39. 状态=部分实现 | 条款=`LIGHTRAG_DSN` | 参考行=123 | 证据: app/parser_adapters.py; app/store.py
40. 状态=部分实现 | 条款=`LIGHTRAG_INDEX_PREFIX` | 参考行=124 | 证据: app/parser_adapters.py; app/store.py
41. 状态=部分实现 | 条款=`RERANK_TIMEOUT_MS` | 参考行=125 | 证据: app/parser_adapters.py; app/store.py
42. 状态=部分实现 | 条款=解析单测：路由、fallback、错误分类、编码回退。 | 参考行=129 | 证据: app/parser_adapters.py; app/store.py
43. 状态=部分实现 | 条款=检索集成：模式选择、metadata 过滤、降级。 | 参考行=130 | 证据: app/parser_adapters.py; app/store.py
44. 状态=部分实现 | 条款=回放：上传->解析->检索->评估链路样本集。 | 参考行=131 | 证据: app/parser_adapters.py; app/store.py
45. 状态=部分实现 | 条款=解析成功率与 fallback 占比报表。 | 参考行=143 | 证据: app/parser_adapters.py; app/store.py
46. 状态=部分实现 | 条款=召回隔离证明（跨租户命中 0）。 | 参考行=144 | 证据: app/parser_adapters.py; app/store.py
47. 状态=部分实现 | 条款=citation 完整率报告。 | 参考行=145 | 证据: app/parser_adapters.py; app/store.py
48. 状态=部分实现 | 条款=rerank 降级触发率与稳定性报告。 | 参考行=146 | 证据: app/parser_adapters.py; app/store.py
49. 状态=部分实现 | 条款=真实文档可稳定完成 parse/index/query。 | 参考行=150 | 证据: app/parser_adapters.py; app/store.py
50. 状态=部分实现 | 条款=检索输出元数据字段完整且可追溯。 | 参考行=151 | 证据: app/parser_adapters.py; app/store.py
51. 状态=部分实现 | 条款=无跨租户召回。 | 参考行=152 | 证据: app/parser_adapters.py; app/store.py
52. 状态=部分实现 | 条款=rerank 异常不影响主链路成功返回。 | 参考行=153 | 证据: app/parser_adapters.py; app/store.py
53. 状态=部分实现 | 条款=风险：外部解析服务抖动导致延迟飙升。 | 参考行=157 | 证据: app/parser_adapters.py; app/store.py
54. 状态=部分实现 | 条款=风险：索引写入失败导致检索空结果。 | 参考行=158 | 证据: app/parser_adapters.py; app/store.py
55. 状态=部分实现 | 条款=回退：临时切回稳定 parser 顺序与本地检索降级策略，保障可用性优先。 | 参考行=159 | 证据: app/parser_adapters.py; app/store.py
56. 状态=部分实现 | 条款=[x] 真实 adapter 已接入并可回归。 | 参考行=163 | 证据: app/parser_adapters.py; app/store.py
57. 状态=部分实现 | 条款=[x] manifest/chunk 字段全量对齐。 | 参考行=164 | 证据: app/parser_adapters.py; app/store.py
58. 状态=部分实现 | 条款=[x] LightRAG 查询隔离已验证。 | 参考行=165 | 证据: app/parser_adapters.py; app/store.py
59. 状态=部分实现 | 条款=[x] rewrite/rerank 降级策略已验证。 | 参考行=166 | 证据: app/parser_adapters.py; app/store.py
60. 状态=部分实现 | 条款=[x] 回放证据与指标报表齐全。 | 参考行=167 | 证据: app/parser_adapters.py; app/store.py
61. 状态=部分实现 | 条款=`app/parser_adapters.py` 新增 `HttpParserAdapter`，支持 `MINERU/DOCLING/OCR` endpoint + timeout 配置；未配置 endpoint 时保持 stub 行为。 | 参考行=171 | 证据: app/parser_adapters.py; app/store.py
62. 状态=部分实现 | 条款=parser 返回兼容 `chunks/content_list/full_md(full.md)` 三类载荷，统一映射为 chunk 契约字段。 | 参考行=172 | 证据: app/parser_adapters.py; app/store.py
63. 状态=部分实现 | 条款=`ParserAdapterRegistry.parse_with_route` 支持解析失败自动回退到 fallback parser，不再因首选 parser 异常直接中断。 | 参考行=173 | 证据: app/parser_adapters.py; app/store.py
64. 状态=部分实现 | 条款=新增回归：`tests/test_parser_adapters.py::test_registry_uses_http_parser_payload_when_endpoint_configured`。 | 参考行=174 | 证据: app/parser_adapters.py; app/store.py
65. 状态=部分实现 | 条款=新增回归：`tests/test_parser_adapters.py::test_registry_fallbacks_when_selected_http_parser_fails`。 | 参考行=175 | 证据: app/parser_adapters.py; app/store.py
66. 状态=部分实现 | 条款=`app/store.py` 新增 chunk 标准化与去重：`chunk_hash = sha256(document_id+page+bbox+heading_path+text)`，并补齐 `page/bbox/chunk_id`。 | 参考行=176 | 证据: app/parser_adapters.py; app/store.py
67. 状态=部分实现 | 条款=`app/repositories/documents.py` 与 `document_chunks` 表新增 `chunk_hash` 持久化字段；读取结果补齐 `page/bbox`。 | 参考行=177 | 证据: app/parser_adapters.py; app/store.py
68. 状态=部分实现 | 条款=解析成功路径新增 LightRAG 索引写入钩子（`LIGHTRAG_DSN` 可选）；索引失败不阻断主链路并记录指标。 | 参考行=178 | 证据: app/parser_adapters.py; app/store.py
69. 状态=部分实现 | 条款=检索查询新增 LightRAG 查询路径（`LIGHTRAG_DSN` 可选）+ 二次 tenant/project/supplier/doc_scope 过滤，保证隔离。 | 参考行=179 | 证据: app/parser_adapters.py; app/store.py
70. 状态=部分实现 | 条款=改写约束保持新增 `constraint_diff` 真实计算；rerank 异常时降级返回 `degraded=true` 与 `degrade_reason`。 | 参考行=180 | 证据: app/parser_adapters.py; app/store.py
71. 状态=部分实现 | 条款=`summarize_ops_metrics` 新增 `parse_retrieval` 观测字段：解析次数、fallback 次数、索引调用/失败、查询次数、降级次数。 | 参考行=181 | 证据: app/parser_adapters.py; app/store.py
72. 状态=部分实现 | 条款=新增回归：`tests/test_retrieval_query.py::test_retrieval_query_degrades_when_rerank_raises`。 | 参考行=182 | 证据: app/parser_adapters.py; app/store.py
73. 状态=部分实现 | 条款=新增回归：`tests/test_retrieval_query.py::test_retrieval_query_uses_lightrag_index_prefix_and_filters_metadata`。 | 参考行=183 | 证据: app/parser_adapters.py; app/store.py
74. 状态=部分实现 | 条款=新增回归：`tests/test_parse_manifest_and_error_classification.py::test_parse_success_updates_manifest_status`（补充 chunk_hash/page/bbox 断言）。 | 参考行=184 | 证据: app/parser_adapters.py; app/store.py
75. 状态=部分实现 | 条款=新增观测回归：`tests/test_observability_metrics_api.py` 覆盖 `parse_retrieval` 指标字段。 | 参考行=185 | 证据: app/parser_adapters.py; app/store.py

**文件：docs/design/2026-02-22-persistence-and-queue-production-spec.md**
文件级结论：部分实现 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
1. 状态=部分实现 | 条款=将当前 `memory/sqlite` 兼容实现升级为 `PostgreSQL + Redis` 生产实现。 | 参考行=9 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
2. 状态=部分实现 | 条款=保持既有 API 契约、错误码、状态机语义不变。 | 参考行=10 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
3. 状态=部分实现 | 条款=给实现与验收提供可直接执行的任务分解与证据格式。 | 参考行=11 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
4. 状态=部分实现 | 条款=仓储真值迁移：`jobs/workflow_checkpoints/dlq_items/audit_logs/evaluation_reports/documents/document_chunks`。 | 参考行=17 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
5. 状态=部分实现 | 条款=幂等与 outbox：请求幂等键、事件可靠投递、消费去重。 | 参考行=18 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
6. 状态=部分实现 | 条款=Redis 队列：enqueue/dequeue/ack/nack/retry/DLQ。 | 参考行=19 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
7. 状态=部分实现 | 条款=DB RLS 注入：`app.current_tenant` 会话级注入与强校验。 | 参考行=20 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
8. 状态=部分实现 | 条款=对象存储 WORM：原始文档与报告归档、legal hold 与 cleanup 行为。 | 参考行=21 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
9. 状态=部分实现 | 条款=跨地域多活。 | 参考行=25 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
10. 状态=部分实现 | 条款=跨服务分布式事务。 | 参考行=26 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
11. 状态=部分实现 | 条款=自动分片与在线扩容编排。 | 参考行=27 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
12. 状态=部分实现 | 条款=`SqliteBackedStore` + `SqliteQueueBackend` 已提供本地持久化回归能力。 | 参考行=31 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
13. 状态=部分实现 | 条款=outbox/queue 内部联调接口已存在并有回归测试。 | 参考行=32 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
14. 状态=部分实现 | 条款=queue `ack/nack` 已有租户归属校验。 | 参考行=33 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
15. 状态=部分实现 | 条款=API 不直接操作 Redis 与 SQL 细节，统一经 repository/queue abstraction。 | 参考行=45 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
16. 状态=部分实现 | 条款=业务事务与 outbox 写入同事务提交。 | 参考行=46 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
17. 状态=部分实现 | 条款=任一重试失败不得破坏状态机时序（`dlq_pending -> dlq_recorded -> failed`）。 | 参考行=47 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
18. 状态=部分实现 | 条款=`JobsRepository`、`WorkflowRepository`、`DlqRepository`、`AuditRepository`。 | 参考行=59 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
19. 状态=部分实现 | 条款=所有写接口显式接收 `tenant_id` 与 `trace_id`。 | 参考行=60 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
20. 状态=部分实现 | 条款=与当前 `InMemoryStore` 输出字段保持一致。 | 参考行=61 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
21. 状态=部分实现 | 条款=会话变量：`SELECT set_config('app.current_tenant', :tenant_id, true)`。 | 参考行=71 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
22. 状态=部分实现 | 条款=核心表 RLS policy 全覆盖。 | 参考行=72 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
23. 状态=部分实现 | 条款=事务工具：`run_in_tx(tenant_id, fn)`。 | 参考行=73 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
24. 状态=部分实现 | 条款=key 命名：`bea:{env}:{tenant}:{queue}`。 | 参考行=83 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
25. 状态=部分实现 | 条款=消息字段：`message_id,event_id,job_id,tenant_id,trace_id,job_type,attempt`。 | 参考行=84 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
26. 状态=部分实现 | 条款=超阈值失败进入 DLQ 并写审计。 | 参考行=85 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
27. 状态=部分实现 | 条款=outbox 状态：`pending/published/failed`。 | 参考行=95 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
28. 状态=部分实现 | 条款=幂等键：`event_id + consumer_name`。 | 参考行=96 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
29. 状态=部分实现 | 条款=死信事件可重放并可审计。 | 参考行=97 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
30. 状态=部分实现 | 条款=开关：`BEA_STORE_BACKEND=sqlite|postgres`、`BEA_QUEUE_BACKEND=sqlite|redis`。 | 参考行=107 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
31. 状态=部分实现 | 条款=双写观察窗口与一致性比对脚本。 | 参考行=108 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
32. 状态=部分实现 | 条款=回退 Runbook（命令级）。 | 参考行=109 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
33. 状态=部分实现 | 条款=对象存储抽象与 `local/s3` 最小实现。 | 参考行=119 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
34. 状态=部分实现 | 条款=原始文档写入对象存储并记录 `storage_uri`。 | 参考行=120 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
35. 状态=部分实现 | 条款=评估报告写入对象存储并记录 `report_uri`。 | 参考行=121 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
36. 状态=部分实现 | 条款=`legal-hold` 与 `storage/cleanup` 对象存储联动。 | 参考行=122 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
37. 状态=部分实现 | 条款=外部 REST/OpenAPI 不新增破坏性字段。 | 参考行=126 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
38. 状态=部分实现 | 条款=`job_id/thread_id/resume_token/error.code` 语义不可变。 | 参考行=127 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
39. 状态=部分实现 | 条款=新增仅允许内部字段，不允许修改现有字段含义。 | 参考行=128 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
40. 状态=部分实现 | 条款=`POSTGRES_DSN` | 参考行=132 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
41. 状态=部分实现 | 条款=`POSTGRES_POOL_MIN` | 参考行=133 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
42. 状态=部分实现 | 条款=`POSTGRES_POOL_MAX` | 参考行=134 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
43. 状态=部分实现 | 条款=`BEA_STORE_POSTGRES_TABLE` | 参考行=135 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
44. 状态=部分实现 | 条款=`REDIS_DSN` | 参考行=136 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
45. 状态=部分实现 | 条款=`REDIS_QUEUE_VISIBILITY_TIMEOUT_S` | 参考行=137 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
46. 状态=部分实现 | 条款=`IDEMPOTENCY_TTL_HOURS` | 参考行=138 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
47. 状态=部分实现 | 条款=`OUTBOX_POLL_INTERVAL_MS` | 参考行=139 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
48. 状态=部分实现 | 条款=`BEA_STORE_BACKEND` | 参考行=140 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
49. 状态=部分实现 | 条款=`BEA_QUEUE_BACKEND` | 参考行=141 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
50. 状态=部分实现 | 条款=`POSTGRES_APPLY_RLS` | 参考行=142 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
51. 状态=部分实现 | 条款=`BEA_REQUIRE_TRUESTACK` | 参考行=143 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
52. 状态=部分实现 | 条款=`BEA_OBJECT_STORAGE_BACKEND` | 参考行=144 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
53. 状态=部分实现 | 条款=`OBJECT_STORAGE_BUCKET` | 参考行=145 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
54. 状态=部分实现 | 条款=`OBJECT_STORAGE_ROOT` | 参考行=146 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
55. 状态=部分实现 | 条款=`OBJECT_STORAGE_PREFIX` | 参考行=147 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
56. 状态=部分实现 | 条款=`OBJECT_STORAGE_WORM_MODE` | 参考行=148 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
57. 状态=部分实现 | 条款=`OBJECT_STORAGE_ENDPOINT` | 参考行=149 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
58. 状态=部分实现 | 条款=`OBJECT_STORAGE_REGION` | 参考行=150 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
59. 状态=部分实现 | 条款=`OBJECT_STORAGE_ACCESS_KEY` | 参考行=151 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
60. 状态=部分实现 | 条款=`OBJECT_STORAGE_SECRET_KEY` | 参考行=152 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
61. 状态=部分实现 | 条款=`OBJECT_STORAGE_FORCE_PATH_STYLE` | 参考行=153 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
62. 状态=部分实现 | 条款=单测：repository CRUD/tenant scope/idempotency。 | 参考行=157 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
63. 状态=部分实现 | 条款=集成：queue retry/ack/nack/DLQ/outbox relay。 | 参考行=158 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
64. 状态=部分实现 | 条款=回放：Gate C-D 核心链路在 postgres+redis 下跑通。 | 参考行=159 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
65. 状态=部分实现 | 条款=变更摘要（接口/数据模型/配置）。 | 参考行=173 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
66. 状态=部分实现 | 条款=测试输出（命令 + 通过截图或日志片段）。 | 参考行=174 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
67. 状态=部分实现 | 条款=一致性比对结果（双写窗口）。 | 参考行=175 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
68. 状态=部分实现 | 条款=回退演练结果（开始时间、结束时间、结果）。 | 参考行=176 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
69. 状态=部分实现 | 条款=主链路关键状态完全不依赖进程内内存。 | 参考行=180 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
70. 状态=部分实现 | 条款=重启后 `jobs/checkpoints/outbox` 可恢复。 | 参考行=181 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
71. 状态=部分实现 | 条款=跨租户访问在 API + DB + queue 三层都被阻断。 | 参考行=182 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
72. 状态=部分实现 | 条款=全量回归在 `postgres+redis` 模式通过。 | 参考行=183 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
73. 状态=部分实现 | 条款=风险：SQL 性能退化导致 job 超时。 | 参考行=187 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
74. 状态=部分实现 | 条款=风险：queue 可见性超时配置不当造成重复消费。 | 参考行=188 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
75. 状态=部分实现 | 条款=回退：切回 `sqlite` 后端，冻结高风险写操作，仅保留读与必要恢复动作。 | 参考行=189 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
76. 状态=部分实现 | 条款=[x] repository 真实现可用。 | 参考行=193 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
77. 状态=部分实现 | 条款=[x] RLS 生效并有越权回归。 | 参考行=194 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
78. 状态=部分实现 | 条款=[x] Redis queue 路径通过并发回归。 | 参考行=195 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
79. 状态=部分实现 | 条款=[x] outbox relay 幂等验证通过。 | 参考行=196 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
80. 状态=部分实现 | 条款=[x] 回退脚本与演练记录完成。 | 参考行=197 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
81. 状态=部分实现 | 条款=新增 `PostgresBackedStore`，支持 `BEA_STORE_BACKEND=postgres`。 | 参考行=201 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
82. 状态=部分实现 | 条款=`create_store_from_env` 新增 `POSTGRES_DSN` 校验与 `BEA_STORE_POSTGRES_TABLE` 配置。 | 参考行=202 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
83. 状态=部分实现 | 条款=新增工厂回归：`tests/test_store_persistence_backend.py` 覆盖 postgres 分支（fake driver）。 | 参考行=203 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
84. 状态=部分实现 | 条款=新增 `app/db/postgres.py` 事务执行器 `PostgresTxRunner`，统一 `set_config('app.current_tenant', ..., true)` 注入。 | 参考行=204 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
85. 状态=部分实现 | 条款=新增 `RedisQueueBackend`，支持 `BEA_QUEUE_BACKEND=redis` 与 tenant 前缀 key 语义。 | 参考行=205 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
86. 状态=部分实现 | 条款=新增回归：`tests/test_queue_backend.py` 覆盖 redis 工厂与 `enqueue/dequeue/nack/ack` 生命周期（fake driver）。 | 参考行=206 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
87. 状态=部分实现 | 条款=新增仓储层起步实现：`app/repositories/jobs.py`（InMemory + Postgres jobs repository）与回归 `tests/test_jobs_repository.py`。 | 参考行=207 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
88. 状态=部分实现 | 条款=`InMemoryStore` 的 job 创建路径已改为通过 `InMemoryJobsRepository` 写入，降低后续切换成本。 | 参考行=208 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
89. 状态=部分实现 | 条款=`PostgresBackedStore` 已同步写入 `jobs` 表，并在 `get_job_for_tenant` 优先走 `PostgresJobsRepository`。 | 参考行=209 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
90. 状态=部分实现 | 条款=新增 `documents/chunks` 仓储层：`app/repositories/documents.py`（InMemory + Postgres）。 | 参考行=210 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
91. 状态=部分实现 | 条款=`PostgresBackedStore` 增加 `documents/document_chunks` 表，并同步写入文档与 chunk 数据。 | 参考行=211 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
92. 状态=部分实现 | 条款=新增 `parse_manifests` 仓储层：`app/repositories/parse_manifests.py`（InMemory + Postgres）。 | 参考行=212 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
93. 状态=部分实现 | 条款=`run_job_once` 的 parse 状态流转（running/retrying/failed/succeeded）统一通过仓储落库，避免仅内存修改。 | 参考行=213 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
94. 状态=部分实现 | 条款=`PostgresBackedStore` 增加 `parse_manifests` 表，并在查询 manifest 时优先走 PostgreSQL 仓储。 | 参考行=214 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
95. 状态=部分实现 | 条款=新增 `workflow_checkpoints/dlq_items/audit_logs` 仓储层（InMemory + Postgres），并补齐对应单测。 | 参考行=215 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
96. 状态=部分实现 | 条款=`InMemoryStore` 将 checkpoint、DLQ、audit 写入统一收敛到仓储 helper，避免直接修改内存结构导致的持久化偏差。 | 参考行=216 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
97. 状态=部分实现 | 条款=`PostgresBackedStore` 增加 `workflow_checkpoints/dlq_items/audit_logs` 表，并将上述三类读写优先走 PostgreSQL 仓储。 | 参考行=217 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
98. 状态=部分实现 | 条款=新增仓储同步回归：当 repository 返回副本对象时，`append_workflow_checkpoint` 与 `requeue_dlq_item` 仍可正确持久化状态。 | 参考行=218 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
99. 状态=部分实现 | 条款=outbox relay 增加消费幂等键实现：`event_id + consumer_name`，并在队列消息中携带 `consumer_name`。 | 参考行=219 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
100. 状态=部分实现 | 条款=`store_state` 快照新增 `outbox_delivery_records`，覆盖 memory/sqlite/postgres 三种后端状态恢复。 | 参考行=220 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
101. 状态=部分实现 | 条款=新增 `app/db/rls.py`（`PostgresRlsManager`），支持核心表 RLS policy 批量下发（`ENABLE/FORCE RLS + tenant policy`）。 | 参考行=221 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
102. 状态=部分实现 | 条款=`create_store_from_env` 支持 `POSTGRES_APPLY_RLS=true` 自动下发策略，并有工厂回归测试覆盖。 | 参考行=222 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
103. 状态=部分实现 | 条款=新增回退脚本 `scripts/rollback_to_sqlite.py`，可将 `.env` 后端开关一键切回 `sqlite`。 | 参考行=223 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
104. 状态=部分实现 | 条款=新增命令级回退手册 `docs/ops/2026-02-22-backend-rollback-runbook.md`，包含切换、重启、验证与证据模板。 | 参考行=224 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
105. 状态=部分实现 | 条款=新增 RLS 下发脚本 `scripts/apply_postgres_rls.py`，支持 `--dsn/--tables` 批量执行策略。 | 参考行=225 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
106. 状态=部分实现 | 条款=新增 `evaluation_reports` 仓储层（InMemory + Postgres），并将创建/恢复路径改为仓储落库。 | 参考行=226 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
107. 状态=部分实现 | 条款=`PostgresBackedStore` 增加 `evaluation_reports` 表，并在读取评估报告时优先走 PostgreSQL 仓储。 | 参考行=227 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
108. 状态=部分实现 | 条款=新增双写一致性比对能力：`app/ops/backend_consistency.py` + `scripts/compare_store_backends.py`。 | 参考行=228 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
109. 状态=部分实现 | 条款=新增一致性比对 Runbook：`docs/ops/2026-02-22-backend-consistency-runbook.md`（命令级 + 证据模板）。 | 参考行=229 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
110. 状态=部分实现 | 条款=修复真实 PostgreSQL 事务上下文注入语句兼容性：`SET LOCAL ... = %s` 改为 `SELECT set_config(..., true)`，避免参数化语法错误。 | 参考行=230 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
111. 状态=部分实现 | 条款=修复 Postgres job 状态持久化缺口：`jobs` 仓储新增 upsert，`transition_job_status/run_job_once` 在状态与错误字段变更后立即落库。 | 参考行=231 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md
112. 状态=部分实现 | 条款=新增真栈强约束开关：`BEA_REQUIRE_TRUESTACK=true` 时，`BEA_STORE_BACKEND` 只能为 `postgres`，`BEA_QUEUE_BACKEND` 只能为 `redis`，并且 queue 初始化失败不再静默回退到 memory。 | 参考行=232 | 证据: app/repositories/*; app/queue_backend.py; docs/ops/2026-02-23-true-stack-enforcement-evidence.md

**文件：docs/design/2026-02-22-security-and-multitenancy-production-spec.md**
文件级结论：部分实现 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
1. 状态=部分实现 | 条款=将当前测试级隔离升级为生产级“默认拒绝”安全模型。 | 参考行=9 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
2. 状态=部分实现 | 条款=建立 API/DB/Vector/Cache/Queue/Object Storage 六层一致租户隔离。 | 参考行=10 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
3. 状态=部分实现 | 条款=固化高风险动作审批、审计与安全阻断流程。 | 参考行=11 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
4. 状态=部分实现 | 条款=JWT 可信来源与租户注入链。 | 参考行=17 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
5. 状态=部分实现 | 条款=租户越权阻断（接口层 + 数据层 + 检索层）。 | 参考行=18 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
6. 状态=部分实现 | 条款=审批动作（DLQ discard、策略变更、终审）治理。 | 参考行=19 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
7. 状态=部分实现 | 条款=日志脱敏与密钥扫描 CI 阻断。 | 参考行=20 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
8. 状态=部分实现 | 条款=完整 IAM 平台改造。 | 参考行=24 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
9. 状态=部分实现 | 条款=跨组织统一身份目录。 | 参考行=25 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
10. 状态=部分实现 | 条款=部分接口已有 `TENANT_SCOPE_VIOLATION` 阻断。 | 参考行=29 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
11. 状态=部分实现 | 条款=queue `ack/nack` 已加租户归属校验。 | 参考行=30 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
12. 状态=部分实现 | 条款=回归用例已覆盖跨租户 queue 操作阻断。 | 参考行=31 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
13. 状态=部分实现 | 条款=未鉴权即拒绝。 | 参考行=43 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
14. 状态=部分实现 | 条款=无 tenant 上下文即拒绝。 | 参考行=44 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
15. 状态=部分实现 | 条款=无授权即拒绝。 | 参考行=45 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
16. 状态=部分实现 | 条款=越权统一：`TENANT_SCOPE_VIOLATION`。 | 参考行=87 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
17. 状态=部分实现 | 条款=鉴权失败统一：`AUTH_FORBIDDEN` 或 `AUTH_UNAUTHORIZED`。 | 参考行=88 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
18. 状态=部分实现 | 条款=高风险审批缺失统一：`APPROVAL_REQUIRED`。 | 参考行=89 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
19. 状态=部分实现 | 条款=`JWT_ISSUER` | 参考行=93 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
20. 状态=部分实现 | 条款=`JWT_AUDIENCE` | 参考行=94 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
21. 状态=部分实现 | 条款=`JWT_SHARED_SECRET`（当前实现：HS256） | 参考行=95 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
22. 状态=部分实现 | 条款=`JWT_REQUIRED_CLAIMS` | 参考行=96 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
23. 状态=部分实现 | 条款=`SECURITY_APPROVAL_REQUIRED_ACTIONS` | 参考行=97 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
24. 状态=部分实现 | 条款=`SECURITY_LOG_REDACTION_ENABLED` | 参考行=98 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
25. 状态=部分实现 | 条款=`SECURITY_SECRET_SCAN_ENABLED` | 参考行=99 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
26. 状态=部分实现 | 条款=鉴权：过期、伪造、缺 claim。 | 参考行=103 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
27. 状态=部分实现 | 条款=越权：API/DB/Vector 穿透测试。 | 参考行=104 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
28. 状态=部分实现 | 条款=审批：高风险动作缺字段阻断。 | 参考行=105 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
29. 状态=部分实现 | 条款=日志：脱敏检查与密钥扫描。 | 参考行=106 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
30. 状态=部分实现 | 条款=越权阻断报告（按层统计）。 | 参考行=119 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
31. 状态=部分实现 | 条款=审批覆盖率报告（目标 100%）。 | 参考行=120 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
32. 状态=部分实现 | 条款=日志脱敏抽检报告。 | 参考行=121 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
33. 状态=部分实现 | 条款=密钥扫描 CI 结果。 | 参考行=122 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
34. 状态=部分实现 | 条款=六层隔离策略均可验证。 | 参考行=126 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
35. 状态=部分实现 | 条款=越权阻断项为 0。 | 参考行=127 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
36. 状态=部分实现 | 条款=高风险动作审批覆盖率 100%。 | 参考行=128 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
37. 状态=部分实现 | 条款=安全回归在压测并发下稳定。 | 参考行=129 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
38. 状态=部分实现 | 条款=风险：授权规则误配导致误封。 | 参考行=133 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
39. 状态=部分实现 | 条款=风险：RLS 策略遗漏导致数据泄漏。 | 参考行=134 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
40. 状态=部分实现 | 条款=回退：临时只读模式 + 高风险动作全冻结 + 强制人工审批。 | 参考行=135 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
41. 状态=部分实现 | 条款=[x] JWT 验签与 claim 校验生效。 | 参考行=139 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
42. 状态=部分实现 | 条款=[x] API 授权与审计生效。 | 参考行=140 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
43. 状态=部分实现 | 条款=[x] DB RLS 全量启用。 | 参考行=141 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
44. 状态=部分实现 | 条款=[x] Vector/Cache/Queue 隔离通过。 | 参考行=142 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
45. 状态=部分实现 | 条款=[x] 高风险审批与 CI 安全阻断通过。 | 参考行=143 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
46. 状态=部分实现 | 条款=新增 `app/security.py`： | 参考行=147 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
47. 状态=部分实现 | 条款=`app/main.py` 中间件接入 JWT 安全上下文： | 参考行=151 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
48. 状态=部分实现 | 条款=高风险审批统一错误码 `APPROVAL_REQUIRED`： | 参考行=155 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
49. 状态=部分实现 | 条款=新增密钥扫描能力： | 参考行=158 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md
50. 状态=部分实现 | 条款=新增安全合规演练脚本 `scripts/security_compliance_drill.py` 与运行手册 `docs/ops/2026-02-23-security-compliance-drill-runbook.md`，用于发布窗口审计完整性与双人复核覆盖率验证。 | 参考行=162 | 证据: app/security.py; app/db/rls.py; docs/ops/2026-02-23-security-multitenancy-evidence.md

**文件：docs/design/2026-02-22-workflow-and-worker-production-spec.md**
文件级结论：部分实现 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
1. 状态=部分实现 | 条款=将工作流执行从进程内模拟升级为真实 Worker 执行模型。 | 参考行=9 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
2. 状态=部分实现 | 条款=落实 LangGraph checkpoint 持久化恢复与 HITL 中断恢复一致性。 | 参考行=10 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
3. 状态=部分实现 | 条款=保障重试、DLQ、审计链路在并发下稳定可回放。 | 参考行=11 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
4. 状态=部分实现 | 条款=API 受理与 Worker 执行解耦。 | 参考行=17 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
5. 状态=部分实现 | 条款=`thread_id` 生命周期与 checkpoint 恢复。 | 参考行=18 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
6. 状态=部分实现 | 条款=HITL interrupt/resume token 约束。 | 参考行=19 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
7. 状态=部分实现 | 条款=Worker 并发、重试、DLQ 路由。 | 参考行=20 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
8. 状态=部分实现 | 条款=多区域 Worker 调度。 | 参考行=24 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
9. 状态=部分实现 | 条款=动态工作流 DSL 编排平台。 | 参考行=25 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
10. 状态=部分实现 | 条款=`thread_id` 已在 job 中生成并复用。 | 参考行=29 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
11. 状态=部分实现 | 条款=checkpoint 查询接口已提供。 | 参考行=30 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
12. 状态=部分实现 | 条款=`drain-once` Worker 调试接口已提供并有回归。 | 参考行=31 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
13. 状态=部分实现 | 条款=API 线程不执行长任务。 | 参考行=44 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
14. 状态=部分实现 | 条款=interrupt payload 必须 JSON 可序列化。 | 参考行=45 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
15. 状态=部分实现 | 条款=resume 仅允许单次消费且绑定 `tenant_id + evaluation_id`。 | 参考行=46 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
16. 状态=部分实现 | 条款=LangGraph 必须携带 `thread_id` 作为恢复指针。 | 参考行=47 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
17. 状态=部分实现 | 条款=`resume_token` TTL 与单次消费约束。 | 参考行=71 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
18. 状态=部分实现 | 条款=`resume_submitted` 审计事件强制写入。 | 参考行=72 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
19. 状态=部分实现 | 条款=非法 resume 返回稳定错误码。 | 参考行=73 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
20. 状态=部分实现 | 条款=任务状态机定义保持不变。 | 参考行=89 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
21. 状态=部分实现 | 条款=`job_id/thread_id/evaluation_id/resume_token` 语义不可变。 | 参考行=90 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
22. 状态=部分实现 | 条款=新增内部字段仅允许追加，不允许语义漂移。 | 参考行=91 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
23. 状态=部分实现 | 条款=`WORKER_CONCURRENCY_PARSE` | 参考行=95 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
24. 状态=部分实现 | 条款=`WORKER_CONCURRENCY_EVAL` | 参考行=96 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
25. 状态=部分实现 | 条款=`WORKER_MAX_RETRIES` | 参考行=97 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
26. 状态=部分实现 | 条款=`WORKER_RETRY_BACKOFF_BASE_MS` | 参考行=98 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
27. 状态=部分实现 | 条款=`RESUME_TOKEN_TTL_HOURS` | 参考行=99 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
28. 状态=部分实现 | 条款=`WORKFLOW_CHECKPOINT_BACKEND` | 参考行=100 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
29. 状态=部分实现 | 条款=`WORKFLOW_RUNTIME`（`langgraph|compat`） | 参考行=101 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
30. 状态=部分实现 | 条款=workflow 单测：节点流转、非法流转阻断。 | 参考行=105 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
31. 状态=部分实现 | 条款=Worker 集成：消费、重试、DLQ、恢复。 | 参考行=106 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
32. 状态=部分实现 | 条款=回放：HITL 中断恢复链路与审计链路。 | 参考行=107 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
33. 状态=部分实现 | 条款=重启恢复证明（重启前后 thread_id/checkpoint 一致）。 | 参考行=119 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
34. 状态=部分实现 | 条款=HITL 恢复成功率与失败原因统计。 | 参考行=120 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
35. 状态=部分实现 | 条款=重试/DLQ 时序回放日志。 | 参考行=121 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
36. 状态=部分实现 | 条款=并发压测结果（延迟、失败率、队列积压）。 | 参考行=122 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
37. 状态=部分实现 | 条款=API 与 Worker 职责彻底解耦。 | 参考行=126 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
38. 状态=部分实现 | 条款=checkpoint 可持久化恢复。 | 参考行=127 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
39. 状态=部分实现 | 条款=HITL 中断恢复与审计完整。 | 参考行=128 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
40. 状态=部分实现 | 条款=重试与 DLQ 时序可稳定复现。 | 参考行=129 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
41. 状态=部分实现 | 条款=风险：Worker 并发配置错误导致重复执行。 | 参考行=133 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
42. 状态=部分实现 | 条款=风险：checkpoint 持久化瓶颈导致吞吐下降。 | 参考行=134 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
43. 状态=部分实现 | 条款=回退：降并发 + 临时强制 HITL + 仅保留关键任务入队。 | 参考行=135 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
44. 状态=部分实现 | 条款=[x] Worker 常驻进程可用。 | 参考行=139 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
45. 状态=部分实现 | 条款=[x] checkpointer 真实后端可恢复。 | 参考行=140 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
46. 状态=部分实现 | 条款=[x] HITL token/审计一致性通过。 | 参考行=141 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
47. 状态=部分实现 | 条款=[x] 重试与 DLQ 时序通过。 | 参考行=142 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
48. 状态=部分实现 | 条款=[x] 并发配额压测通过。 | 参考行=143 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
49. 状态=部分实现 | 条款=新增常驻 Worker 运行时：`app/worker_runtime.py` + `scripts/run_worker.py`，支持按队列持续轮询执行。 | 参考行=147 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
50. 状态=部分实现 | 条款=队列层新增延迟可见能力（available_at）与 `nack(delay_ms)`，用于指数退避重试。 | 参考行=148 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
51. 状态=部分实现 | 条款=`run_job_once` 接入配置化重试参数：`WORKER_MAX_RETRIES`、`WORKER_RETRY_BACKOFF_BASE_MS`、`WORKER_RETRY_BACKOFF_MAX_MS`。 | 参考行=149 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
52. 状态=部分实现 | 条款=HITL token TTL 接入 `RESUME_TOKEN_TTL_HOURS` 配置，保持单次消费与租户绑定约束。 | 参考行=150 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
53. 状态=部分实现 | 条款=Worker 调度引入按 tenant 轮询与 `tenant_burst_limit`，避免单租户突发独占消费窗口。 | 参考行=151 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
54. 状态=部分实现 | 条款=新增 `WORKFLOW_RUNTIME`，默认启用 LangGraph runtime；当依赖缺失且非真栈环境时降级为兼容执行路径。 | 参考行=152 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
55. 状态=部分实现 | 条款=LangGraph runtime 使用 `interrupt`/`Command(resume=...)` 实现 HITL 中断恢复。 | 参考行=153 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md
56. 状态=部分实现 | 条款=LangGraph checkpoint 状态持久化与现有 workflow checkpoint 分离，内部标记 `langgraph_state`。 | 参考行=154 | 证据: app/langgraph_runtime.py; app/worker_runtime.py; docs/ops/2026-02-23-workflow-worker-evidence.md

**文件：docs/design/2026-02-23-object-storage-worm-spec.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
1. 状态=已实现 | 条款=将原始文档与评估报告落入对象存储，形成可审计的证据归档链路。 | 参考行=9 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
2. 状态=已实现 | 条款=提供最小 WORM 语义：写入后不可覆盖，legal hold/retention 生效时不可删除。 | 参考行=10 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
3. 状态=已实现 | 条款=与现有 API 契约（`legal-hold/*`、`storage/cleanup`）一致，不新增破坏性字段。 | 参考行=11 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
4. 状态=已实现 | 条款=原始上传文档写入对象存储。 | 参考行=17 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
5. 状态=已实现 | 条款=评估报告写入对象存储（JSON 归档）。 | 参考行=18 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
6. 状态=已实现 | 条款=`legal hold` 影响对象存储删除行为。 | 参考行=19 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
7. 状态=已实现 | 条款=`storage/cleanup` 触发对象存储删除。 | 参考行=20 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
8. 状态=已实现 | 条款=跨区域复制与多活。 | 参考行=24 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
9. 状态=已实现 | 条款=自动归档与生命周期策略编排（可在后续运维策略补充）。 | 参考行=25 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
10. 状态=已实现 | 条款=对象存储权限细粒度策略平台化。 | 参考行=26 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
11. 状态=已实现 | 条款=`put_object(tenant_id, object_type, object_id, filename, content_bytes, content_type) -> storage_uri` | 参考行=32 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
12. 状态=已实现 | 条款=`get_object(storage_uri) -> bytes` | 参考行=33 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
13. 状态=已实现 | 条款=`delete_object(storage_uri) -> deleted(bool)` | 参考行=34 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
14. 状态=已实现 | 条款=`apply_legal_hold(storage_uri) -> bool` | 参考行=35 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
15. 状态=已实现 | 条款=`release_legal_hold(storage_uri) -> bool` | 参考行=36 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
16. 状态=已实现 | 条款=`is_legal_hold_active(storage_uri) -> bool` | 参考行=37 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
17. 状态=已实现 | 条款=`set_retention(storage_uri, mode, retain_until) -> bool` | 参考行=38 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
18. 状态=已实现 | 条款=`get_retention(storage_uri) -> {mode, retain_until} | None` | 参考行=39 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
19. 状态=已实现 | 条款=`is_retention_active(storage_uri, now) -> bool` | 参考行=40 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
20. 状态=已实现 | 条款=原始文档： | 参考行=59 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
21. 状态=已实现 | 条款=评估报告： | 参考行=61 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
22. 状态=已实现 | 条款=`OBJECT_STORAGE_WORM_MODE=true` 时： | 参考行=68 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
23. 状态=已实现 | 条款=`OBJECT_STORAGE_WORM_MODE=false` 时： | 参考行=71 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
24. 状态=已实现 | 条款=`legal hold` 对象以 `storage_uri` 为粒度。 | 参考行=77 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
25. 状态=已实现 | 条款=`impose` 后必须标记对象为 `hold=true`，并在 cleanup 删除时阻断。 | 参考行=78 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
26. 状态=已实现 | 条款=`release` 必须双人复核，释放后才允许删除。 | 参考行=79 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
27. 状态=已实现 | 条款=retention 为“时间窗保全”，在 `retain_until` 之前禁止删除。 | 参考行=83 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
28. 状态=已实现 | 条款=retention 模式支持 `GOVERNANCE/COMPLIANCE`（由配置决定）。 | 参考行=84 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
29. 状态=已实现 | 条款=retention 与 legal hold 可同时存在，删除需二者都解除。 | 参考行=85 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
30. 状态=已实现 | 条款=`POST /internal/legal-hold/impose`： | 参考行=89 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
31. 状态=已实现 | 条款=`POST /internal/storage/cleanup`： | 参考行=91 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
32. 状态=已实现 | 条款=`BEA_OBJECT_STORAGE_BACKEND=local|s3` | 参考行=98 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
33. 状态=已实现 | 条款=`OBJECT_STORAGE_BUCKET`（默认 `bea`） | 参考行=99 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
34. 状态=已实现 | 条款=`OBJECT_STORAGE_ROOT`（local backend 使用） | 参考行=100 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
35. 状态=已实现 | 条款=`OBJECT_STORAGE_PREFIX`（可选） | 参考行=101 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
36. 状态=已实现 | 条款=`OBJECT_STORAGE_WORM_MODE`（默认 `true`） | 参考行=102 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
37. 状态=已实现 | 条款=`OBJECT_STORAGE_ENDPOINT`（s3 兼容） | 参考行=103 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
38. 状态=已实现 | 条款=`OBJECT_STORAGE_REGION` | 参考行=104 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
39. 状态=已实现 | 条款=`OBJECT_STORAGE_ACCESS_KEY` | 参考行=105 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
40. 状态=已实现 | 条款=`OBJECT_STORAGE_SECRET_KEY` | 参考行=106 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
41. 状态=已实现 | 条款=`OBJECT_STORAGE_FORCE_PATH_STYLE`（默认 `true`） | 参考行=107 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
42. 状态=已实现 | 条款=`OBJECT_STORAGE_RETENTION_DAYS`（默认 `0`，关闭） | 参考行=108 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
43. 状态=已实现 | 条款=`OBJECT_STORAGE_RETENTION_MODE`（默认 `GOVERNANCE`） | 参考行=109 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
44. 状态=已实现 | 条款=上传文档后对象存储存在原始文件。 | 参考行=113 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
45. 状态=已实现 | 条款=评估报告生成后对象存储存在 report.json。 | 参考行=114 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
46. 状态=已实现 | 条款=legal hold 生效后 cleanup 失败并返回 `LEGAL_HOLD_ACTIVE`。 | 参考行=115 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
47. 状态=已实现 | 条款=retention 生效后 cleanup 失败并返回 `RETENTION_ACTIVE`。 | 参考行=116 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
48. 状态=已实现 | 条款=legal hold 释放后 cleanup 删除成功并写审计日志。 | 参考行=117 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
49. 状态=已实现 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=121 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
50. 状态=已实现 | 条款=`docs/design/2026-02-21-data-model-and-storage-spec.md` | 参考行=122 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
51. 状态=已实现 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=123 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py
52. 状态=已实现 | 条款=`docs/design/2026-02-22-persistence-and-queue-production-spec.md` | 参考行=124 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; app/object_storage.py; app/store.py

**文件：docs/plans/2026-02-21-end-to-end-unified-design.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=系统定位：AI 生成“可解释评分建议”，专家做最终裁量。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=主链路：`上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`。 | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=任务模型：所有长任务异步化，状态以 `job_id` 为准。 | 参考行=11 | 证据: 待补
4. 状态=未验证 | 条款=失败模型：`failed` 为 DLQ 子流程结果，不与 DLQ 并行分叉。 | 参考行=12 | 证据: 待补
5. 状态=未验证 | 条款=隔离模型：MVP 即启用 API/DB/Vector/Cache/Queue 五层租户隔离。 | 参考行=13 | 证据: 待补
6. 状态=未验证 | 条款=发布模型：质量、性能、安全、成本四门禁同时达标才允许放量。 | 参考行=14 | 证据: 待补
7. 状态=未验证 | 条款=项目/供应商/规则管理。 | 参考行=20 | 证据: 待补
8. 状态=未验证 | 条款=文档上传、解析、分块、索引。 | 参考行=21 | 证据: 待补
9. 状态=未验证 | 条款=检索增强评分建议与证据链。 | 参考行=22 | 证据: 待补
10. 状态=未验证 | 条款=人工复核中断与恢复。 | 参考行=23 | 证据: 待补
11. 状态=未验证 | 条款=报告归档、审计、DLQ 运维。 | 参考行=24 | 证据: 待补
12. 状态=未验证 | 条款=全自动终审发布。 | 参考行=28 | 证据: 待补
13. 状态=未验证 | 条款=微服务拆分与跨服务分布式事务。 | 参考行=29 | 证据: 待补
14. 状态=未验证 | 条款=Neo4j/Milvus 主栈。 | 参考行=30 | 证据: 待补
15. 状态=未验证 | 条款=RAPTOR/GraphRAG 直接进入 MVP。 | 参考行=31 | 证据: 待补
16. 状态=未验证 | 条款=每个评分项必须有证据引用。 | 参考行=37 | 证据: 待补
17. 状态=未验证 | 条款=专家保留最终判定权与改判权。 | 参考行=38 | 证据: 待补
18. 状态=未验证 | 条款=终审记录必须保留审计链条。 | 参考行=39 | 证据: 待补
19. 状态=未验证 | 条款=任何写操作必须有幂等策略。 | 参考行=43 | 证据: 待补
20. 状态=未验证 | 条款=跨租户访问必须在 API 和 DB 双重阻断。 | 参考行=44 | 证据: 待补
21. 状态=未验证 | 条款=无 `trace_id` 的请求视为不合规请求。 | 参考行=45 | 证据: 待补
22. 状态=未验证 | 条款=审计日志不可篡改。 | 参考行=49 | 证据: 待补
23. 状态=未验证 | 条款=legal hold 对象不可被自动清理。 | 参考行=50 | 证据: 待补
24. 状态=未验证 | 条款=高风险动作必须双人复核。 | 参考行=51 | 证据: 待补
25. 状态=未验证 | 条款=以 star 数作为选型依据。 | 参考行=75 | 证据: 待补
26. 状态=未验证 | 条款=直接上重型图数据库与向量数据库组合。 | 参考行=76 | 证据: 待补
27. 状态=未验证 | 条款=复杂多 Agent 自治编排替代可控状态机。 | 参考行=77 | 证据: 待补
28. 状态=未验证 | 条款=`ingestion`：文档接收、解析、分块、入库。 | 参考行=119 | 证据: 待补
29. 状态=未验证 | 条款=`retrieval`：查询理解、检索、重排、证据打包。 | 参考行=120 | 证据: 待补
30. 状态=未验证 | 条款=`evaluation`：规则判定、LLM 评分、置信度计算。 | 参考行=121 | 证据: 待补
31. 状态=未验证 | 条款=`workflow`：状态机编排、HITL、恢复、错误路由。 | 参考行=122 | 证据: 待补
32. 状态=未验证 | 条款=`governance`：审计、权限、发布门禁、运维流程。 | 参考行=123 | 证据: 待补
33. 状态=未验证 | 条款=模块内同步调用。 | 参考行=127 | 证据: 待补
34. 状态=未验证 | 条款=模块间优先领域事件（outbox），避免隐式耦合。 | 参考行=128 | 证据: 待补
35. 状态=未验证 | 条款=外部副作用只允许在 workflow 定义的提交节点执行。 | 参考行=129 | 证据: 待补
36. 状态=未验证 | 条款=`score_confidence < 0.65` | 参考行=163 | 证据: 待补
37. 状态=未验证 | 条款=`citation_coverage < 0.90` | 参考行=164 | 证据: 待补
38. 状态=未验证 | 条款=`score_deviation_pct > 20%` | 参考行=165 | 证据: 待补
39. 状态=未验证 | 条款=命中红线规则（合规项） | 参考行=166 | 证据: 待补
40. 状态=未验证 | 条款=只能使用最新 `resume_token`。 | 参考行=170 | 证据: 待补
41. 状态=未验证 | 条款=恢复动作必须记录 `reviewer_id`、`decision`、`comment`。 | 参考行=171 | 证据: 待补
42. 状态=未验证 | 条款=恢复后流程继续到 `finalize_report`，禁止回跳到任意节点。 | 参考行=172 | 证据: 待补
43. 状态=未验证 | 条款=`content_list.json` 为定位真值；`full.md` 为结构真值。 | 参考行=178 | 证据: 待补
44. 状态=未验证 | 条款=兼容旧命名 `context_list.json`，但 canonical 名为 `content_list`。 | 参考行=179 | 证据: 待补
45. 状态=未验证 | 条款=bbox 统一归一化为 `[x0,y0,x1,y1]`。 | 参考行=180 | 证据: 待补
46. 状态=未验证 | 条款=chunk 元数据必须含 `page,bbox,heading_path,chunk_type`。 | 参考行=181 | 证据: 待补
47. 状态=未验证 | 条款=查询先标准化，再做“约束保持改写”。 | 参考行=185 | 证据: 待补
48. 状态=未验证 | 条款=模式由 selector 自动选 `local/global/hybrid/mix`。 | 参考行=186 | 证据: 待补
49. 状态=未验证 | 条款=SQL 支路只允许白名单字段，禁止自由 SQL。 | 参考行=187 | 证据: 待补
50. 状态=未验证 | 条款=最终评分由“规则引擎硬判定 + LLM 软评分”组合完成。 | 参考行=188 | 证据: 待补
51. 状态=未验证 | 条款=LangGraph checkpointer 持久化，`thread_id` 作为恢复指针。 | 参考行=192 | 证据: 待补
52. 状态=未验证 | 条款=`interrupt` 仅用于人工决策与高风险动作确认。 | 参考行=193 | 证据: 待补
53. 状态=未验证 | 条款=每个副作用节点必须声明幂等键。 | 参考行=194 | 证据: 待补
54. 状态=未验证 | 条款=重试上限 3 次，指数退避+抖动。 | 参考行=198 | 证据: 待补
55. 状态=未验证 | 条款=第 4 次失败写入 DLQ，再标记 failed。 | 参考行=199 | 证据: 待补
56. 状态=未验证 | 条款=DLQ 支持 `requeue/discard`，其中 discard 需双人复核。 | 参考行=200 | 证据: 待补
57. 状态=未验证 | 条款=API 层：`tenant_id` 只来源 JWT。 | 参考行=204 | 证据: 待补
58. 状态=未验证 | 条款=DB 层：核心表全量 `tenant_id` + RLS。 | 参考行=205 | 证据: 待补
59. 状态=未验证 | 条款=检索层：向量查询必须带 `tenant_id+project_id` 过滤。 | 参考行=206 | 证据: 待补
60. 状态=未验证 | 条款=缓存与队列：key 与消息头强制 tenant 前缀。 | 参考行=207 | 证据: 待补
61. 状态=未验证 | 条款=API `P95 <= 1.5s`（查询型接口）。 | 参考行=213 | 证据: 待补
62. 状态=未验证 | 条款=解析 `50页P95 <= 180s`。 | 参考行=214 | 证据: 待补
63. 状态=未验证 | 条款=评估 `P95 <= 120s`。 | 参考行=215 | 证据: 待补
64. 状态=未验证 | 条款=检索 `P95 <= 4s`。 | 参考行=216 | 证据: 待补
65. 状态=未验证 | 条款=RAGAS：`precision/recall >= 0.80`，`faithfulness >= 0.90`。 | 参考行=220 | 证据: 待补
66. 状态=未验证 | 条款=DeepEval：幻觉率 `<= 5%`。 | 参考行=221 | 证据: 待补
67. 状态=未验证 | 条款=citation 可回跳率 `>= 98%`。 | 参考行=222 | 证据: 待补
68. 状态=未验证 | 条款=跨租户越权事件 `= 0`。 | 参考行=226 | 证据: 待补
69. 状态=未验证 | 条款=高风险动作审计覆盖率 `= 100%`。 | 参考行=227 | 证据: 待补
70. 状态=未验证 | 条款=legal hold 对象违规删除 `= 0`。 | 参考行=228 | 证据: 待补
71. 状态=未验证 | 条款=单任务成本 P95 不高于基线 `1.2x`。 | 参考行=232 | 证据: 待补
72. 状态=未验证 | 条款=模型降级策略触发后服务可用性不低于 `99.5%`。 | 参考行=233 | 证据: 待补
73. 状态=未验证 | 条款=契约测试报告。 | 参考行=251 | 证据: 待补
74. 状态=未验证 | 条款=E2E 回放报告。 | 参考行=252 | 证据: 待补
75. 状态=未验证 | 条款=评估与压测报告。 | 参考行=253 | 证据: 待补
76. 状态=未验证 | 条款=安全回归报告。 | 参考行=254 | 证据: 待补
77. 状态=未验证 | 条款=回滚演练记录。 | 参考行=255 | 证据: 待补
78. 状态=未验证 | 条款=`docs/design/2026-02-21-implementation-plan.md` | 参考行=259 | 证据: 待补
79. 状态=未验证 | 条款=`docs/design/2026-02-21-mineru-ingestion-spec.md` | 参考行=260 | 证据: 待补
80. 状态=未验证 | 条款=`docs/design/2026-02-21-retrieval-and-scoring-spec.md` | 参考行=261 | 证据: 待补
81. 状态=未验证 | 条款=`docs/design/2026-02-21-langgraph-agent-workflow-spec.md` | 参考行=262 | 证据: 待补
82. 状态=未验证 | 条款=`docs/design/2026-02-21-rest-api-specification.md` | 参考行=263 | 证据: 待补
83. 状态=未验证 | 条款=`docs/design/2026-02-21-data-model-and-storage-spec.md` | 参考行=264 | 证据: 待补
84. 状态=未验证 | 条款=`docs/design/2026-02-21-error-handling-and-dlq-spec.md` | 参考行=265 | 证据: 待补
85. 状态=未验证 | 条款=`docs/design/2026-02-21-security-design.md` | 参考行=266 | 证据: 待补
86. 状态=未验证 | 条款=`docs/design/2026-02-21-frontend-interaction-spec.md` | 参考行=267 | 证据: 待补
87. 状态=未验证 | 条款=`docs/design/2026-02-21-testing-strategy.md` | 参考行=268 | 证据: 待补
88. 状态=未验证 | 条款=`docs/design/2026-02-21-deployment-config.md` | 参考行=269 | 证据: 待补
89. 状态=未验证 | 条款=`docs/plans/2026-02-22-production-capability-plan.md` | 参考行=270 | 证据: 待补
90. 状态=未验证 | 条款=`docs/design/2026-02-22-persistence-and-queue-production-spec.md` | 参考行=271 | 证据: 待补
91. 状态=未验证 | 条款=`docs/design/2026-02-22-parser-and-retrieval-production-spec.md` | 参考行=272 | 证据: 待补
92. 状态=未验证 | 条款=`docs/design/2026-02-22-workflow-and-worker-production-spec.md` | 参考行=273 | 证据: 待补
93. 状态=未验证 | 条款=`docs/design/2026-02-22-security-and-multitenancy-production-spec.md` | 参考行=274 | 证据: 待补
94. 状态=未验证 | 条款=`docs/design/2026-02-22-observability-and-deploy-production-spec.md` | 参考行=275 | 证据: 待补
95. 状态=未验证 | 条款=`docs/design/2026-02-23-object-storage-worm-spec.md` | 参考行=276 | 证据: 待补
96. 状态=未验证 | 条款=LangGraph docs（interrupt/checkpoint/durable execution） | 参考行=280 | 证据: 待补
97. 状态=未验证 | 条款=LangChain docs（structured output/tool strategy） | 参考行=282 | 证据: 待补
98. 状态=未验证 | 条款=FastAPI docs（BackgroundTasks/202/DI） | 参考行=284 | 证据: 待补
99. 状态=未验证 | 条款=MinerU 仓库与文档 | 参考行=286 | 证据: 待补
100. 状态=未验证 | 条款=LightRAG 仓库 | 参考行=288 | 证据: 待补
101. 状态=未验证 | 条款=RAGAS | 参考行=290 | 证据: 待补
102. 状态=未验证 | 条款=RAGChecker | 参考行=292 | 证据: 待补
103. 状态=未验证 | 条款=DeepEval | 参考行=294 | 证据: 待补
104. 状态=未验证 | 条款=superpowers skill 系统 | 参考行=296 | 证据: 待补

**文件：docs/plans/2026-02-21-gate-c-api-skeleton-design.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=`202 + job_id` 的异步受理接口。 | 参考行=11 | 证据: 待补
2. 状态=未验证 | 条款=`jobs` 状态查询接口（含状态机字段）。 | 参考行=12 | 证据: 待补
3. 状态=未验证 | 条款=HITL 恢复接口（`resume_token`）。 | 参考行=13 | 证据: 待补
4. 状态=未验证 | 条款=citation 回跳查询接口。 | 参考行=14 | 证据: 待补
5. 状态=未验证 | 条款=先测试后实现（TDD）。 | 参考行=18 | 证据: 待补
6. 状态=未验证 | 条款=仅做最小实现，不引入真实外部依赖（DB/队列/向量库）。 | 参考行=19 | 证据: 待补
7. 状态=未验证 | 条款=保持字段与 `docs/design/2026-02-21-openapi-v1.yaml` 一致。 | 参考行=20 | 证据: 待补
8. 状态=未验证 | 条款=不做“自动终审”行为，只实现契约层骨架。 | 参考行=21 | 证据: 待补
9. 状态=未验证 | 条款=FastAPI + 进程内字典保存 jobs、idempotency、citations。 | 参考行=27 | 证据: 待补
10. 状态=未验证 | 条款=用纯接口测试验证契约行为。 | 参考行=28 | 证据: 待补
11. 状态=未验证 | 条款=优点：实现快、测试稳定、适合 Gate C 最小闭环。 | 参考行=29 | 证据: 待补
12. 状态=未验证 | 条款=缺点：重启丢状态，不适用于生产。 | 参考行=30 | 证据: 待补
13. 状态=未验证 | 条款=增加 SQLModel/SQLAlchemy 与迁移。 | 参考行=34 | 证据: 待补
14. 状态=未验证 | 条款=优点：更贴近生产数据形态。 | 参考行=35 | 证据: 待补
15. 状态=未验证 | 条款=缺点：超出当前“最小骨架”范围，增加复杂度。 | 参考行=36 | 证据: 待补
16. 状态=未验证 | 条款=一步到位接近目标架构。 | 参考行=40 | 证据: 待补
17. 状态=未验证 | 条款=优点：架构一致性高。 | 参考行=41 | 证据: 待补
18. 状态=未验证 | 条款=缺点：搭建与运维成本高，不符合当前阶段速度目标。 | 参考行=42 | 证据: 待补
19. 状态=未验证 | 条款=先保证契约正确和状态机字段完整。 | 参考行=48 | 证据: 待补
20. 状态=未验证 | 条款=后续 Gate C/C+ 再把存储实现替换成 PostgreSQL/Redis。 | 参考行=49 | 证据: 待补
21. 状态=未验证 | 条款=通过 TDD 锁定接口行为，避免后续替换时语义漂移。 | 参考行=50 | 证据: 待补
22. 状态=未验证 | 条款=写接口都要求 `Idempotency-Key`。 | 参考行=54 | 证据: 待补
23. 状态=未验证 | 条款=所有响应都有 `meta.trace_id`。 | 参考行=55 | 证据: 待补
24. 状态=未验证 | 条款=异步接口返回 `202` 且含 `job_id`。 | 参考行=56 | 证据: 待补
25. 状态=未验证 | 条款=关键错误码可触发：`IDEMPOTENCY_MISSING`、`IDEMPOTENCY_CONFLICT`、`WF_INTERRUPT_RESUME_INVALID`。 | 参考行=57 | 证据: 待补
26. 状态=未验证 | 条款=`GET /jobs/{job_id}` 返回状态机允许状态集合。 | 参考行=58 | 证据: 待补

**文件：docs/plans/2026-02-21-gate-c-api-skeleton-implementation.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=Add FastAPI app factory. | 参考行=38 | 证据: 待补
2. 状态=未验证 | 条款=Add `GET /healthz` returning `{"status":"ok"}`. | 参考行=39 | 证据: 待补
3. 状态=未验证 | 条款=Assert every success response includes `meta.trace_id`. | 参考行=63 | 证据: 待补
4. 状态=未验证 | 条款=Assert errors follow `{success:false,error:{code,message,retryable,class},meta}`. | 参考行=64 | 证据: 待补
5. 状态=未验证 | 条款=Add success/error envelope builders. | 参考行=73 | 证据: 待补
6. 状态=未验证 | 条款=Add request-scoped trace id middleware. | 参考行=74 | 证据: 待补
7. 状态=未验证 | 条款=Missing `Idempotency-Key` on write endpoint -> `400 IDEMPOTENCY_MISSING`. | 参考行=98 | 证据: 待补
8. 状态=未验证 | 条款=Same key + same body -> same accepted payload. | 参考行=99 | 证据: 待补
9. 状态=未验证 | 条款=Same key + different body -> `409 IDEMPOTENCY_CONFLICT`. | 参考行=100 | 证据: 待补
10. 状态=未验证 | 条款=In-memory idempotency record keyed by `(endpoint, key)`. | 参考行=109 | 证据: 待补
11. 状态=未验证 | 条款=Stable request fingerprint for conflict detection. | 参考行=110 | 证据: 待补
12. 状态=未验证 | 条款=Reuse accepted response for idempotent replay. | 参考行=111 | 证据: 待补
13. 状态=未验证 | 条款=`POST /api/v1/documents/upload` returns `202` with `document_id/job_id/status/next`. | 参考行=135 | 证据: 待补
14. 状态=未验证 | 条款=`POST /api/v1/evaluations` returns `202` with `evaluation_id/job_id/status`. | 参考行=136 | 证据: 待补
15. 状态=未验证 | 条款=`GET /api/v1/jobs/{job_id}` returns job data with allowed status values. | 参考行=137 | 证据: 待补
16. 状态=未验证 | 条款=Unknown job id returns error envelope. | 参考行=138 | 证据: 待补
17. 状态=未验证 | 条款=Add upload/evaluation/job routes. | 参考行=147 | 证据: 待补
18. 状态=未验证 | 条款=Create jobs in store with initial `queued` status. | 参考行=148 | 证据: 待补
19. 状态=未验证 | 条款=Return envelopes aligned to OpenAPI baseline. | 参考行=149 | 证据: 待补
20. 状态=未验证 | 条款=Valid resume token returns `202` with resume job id. | 参考行=172 | 证据: 待补
21. 状态=未验证 | 条款=Invalid resume token returns `409 WF_INTERRUPT_RESUME_INVALID`. | 参考行=173 | 证据: 待补
22. 状态=未验证 | 条款=Citation source endpoint returns `document_id/page/bbox/text/context`. | 参考行=174 | 证据: 待补
23. 状态=未验证 | 条款=Unknown citation chunk returns error envelope. | 参考行=175 | 证据: 待补
24. 状态=未验证 | 条款=Add resume token registry and validation. | 参考行=184 | 证据: 待补
25. 状态=未验证 | 条款=Add citation source in-memory dataset and lookup route. | 参考行=185 | 证据: 待补

**文件：docs/plans/2026-02-22-production-capability-plan.md**
文件级结论：部分实现 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
1. 状态=部分实现 | 条款=当前阶段完成了 Gate C-F 的“流程骨架可运行”。 | 参考行=15 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
2. 状态=部分实现 | 条款=现阶段目标是将骨架替换为可生产运行的真实能力。 | 参考行=16 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
3. 状态=部分实现 | 条款=本阶段不是推翻重写，而是在既有状态机、错误码、契约之上逐项替换实现。 | 参考行=17 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
4. 状态=部分实现 | 条款=`main` 已包含 Gate C-F 契约与测试基线。 | 参考行=23 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
5. 状态=部分实现 | 条款=OpenAPI 与 REST 规范可解析且无冲突。 | 参考行=24 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
6. 状态=部分实现 | 条款=全量测试基线通过。 | 参考行=25 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
7. 状态=部分实现 | 条款=InMemory 关键路径已替换为真实存储与队列。 | 参考行=29 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
8. 状态=部分实现 | 条款=解析、检索、评分链路由真实适配器驱动。 | 参考行=30 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
9. 状态=部分实现 | 条款=LangGraph checkpoint 与 interrupt/resume 可持久化恢复。 | 参考行=31 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
10. 状态=部分实现 | 条款=API/DB/Vector/Cache/Queue 五层租户隔离通过回归。 | 参考行=32 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
11. 状态=部分实现 | 条款=发布流水线具备可执行灰度、回滚、回放验证。 | 参考行=33 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
12. 状态=部分实现 | 条款=`docs/design/2026-02-22-persistence-and-queue-production-spec.md` | 参考行=37 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
13. 状态=部分实现 | 条款=`docs/design/2026-02-22-parser-and-retrieval-production-spec.md` | 参考行=38 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
14. 状态=部分实现 | 条款=`docs/design/2026-02-22-workflow-and-worker-production-spec.md` | 参考行=39 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
15. 状态=部分实现 | 条款=`docs/design/2026-02-22-security-and-multitenancy-production-spec.md` | 参考行=40 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
16. 状态=部分实现 | 条款=`docs/design/2026-02-22-observability-and-deploy-production-spec.md` | 参考行=41 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
17. 状态=部分实现 | 条款=Repository 层替换 InMemory 关键路径。 | 参考行=59 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
18. 状态=部分实现 | 条款=PostgreSQL 迁移与索引、RLS 策略落地。 | 参考行=60 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
19. 状态=部分实现 | 条款=Redis 队列与幂等、锁、缓存命名规范落地。 | 参考行=61 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
20. 状态=部分实现 | 条款=outbox 事件表与消费幂等落地。 | 参考行=62 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
21. 状态=部分实现 | 条款=MinerU/Docling/OCR 适配器统一接口落地。 | 参考行=66 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
22. 状态=部分实现 | 条款=parse manifest 与 chunk 元数据真实入库。 | 参考行=67 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
23. 状态=部分实现 | 条款=LightRAG 检索链路与 metadata 过滤真实化。 | 参考行=68 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
24. 状态=部分实现 | 条款=rerank 降级与约束保持改写真实化。 | 参考行=69 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
25. 状态=部分实现 | 条款=LangGraph checkpointer 使用持久化后端。 | 参考行=73 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
26. 状态=部分实现 | 条款=`thread_id` 生成、传递、恢复策略落地。 | 参考行=74 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
27. 状态=部分实现 | 条款=HITL interrupt/resume 与审计一致性落地。 | 参考行=75 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
28. 状态=部分实现 | 条款=Worker 并发、重试、DLQ 路由真实执行。 | 参考行=76 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
29. 状态=部分实现 | 条款=JWT 可信来源与租户注入链路落地。 | 参考行=80 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
30. 状态=部分实现 | 条款=API 层越权阻断与审计落地。 | 参考行=81 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
31. 状态=部分实现 | 条款=DB RLS 与向量检索 metadata 过滤一致化。 | 参考行=82 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
32. 状态=部分实现 | 条款=高风险动作审批策略强制执行。 | 参考行=83 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
33. 状态=部分实现 | 条款=指标、日志、Trace 三件套统一语义落地。 | 参考行=87 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
34. 状态=部分实现 | 条款=SLO 与告警分级（P0/P1/P2）落地。 | 参考行=88 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
35. 状态=部分实现 | 条款=staging 回放、canary、rollback 脚本化。 | 参考行=89 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
36. 状态=部分实现 | 条款=事故 runbook 与变更管理与流水线联动。 | 参考行=90 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
37. 状态=部分实现 | 条款=契约测试报告。 | 参考行=96 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
38. 状态=部分实现 | 条款=集成/回放证据。 | 参考行=97 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
39. 状态=部分实现 | 条款=性能/安全关键指标。 | 参考行=98 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
40. 状态=部分实现 | 条款=回滚演练记录。 | 参考行=99 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
41. 状态=部分实现 | 条款=真栈 E2E 跑通（上传 -> 解析 -> 检索 -> 评估 -> HITL -> 报告）。 | 参考行=103 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
42. 状态=部分实现 | 条款=四门禁与 Gate E/F 控制面可在真栈执行。 | 参考行=104 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
43. 状态=部分实现 | 条款=30 分钟内可完成回滚并完成回放验证。 | 参考行=105 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
44. 状态=部分实现 | 条款=风险：真实组件接入导致契约漂移。 | 参考行=109 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
45. 状态=部分实现 | 条款=控制：文档先改、契约先测、再替换实现。 | 参考行=110 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
46. 状态=部分实现 | 条款=回退：任一轨道异常时只回退该轨道实现，不破坏已通过轨道。 | 参考行=111 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
47. 状态=部分实现 | 条款=本计划是生产能力阶段总计划。 | 参考行=115 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
48. 状态=部分实现 | 条款=`docs/design/2026-02-21-implementation-plan.md` 仍是 Gate A-F 总计划。 | 参考行=116 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
49. 状态=部分实现 | 条款=本计划不替代 SSOT，只补充“骨架到生产化”的执行路径。 | 参考行=117 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
50. 状态=部分实现 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=121 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
51. 状态=部分实现 | 条款=`docs/design/2026-02-21-implementation-plan.md` | 参考行=122 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
52. 状态=部分实现 | 条款=`docs/design/2026-02-21-openapi-v1.yaml` | 参考行=123 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
53. 状态=部分实现 | 条款=主链路以真栈运行：API 受理、Worker 执行、真实存储与真实队列、真实解析与检索、真实门禁与发布准入。 | 参考行=129 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
54. 状态=部分实现 | 条款=所有关键流程可追溯：任一 `job_id/evaluation_id/thread_id` 可追到日志、审计、checkpoint、回放结果。 | 参考行=130 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
55. 状态=部分实现 | 条款=多租户隔离具备工程化防线：API/DB/Vector/Cache/Queue 全链路阻断跨租户访问。 | 参考行=131 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
56. 状态=部分实现 | 条款=发布具备可控性：灰度、回滚、回放与准入评估可以重复执行，不依赖人工临场判断。 | 参考行=132 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
57. 状态=部分实现 | 条款=真实组件替换尚未完成的部分（若仍存在 sqlite/memory 路径，需全部下线）。 | 参考行=138 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
58. 状态=部分实现 | 条款=生产环境 SLO 基线与容量压测（峰值、故障注入、恢复时间）需形成正式报告。 | 参考行=139 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
59. 状态=部分实现 | 条款=安全合规闭环（密钥治理、审计留存、审批策略）需经过一次完整演练并归档。 | 参考行=140 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
60. 状态=部分实现 | 条款=自动化运维深度：告警抑制、自动降级、自动回放编排。 | 参考行=144 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
61. 状态=部分实现 | 条款=评估数据集治理：反例集与黄金集迭代策略精细化。 | 参考行=145 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
62. 状态=部分实现 | 条款=成本治理：模型路由精调、预算预测与告警精度优化。 | 参考行=146 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
63. 状态=部分实现 | 条款=多区域容灾与跨地域部署。 | 参考行=150 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
64. 状态=部分实现 | 条款=更细粒度的权限模型与策略平台化。 | 参考行=151 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md
65. 状态=部分实现 | 条款=高级检索优化（图谱增强、跨文档结构化推理）。 | 参考行=152 | 证据: docs/ops/2026-02-23-end-to-end-implementation-status.md

**文件：docs/plans/2026-02-23-post-n1-n5-implementation-plan.md**
文件级结论：已实现 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
1. 状态=已实现 | 条款=真实 WORM 合规保全 API 接入与证据化。 | 参考行=14 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
2. 状态=已实现 | 条款=LangGraph 真 runtime 图执行替换与完整持久化恢复。 | 参考行=15 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
3. 状态=已实现 | 条款=解析/检索/评分深度实现与一致性治理。 | 参考行=16 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
4. 状态=已实现 | 条款=前端 E2E 自动化与引用高亮真实化。 | 参考行=17 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
5. 状态=已实现 | 条款=Gate D/E/F 真实环境下的再次验收与证据归档。 | 参考行=18 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
6. 状态=已实现 | 条款=微服务拆分。 | 参考行=21 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
7. 状态=已实现 | 条款=改写 SSOT 范围或引入新的主栈。 | 参考行=22 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
8. 状态=已实现 | 条款=引入复杂图数据库替代当前主流程。 | 参考行=23 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
9. 状态=已实现 | 条款=N1-N5 已完成并有证据归档。 | 参考行=28 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
10. 状态=已实现 | 条款=OpenAPI 与 REST 文档未出现契约漂移。 | 参考行=29 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
11. 状态=已实现 | 条款=全量测试基线可通过。 | 参考行=30 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
12. 状态=已实现 | 条款=真实 WORM API 对接完成，并有合规证据。 | 参考行=33 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
13. 状态=已实现 | 条款=LangGraph runtime 全替换，不再依赖兼容路径。 | 参考行=34 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
14. 状态=已实现 | 条款=解析/检索/评分主链路达到 SSOT 目标行为。 | 参考行=35 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
15. 状态=已实现 | 条款=前端关键流程 E2E 证据齐全。 | 参考行=36 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
16. 状态=已实现 | 条款=Gate D/E/F 在真实环境下重新验收通过。 | 参考行=37 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
17. 状态=已实现 | 条款=对接对象存储合规保全 API（示例：S3 Object Lock/Retention/Legal Hold）。 | 参考行=52 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
18. 状态=已实现 | 条款=合规策略变更全链路审计化。 | 参考行=53 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
19. 状态=已实现 | 条款=清理与释放行为严格受保全策略约束。 | 参考行=54 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
20. 状态=已实现 | 条款=审计日志不可篡改，legal hold 对象不可被自动清理。 | 参考行=57 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
21. 状态=已实现 | 条款=legal hold release 属高风险动作，需双人复核。 | 参考行=58 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
22. 状态=已实现 | 条款=归档对象必须可由 `storage_uri/report_uri` 追溯。 | 参考行=59 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
23. 状态=已实现 | 条款=`docs/design/2026-02-23-object-storage-worm-spec.md`。 | 参考行=62 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
24. 状态=已实现 | 条款=现有对象存储适配层实现。 | 参考行=63 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
25. 状态=已实现 | 条款=对象存储合规模块与配置说明。 | 参考行=66 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
26. 状态=已实现 | 条款=真实保全状态变更审计记录。 | 参考行=67 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
27. 状态=已实现 | 条款=适配层的集成测试与证据。 | 参考行=68 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
28. 状态=已实现 | 条款=legal hold + retention 均可实际生效并可查询。 | 参考行=71 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
29. 状态=已实现 | 条款=处于保全的对象删除严格失败并记录审计。 | 参考行=72 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
30. 状态=已实现 | 条款=证据文档包含命令、输出与时间窗口。 | 参考行=73 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
31. 状态=已实现 | 条款=保留现有流程约束路径作为兼容开关。 | 参考行=76 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
32. 状态=已实现 | 条款=回退不影响已归档对象的保全状态。 | 参考行=77 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
33. 状态=已实现 | 条款=使用真实 LangGraph 节点图执行替换兼容路径。 | 参考行=82 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
34. 状态=已实现 | 条款=checkpointer/interrupt/resume 全链路真实持久化。 | 参考行=83 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
35. 状态=已实现 | 条款=typed edges 与节点副作用边界可追溯。 | 参考行=84 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
36. 状态=已实现 | 条款=checkpointer 必须携带 `thread_id` 持久化恢复。 | 参考行=87 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
37. 状态=已实现 | 条款=HITL 仅使用 `interrupt`/`Command(resume=...)`，负载 JSON 可序列化。 | 参考行=88 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
38. 状态=已实现 | 条款=每个副作用节点必须声明幂等键。 | 参考行=89 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
39. 状态=已实现 | 条款=`docs/design/2026-02-22-workflow-and-worker-production-spec.md`。 | 参考行=92 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
40. 状态=已实现 | 条款=现有 runtime 兼容实现。 | 参考行=93 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
41. 状态=已实现 | 条款=LangGraph 图定义与运行时适配层。 | 参考行=96 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
42. 状态=已实现 | 条款=workflow 集成测试与回放证据。 | 参考行=97 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
43. 状态=已实现 | 条款=中断与恢复操作的审计与追踪。 | 参考行=98 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
44. 状态=已实现 | 条款=强制启用 LangGraph runtime 后所有流程可运行。 | 参考行=101 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
45. 状态=已实现 | 条款=`thread_id` 持久化恢复在 worker 重启后仍可继续。 | 参考行=102 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
46. 状态=已实现 | 条款=DLQ 与失败路径时序不回退。 | 参考行=103 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
47. 状态=已实现 | 条款=保留兼容路径开关，仅用于临时应急。 | 参考行=106 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
48. 状态=已实现 | 条款=回退时必须补一次回放验证。 | 参考行=107 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
49. 状态=已实现 | 条款=解析链路完全对齐 SSOT 结构字段。 | 参考行=112 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
50. 状态=已实现 | 条款=检索与评分策略可配置化且可验证。 | 参考行=113 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
51. 状态=已实现 | 条款=引用覆盖与置信度规则与 HITL 策略一致。 | 参考行=114 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
52. 状态=已实现 | 条款=`content_list.json` 为定位真值，`full.md` 为结构真值。 | 参考行=117 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
53. 状态=已实现 | 条款=bbox 归一化为 `[x0,y0,x1,y1]`，引用对象含 `page,bbox,heading_path,chunk_type`。 | 参考行=118 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
54. 状态=已实现 | 条款=HITL 触发条件满足 `score_confidence/citation_coverage/score_deviation_pct` 规则。 | 参考行=119 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
55. 状态=已实现 | 条款=`docs/design/2026-02-22-parser-and-retrieval-production-spec.md`。 | 参考行=122 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
56. 状态=已实现 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md`。 | 参考行=123 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
57. 状态=已实现 | 条款=解析器与检索器统一接口及参数约束。 | 参考行=126 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
58. 状态=已实现 | 条款=评分规则与置信度计算模块。 | 参考行=127 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
59. 状态=已实现 | 条款=解析、检索、评分的集成测试与证据。 | 参考行=128 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
60. 状态=已实现 | 条款=每个评分项有可回跳引用并满足覆盖率阈值。 | 参考行=131 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
61. 状态=已实现 | 条款=`score_confidence/citation_coverage` 与 HITL 触发一致。 | 参考行=132 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
62. 状态=已实现 | 条款=评估链路回放结果与黄金集对齐。 | 参考行=133 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
63. 状态=已实现 | 条款=允许降级为保守检索模式，但需记录原因。 | 参考行=136 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
64. 状态=已实现 | 条款=回退后需要更新证据并标注差异。 | 参考行=137 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
65. 状态=已实现 | 条款=上传->评估->HITL->报告全流程 E2E 自动化。 | 参考行=142 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
66. 状态=已实现 | 条款=citation 回跳与 bbox 高亮对接真实解析坐标。 | 参考行=143 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
67. 状态=已实现 | 条款=权限与双人复核交互一致化。 | 参考行=144 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
68. 状态=已实现 | 条款=主链路必须覆盖 `上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`。 | 参考行=147 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
69. 状态=已实现 | 条款=高风险动作双人复核前端必须可见且阻断执行。 | 参考行=148 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
70. 状态=已实现 | 条款=引用回跳必须基于解析定位字段（`page/bbox`），报告可追溯 `report_uri`。 | 参考行=149 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
71. 状态=已实现 | 条款=`docs/design/2026-02-21-frontend-interaction-spec.md`。 | 参考行=152 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
72. 状态=已实现 | 条款=当前前端引用面板与权限实现。 | 参考行=153 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
73. 状态=已实现 | 条款=前端 E2E 测试脚本与证据。 | 参考行=156 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
74. 状态=已实现 | 条款=引用回跳与高亮的实测截图与日志。 | 参考行=157 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
75. 状态=已实现 | 条款=角色门控与审批交互证据。 | 参考行=158 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
76. 状态=已实现 | 条款=E2E 覆盖关键路径并可重复执行。 | 参考行=161 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
77. 状态=已实现 | 条款=引用回跳定位准确，bbox 位置一致。 | 参考行=162 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
78. 状态=已实现 | 条款=高风险动作必须双 reviewer 才能完成。 | 参考行=163 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
79. 状态=已实现 | 条款=若高亮对齐失败，需回退为引用证据列表展示。 | 参考行=166 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
80. 状态=已实现 | 条款=回退必须标注原因与补偿方案。 | 参考行=167 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
81. 状态=已实现 | 条款=Gate D 四门禁在真实环境复验。 | 参考行=172 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
82. 状态=已实现 | 条款=Gate E 灰度与回滚演练证据齐全。 | 参考行=173 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
83. 状态=已实现 | 条款=Gate F 运营优化有可量化改进指标。 | 参考行=174 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
84. 状态=已实现 | 条款=质量、性能、安全、成本四门禁同时达标才允许放量。 | 参考行=177 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
85. 状态=已实现 | 条款=回滚触发后 30 分钟内恢复服务并完成回放验证。 | 参考行=178 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
86. 状态=已实现 | 条款=高风险任务始终保留 HITL，放量审批与回放结果入审计链。 | 参考行=179 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
87. 状态=已实现 | 条款=`docs/design/2026-02-22-gate-d-four-gates-checklist.md`。 | 参考行=182 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
88. 状态=已实现 | 条款=`docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md`。 | 参考行=183 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
89. 状态=已实现 | 条款=`docs/design/2026-02-22-gate-f-operations-optimization-checklist.md`。 | 参考行=184 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
90. 状态=已实现 | 条款=四门禁复验报告与指标快照。 | 参考行=187 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
91. 状态=已实现 | 条款=灰度、回滚与回放证据包。 | 参考行=188 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
92. 状态=已实现 | 条款=运营优化前后对比数据。 | 参考行=189 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
93. 状态=已实现 | 条款=质量、性能、安全、成本门禁全部达标。 | 参考行=192 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
94. 状态=已实现 | 条款=30 分钟内完成回滚并通过回放验证。 | 参考行=193 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
95. 状态=已实现 | 条款=两轮运营优化指标连续改善。 | 参考行=194 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
96. 状态=已实现 | 条款=回滚到前一稳定版本并记录审计。 | 参考行=197 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
97. 状态=已实现 | 条款=必须阻止继续放量。 | 参考行=198 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
98. 状态=已实现 | 条款=文档变更记录。 | 参考行=203 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
99. 状态=已实现 | 条款=测试/回放/演练输出。 | 参考行=204 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
100. 状态=已实现 | 条款=运行日志与审计记录。 | 参考行=205 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
101. 状态=已实现 | 条款=结论与风险说明。 | 参考行=206 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
102. 状态=已实现 | 条款=N6 真实 WORM API 接入：已完成并有证据。 | 参考行=210 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
103. 状态=已实现 | 条款=N7 LangGraph 真 runtime 替换：已完成并有证据。 | 参考行=211 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
104. 状态=已实现 | 条款=N8 解析/检索/评分深度实现：已完成并有证据。 | 参考行=212 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
105. 状态=已实现 | 条款=N9 前端 E2E 与引用真实化：已完成并有证据。 | 参考行=213 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
106. 状态=已实现 | 条款=N10 Gate D/E/F 真实验收与准入归档：已完成并有证据。 | 参考行=214 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
107. 状态=已实现 | 条款=`docs/ops/2026-02-23-n6-worm-api-evidence.md` | 参考行=217 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
108. 状态=已实现 | 条款=`docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md` | 参考行=218 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
109. 状态=已实现 | 条款=`docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md` | 参考行=219 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
110. 状态=已实现 | 条款=`docs/ops/2026-02-23-n9-frontend-e2e-evidence.md` | 参考行=220 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
111. 状态=已实现 | 条款=`docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md` | 参考行=221 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
112. 状态=已实现 | 条款=真实组件接入导致契约漂移。 | 参考行=226 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
113. 状态=已实现 | 条款=替换 runtime 引入状态机不一致。 | 参考行=227 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
114. 状态=已实现 | 条款=解析与检索的性能回退。 | 参考行=228 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
115. 状态=已实现 | 条款=所有变更先更新文档契约与证据模板。 | 参考行=231 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
116. 状态=已实现 | 条款=引入回放测试作为回归门禁。 | 参考行=232 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
117. 状态=已实现 | 条款=关键性能指标设定阈值并触发自动回滚。 | 参考行=233 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
118. 状态=已实现 | 条款=`docs/plans/2026-02-21-end-to-end-unified-design.md` | 参考行=237 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
119. 状态=已实现 | 条款=`docs/design/2026-02-21-implementation-plan.md` | 参考行=238 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
120. 状态=已实现 | 条款=`docs/plans/2026-02-22-production-capability-plan.md` | 参考行=239 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md
121. 状态=已实现 | 条款=`docs/ops/2026-02-23-end-to-end-implementation-status.md` | 参考行=240 | 证据: docs/ops/2026-02-23-n6-worm-api-evidence.md; docs/ops/2026-02-23-n7-langgraph-runtime-evidence.md; docs/ops/2026-02-23-n8-parser-retrieval-scoring-evidence.md; docs/ops/2026-02-23-n9-frontend-e2e-evidence.md; docs/ops/2026-02-23-n10-gate-def-revalidation-evidence.md

**文件：docs/plans/2026-02-23-session-handoff.md**
文件级结论：未验证 | 证据: 待补
1. 状态=未验证 | 条款=仓库状态：`main` 与 `origin/main` 对齐，工作区干净。 | 参考行=9 | 证据: 待补
2. 状态=未验证 | 条款=已完成阶段： | 参考行=10 | 证据: 待补
3. 状态=未验证 | 条款=最近关键落地： | 参考行=13 | 证据: 待补
4. 状态=未验证 | 条款=当前全量验证结果： | 参考行=16 | 证据: 待补
5. 状态=未验证 | 条款=`trace_id` 严格合规：支持 `TRACE_ID_STRICT_REQUIRED=true` 时强制请求携带 `x-trace-id`。 | 参考行=22 | 证据: 待补
6. 状态=未验证 | 条款=高风险动作双人复核：`dlq_discard`、`legal_hold_release` 已强制双 reviewer。 | 参考行=23 | 证据: 待补
7. 状态=未验证 | 条款=`legal hold` 生命周期：impose/list/release/cleanup 阻断链路已落地。 | 参考行=24 | 证据: 待补
8. 状态=未验证 | 条款=审计完整性：审计日志包含 `prev_hash/audit_hash`，并提供完整性校验接口。 | 参考行=25 | 证据: 待补
9. 状态=未验证 | 条款=健康接口对齐：`GET /api/v1/health` 已补齐。 | 参考行=26 | 证据: 待补
10. 状态=未验证 | 条款=Object Storage WORM 仍是流程约束层，尚未接入真实对象存储保全策略 API。 | 参考行=30 | 证据: 待补
11. 状态=未验证 | 条款=LangGraph 仍为兼容语义实现，尚未替换为完整 runtime 节点图执行。 | 参考行=31 | 证据: 待补
12. 状态=未验证 | 条款=项目/供应商/规则管理完整资源接口仍未实现（目前文档标注为规划）。 | 参考行=32 | 证据: 待补
13. 状态=未验证 | 条款=前端 citation 回跳 + bbox 高亮 + 角色门控仍待实现。 | 参考行=33 | 证据: 待补
14. 状态=未验证 | 条款=接入对象存储适配层（最小可先做 S3/MinIO 兼容）。 | 参考行=41 | 证据: 待补
15. 状态=未验证 | 条款=报告与原始证据写入对象存储并可标记 legal hold。 | 参考行=42 | 证据: 待补
16. 状态=未验证 | 条款=cleanup 流程对 hold 对象保持硬阻断。 | 参考行=43 | 证据: 待补
17. 状态=未验证 | 条款=有可运行适配器与 API/服务调用链。 | 参考行=47 | 证据: 待补
18. 状态=未验证 | 条款=有集成测试（含 hold 状态下删除阻断）。 | 参考行=48 | 证据: 待补
19. 状态=未验证 | 条款=有 runbook 与证据文档。 | 参考行=49 | 证据: 待补
20. 状态=未验证 | 条款=用真实 LangGraph 状态图替换当前兼容执行路径。 | 参考行=55 | 证据: 待补
21. 状态=未验证 | 条款=checkpoint/interrupt/resume 与 `thread_id` 持久化全打通。 | 参考行=56 | 证据: 待补
22. 状态=未验证 | 条款=现有 resume/checkpoint 回归测试继续通过。 | 参考行=60 | 证据: 待补
23. 状态=未验证 | 条款=新增 workflow runtime 集成测试通过。 | 参考行=61 | 证据: 待补
24. 状态=未验证 | 条款=失败重试与 DLQ 时序不回退。 | 参考行=62 | 证据: 待补
25. 状态=未验证 | 条款=按现有契约补齐资源 CRUD（至少 `list/create/get/update`）。 | 参考行=68 | 证据: 待补
26. 状态=未验证 | 条款=全链路租户隔离 + 审计 + 幂等保持一致。 | 参考行=69 | 证据: 待补
27. 状态=未验证 | 条款=OpenAPI 与 REST 文档同步。 | 参考行=73 | 证据: 待补
28. 状态=未验证 | 条款=契约测试覆盖核心路径。 | 参考行=74 | 证据: 待补
29. 状态=未验证 | 条款=与评估主链路联调可用。 | 参考行=75 | 证据: 待补
30. 状态=未验证 | 条款=评估页证据面板 + citation 回跳 + bbox 高亮。 | 参考行=81 | 证据: 待补
31. 状态=未验证 | 条款=角色门控（admin/agent/evaluator/viewer）与高风险操作确认流。 | 参考行=82 | 证据: 待补
32. 状态=未验证 | 条款=前端 E2E 至少覆盖：上传->评估->HITL->报告、DLQ 操作。 | 参考行=86 | 证据: 待补
33. 状态=未验证 | 条款=关键交互满足前端规范文档。 | 参考行=87 | 证据: 待补
34. 状态=未验证 | 条款=staging 跑一次 SLO/故障注入/恢复演练。 | 参考行=93 | 证据: 待补
35. 状态=未验证 | 条款=跑一次安全合规演练（双人复核、审计完整性、密钥扫描）。 | 参考行=94 | 证据: 待补
36. 状态=未验证 | 条款=形成完整证据包（命令、结果、时间窗口、结论）。 | 参考行=98 | 证据: 待补
37. 状态=未验证 | 条款=与 Gate E/F 准入流程文档一致。 | 参考行=99 | 证据: 待补
38. 状态=未验证 | 条款=先阅读： | 参考行=103 | 证据: 待补
39. 状态=未验证 | 条款=直接从 N1 开始实现，并遵循“文档先更新，再改实现，再补验证证据”。 | 参考行=107 | 证据: 待补
