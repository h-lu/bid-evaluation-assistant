# 端到端统一方案后续实施计划（N6+）

> 日期：2026-02-23  
> 适用范围：Gate A-F 与 N1-N5 完成之后  
> 对齐 SSOT：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标与定位

本计划用于 N1-N5 收口后的后续实施，聚焦 SSOT 完全体尚未达到的能力与发布级工程化。原则是“文档先更新、再替换实现、证据驱动验收”。

## 2. 范围与非目标

范围：
1. 真实 WORM 合规保全 API 接入与证据化。
2. LangGraph 真 runtime 图执行替换与完整持久化恢复。
3. 解析/检索/评分深度实现与一致性治理。
4. 前端 E2E 自动化与引用高亮真实化。
5. Gate D/E/F 真实环境下的再次验收与证据归档。

非目标：
1. 微服务拆分。
2. 改写 SSOT 范围或引入新的主栈。
3. 引入复杂图数据库替代当前主流程。

## 3. 入口与出口

入口条件：
1. N1-N5 已完成并有证据归档。
2. OpenAPI 与 REST 文档未出现契约漂移。
3. 全量测试基线可通过。

出口条件：
1. 真实 WORM API 对接完成，并有合规证据。
2. LangGraph runtime 全替换，不再依赖兼容路径。
3. 解析/检索/评分主链路达到 SSOT 目标行为。
4. 前端关键流程 E2E 证据齐全。
5. Gate D/E/F 在真实环境下重新验收通过。

## 4. 执行顺序（必须）

```text
N6 真实 WORM API 接入
 -> N7 LangGraph 真 runtime 替换
 -> N8 解析/检索/评分深度实现
 -> N9 前端 E2E 与引用真实化
 -> N10 Gate D/E/F 真实验收与准入归档
```

## 5. N6 真实 WORM API 接入

目标：
1. 对接对象存储合规保全 API（示例：S3 Object Lock/Retention/Legal Hold）。
2. 合规策略变更全链路审计化。
3. 清理与释放行为严格受保全策略约束。

SSOT 对齐要点：
1. 审计日志不可篡改，legal hold 对象不可被自动清理。
2. legal hold release 属高风险动作，需双人复核。
3. 归档对象必须可由 `storage_uri/report_uri` 追溯。

输入：
1. `docs/design/2026-02-23-object-storage-worm-spec.md`。
2. 现有对象存储适配层实现。

产出：
1. 对象存储合规模块与配置说明。
2. 真实保全状态变更审计记录。
3. 适配层的集成测试与证据。

验收：
1. legal hold + retention 均可实际生效并可查询。
2. 处于保全的对象删除严格失败并记录审计。
3. 证据文档包含命令、输出与时间窗口。

回退：
1. 保留现有流程约束路径作为兼容开关。
2. 回退不影响已归档对象的保全状态。

## 6. N7 LangGraph 真 runtime 替换

目标：
1. 使用真实 LangGraph 节点图执行替换兼容路径。
2. checkpointer/interrupt/resume 全链路真实持久化。
3. typed edges 与节点副作用边界可追溯。

SSOT 对齐要点：
1. checkpointer 必须携带 `thread_id` 持久化恢复。
2. HITL 仅使用 `interrupt`/`Command(resume=...)`，负载 JSON 可序列化。
3. 每个副作用节点必须声明幂等键。

输入：
1. `docs/design/2026-02-22-workflow-and-worker-production-spec.md`。
2. 现有 runtime 兼容实现。

产出：
1. LangGraph 图定义与运行时适配层。
2. workflow 集成测试与回放证据。
3. 中断与恢复操作的审计与追踪。

验收：
1. 强制启用 LangGraph runtime 后所有流程可运行。
2. `thread_id` 持久化恢复在 worker 重启后仍可继续。
3. DLQ 与失败路径时序不回退。

回退：
1. 保留兼容路径开关，仅用于临时应急。
2. 回退时必须补一次回放验证。

## 7. N8 解析/检索/评分深度实现

目标：
1. 解析链路完全对齐 SSOT 结构字段。
2. 检索与评分策略可配置化且可验证。
3. 引用覆盖与置信度规则与 HITL 策略一致。

