# 会话交接与下一步计划（Session Handoff）

> 日期：2026-02-23  
> 基线分支：`main`  
> 基线提交：`2345381`

## 1. 当前状态

1. 仓库状态：`main` 与 `origin/main` 对齐，工作区干净。
2. 已完成阶段：
   - Gate A-F（骨架与门禁链路）。
   - 生产能力阶段 P0-P6（存储/队列、解析检索、工作流、租户安全、观测发布、准入回放）。
3. 最近关键落地：
   - `2345381`：SSOT 缺口收口（trace 严格模式、双人复核、legal hold、审计完整性）。
   - `773b775`：前端 Vue3 骨架（核心路由与 API 接线）。
4. 当前全量验证结果：
   - `pytest -q` 通过。
   - `python3 scripts/security_secret_scan.py` 通过（0 finding）。

## 2. 已补齐的 SSOT 关键能力

1. `trace_id` 严格合规：支持 `TRACE_ID_STRICT_REQUIRED=true` 时强制请求携带 `x-trace-id`。
2. 高风险动作双人复核：`dlq_discard`、`legal_hold_release` 已强制双 reviewer。
3. `legal hold` 生命周期：impose/list/release/cleanup 阻断链路已落地。
4. 审计完整性：审计日志包含 `prev_hash/audit_hash`，并提供完整性校验接口。
5. 健康接口对齐：`GET /api/v1/health` 已补齐。

## 3. 仍未完全达成的目标（相对 SSOT 完全体）

1. Object Storage WORM 仍是流程约束层，尚未接入真实对象存储保全策略 API。
2. LangGraph 仍为兼容语义实现，尚未替换为完整 runtime 节点图执行。
3. 项目/供应商/规则管理完整资源接口仍未实现（目前文档标注为规划）。
4. 前端 citation 回跳 + bbox 高亮 + 角色门控仍待实现。

## 4. 下一会话执行顺序（建议）

### 4.1 N1：真实 WORM 保全接入（后端）

目标：

1. 接入对象存储适配层（最小可先做 S3/MinIO 兼容）。
2. 报告与原始证据写入对象存储并可标记 legal hold。
3. cleanup 流程对 hold 对象保持硬阻断。

完成标准：

1. 有可运行适配器与 API/服务调用链。
2. 有集成测试（含 hold 状态下删除阻断）。
3. 有 runbook 与证据文档。

### 4.2 N2：LangGraph runtime 真替换（工作流）

目标：

1. 用真实 LangGraph 状态图替换当前兼容执行路径。
2. checkpoint/interrupt/resume 与 `thread_id` 持久化全打通。

完成标准：

1. 现有 resume/checkpoint 回归测试继续通过。
2. 新增 workflow runtime 集成测试通过。
3. 失败重试与 DLQ 时序不回退。

### 4.3 N3：业务资源 API 补全（projects/suppliers/rules）

目标：

1. 按现有契约补齐资源 CRUD（至少 `list/create/get/update`）。
2. 全链路租户隔离 + 审计 + 幂等保持一致。

完成标准：

1. OpenAPI 与 REST 文档同步。
2. 契约测试覆盖核心路径。
3. 与评估主链路联调可用。

### 4.4 N4：前端能力收口（引用回跳与权限）

目标：

1. 评估页证据面板 + citation 回跳 + bbox 高亮。
2. 角色门控（admin/agent/evaluator/viewer）与高风险操作确认流。

完成标准：

1. 前端 E2E 至少覆盖：上传->评估->HITL->报告、DLQ 操作。
2. 关键交互满足前端规范文档。

### 4.5 N5：生产演练证据归档

目标：

1. staging 跑一次 SLO/故障注入/恢复演练。
2. 跑一次安全合规演练（双人复核、审计完整性、密钥扫描）。

完成标准：

1. 形成完整证据包（命令、结果、时间窗口、结论）。
2. 与 Gate E/F 准入流程文档一致。

## 5. 新会话启动建议

1. 先阅读：
   - `docs/plans/2026-02-21-end-to-end-unified-design.md`
   - `docs/plans/2026-02-22-production-capability-plan.md`
   - `docs/ops/2026-02-23-ssot-gap-closure.md`
2. 直接从 N1 开始实现，并遵循“文档先更新，再改实现，再补验证证据”。
