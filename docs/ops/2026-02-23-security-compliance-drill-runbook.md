# 安全合规演练 Runbook（P6+）

> 日期：2026-02-23  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 校验审计日志关键字段完整性。
2. 校验高风险动作双人复核覆盖率。
3. 生成可归档演练结果。

## 2. 输入准备

1. 导出审计日志为 JSON 数组（建议最近一次发布窗口）。
2. 每条记录至少包含：`audit_id/tenant_id/action/trace_id/occurred_at`。
3. 高风险动作记录附带 `approval_reviewers`（数组）。

## 3. 执行命令

```bash
python3 scripts/security_compliance_drill.py \
  --audit-json ./artifacts/audit_logs_release_window.json
```

返回 JSON 字段：

1. `passed`：是否通过。
2. `violations`：违规明细。
3. `required_fields_missing`：缺失字段计数。
4. `high_risk_actions_total` 与 `high_risk_actions_with_dual_review`。

## 4. 判定规则

1. 任一关键字段缺失：失败。
2. 高风险动作未满足双人复核：失败。
3. 无违规项：通过。

## 5. 归档模板

1. 演练时间窗口。
2. 输入审计日志快照路径。
3. 命令与输出 JSON。
4. 失败项整改责任人与完成时间。