SSOT 对齐要点：
1. `content_list.json` 为定位真值，`full.md` 为结构真值。
2. bbox 归一化为 `[x0,y0,x1,y1]`，引用对象含 `page,bbox,heading_path,chunk_type`。
3. HITL 触发条件满足 `score_confidence/citation_coverage/score_deviation_pct` 规则。

输入：
1. `docs/design/2026-02-22-parser-and-retrieval-production-spec.md`。
2. `docs/design/2026-02-21-end-to-end-unified-design.md`。

产出：
1. 解析器与检索器统一接口及参数约束。
2. 评分规则与置信度计算模块。
3. 解析、检索、评分的集成测试与证据。

验收：
1. 每个评分项有可回跳引用并满足覆盖率阈值。
2. `score_confidence/citation_coverage` 与 HITL 触发一致。
3. 评估链路回放结果与黄金集对齐。

回退：
1. 允许降级为保守检索模式，但需记录原因。
2. 回退后需要更新证据并标注差异。

## 8. N9 前端 E2E 与引用真实化

目标：
1. 上传->评估->HITL->报告全流程 E2E 自动化。
2. citation 回跳与 bbox 高亮对接真实解析坐标。
3. 权限与双人复核交互一致化。

SSOT 对齐要点：
1. 主链路必须覆盖 `上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`。
2. 高风险动作双人复核前端必须可见且阻断执行。
3. 引用回跳必须基于解析定位字段（`page/bbox`），报告可追溯 `report_uri`。

输入：
1. `docs/design/2026-02-21-front-end-spec.md`。
2. 当前前端引用面板与权限实现。

产出：
1. 前端 E2E 测试脚本与证据。
2. 引用回跳与高亮的实测截图与日志。
3. 角色门控与审批交互证据。

验收：
1. E2E 覆盖关键路径并可重复执行。
2. 引用回跳定位准确，bbox 位置一致。
3. 高风险动作必须双 reviewer 才能完成。

回退：
1. 若高亮对齐失败，需回退为引用证据列表展示。
2. 回退必须标注原因与补偿方案。

## 9. N10 Gate D/E/F 真实验收与准入归档

目标：
1. Gate D 四门禁在真实环境复验。
2. Gate E 灰度与回滚演练证据齐全。
3. Gate F 运营优化有可量化改进指标。

SSOT 对齐要点：
1. 质量、性能、安全、成本四门禁同时达标才允许放量。
2. 回滚触发后 30 分钟内恢复服务并完成回放验证。
3. 高风险任务始终保留 HITL，放量审批与回放结果入审计链。

输入：
1. `docs/design/2026-02-22-gate-d-four-gates-checklist.md`。
2. `docs/design/2026-02-22-gate-e-rollout-and-rollback-checklist.md`。
3. `docs/design/2026-02-22-gate-f-operations-optimization-checklist.md`。

产出：
1. 四门禁复验报告与指标快照。
2. 灰度、回滚与回放证据包。
3. 运营优化前后对比数据。

验收：
1. 质量、性能、安全、成本门禁全部达标。
2. 30 分钟内完成回滚并通过回放验证。
3. 两轮运营优化指标连续改善。

回退：
1. 回滚到前一稳定版本并记录审计。
2. 必须阻止继续放量。

## 10. 证据与验收矩阵

每一阶段至少包含以下证据：
1. 文档变更记录。
2. 测试/回放/演练输出。
3. 运行日志与审计记录。
4. 结论与风险说明。

## 11. 风险与控制

风险：
1. 真实组件接入导致契约漂移。
2. 替换 runtime 引入状态机不一致。
3. 解析与检索的性能回退。

控制：
1. 所有变更先更新文档契约与证据模板。
2. 引入回放测试作为回归门禁。
3. 关键性能指标设定阈值并触发自动回滚。

## 12. 参考与关联文档

1. `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. `docs/design/2026-02-21-implementation-plan.md`
3. `docs/plans/2026-02-22-production-capability-plan.md`
4. `docs/ops/2026-02-23-end-to-end-implementation-status.md`
