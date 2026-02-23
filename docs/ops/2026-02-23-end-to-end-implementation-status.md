# 端到端统一方案实现状态（详细）

> 日期：2026-02-23  
> 基于分支：`codex/n1-n5-closeout`  
> 基于提交：`76ab79f`

## 1. 目的与范围

本文档用于对照 SSOT（`docs/plans/2026-02-21-end-to-end-unified-design.md`）给出当前端到端能力的详细实现状态、证据位置与仍需补齐的事项。内容覆盖 N1-N5 的实装结果与剩余差距。

## 2. 总体结论

结论：已完成 N1-N5 的落地与证据归档，但与 SSOT 完全体仍有差距，主要集中在“真实 WORM 保全 API 接入”和“LangGraph 真实 runtime 图执行”以及“深度解析/检索/评分体系的完整实现”。

注意：本文档不新增行为承诺，不替代 SSOT 或专项设计，仅做现状记录与差距说明。

## 3. N1-N5 实施状态总览

状态标记：
- [x] 已完成并有证据
- [~] 部分完成（具备可运行替代路径）
- [ ] 未完成

### 3.1 N1 真实 WORM 保全接入（后端）

- [~] 对象存储适配层已落地（本地/S3 兼容），WORM 为流程约束实现。
- [x] 报告与原始证据写入对象存储，并可标记 legal hold。
- [x] cleanup 流程对 legal hold 对象阻断删除。

证据与实现：
- 实现：`app/object_storage.py`、`app/services/storage.py`、`app/services/legal_hold.py`。
- 测试：`tests/test_object_storage_worm.py`。
- 文档：`docs/design/2026-02-23-object-storage-worm-spec.md`、`docs/ops/2026-02-23-object-storage-worm-evidence.md`。

差距：
- 仍未接入真实对象存储“合规保全/WORM 策略 API”。当前为语义约束与流程阻断层。

### 3.2 N2 LangGraph runtime 真替换（工作流）

- [~] 运行时路径已支持 LangGraph，默认兼容模式回落。
- [~] checkpoint/interrupt/resume 已按语义适配，但仍非完整 runtime 图执行。

证据与实现：
- 实现：`app/workflow/runtime.py`、`app/stores.py`。
- 文档：`docs/design/2026-02-22-workflow-and-worker-production-spec.md`、`docs/ops/2026-02-23-workflow-worker-evidence.md`。

差距：
- 真实 LangGraph 图执行、typed edges 与完整节点编排仍未替换完成。

### 3.3 N3 业务资源 API（projects/suppliers/rules）

- [x] 资源 CRUD 已落地（list/create/get/update）。
- [x] 租户隔离 + 审计 + 幂等一致性对齐。

证据与实现：
- 实现：`app/main.py`、`app/repositories/projects.py`、`app/repositories/suppliers.py`、`app/repositories/rule_packs.py`。
- 测试：`tests/test_projects_suppliers_rules_api.py`。
- 文档：`docs/design/2026-02-21-openapi-v1.yaml`、`docs/design/2026-02-21-rest-api-specification.md`、`docs/ops/2026-02-23-resource-api-evidence.md`。

差距：
- 规则包与评估链路深度联动（自动应用、版本演进、冲突检测）仍为后续演进事项。

### 3.4 N4 前端能力收口（引用回跳与权限）

- [x] 评估报告页新增证据面板、citation 回跳。
- [~] bbox 高亮为模拟展示（需要与解析坐标体系进一步对齐）。
- [x] 角色门控与高风险操作双人复核提示已落地。

证据与实现：
- 实现：`frontend/src/views/EvaluationReportView.vue`、`frontend/src/stores/session.js`。
- 文档：`docs/ops/2026-02-23-frontend-citation-evidence.md`。

差距：
- 真实坐标高亮、页面级 E2E 流程测试尚未补齐。

### 3.5 N5 生产演练证据归档

- [x] 生产演练证据已整理归档。
- [x] 安全合规演练脚本已执行并记录。

证据与实现：
- 证据：`docs/ops/2026-02-23-production-drill-evidence.md`。
- 产物：`artifacts/audit_logs_release_window.json`（已忽略提交）。

差距：
- 若进入正式准入流程，需要 staging 真实环境的演练证据补充。

## 4. 与 SSOT 仍存在的核心差距

1. 真实 WORM 保全 API：当前为流程约束与存储标记，缺少与存储服务合规保全 API 的实接。
2. LangGraph 真 runtime：仍是兼容执行路径，需替换为完整节点图执行与 typed edges。
3. 深度解析/检索/评分：目前以稳定主链路为主，尚未达到 SSOT 中高阶能力的完整实现。
4. 前端 E2E：关键流程尚未形成端到端自动化覆盖证据。

## 5. 证据索引（便于复核）

- N1：`docs/ops/2026-02-23-object-storage-worm-evidence.md`
- N2：`docs/ops/2026-02-23-workflow-worker-evidence.md`
- N3：`docs/ops/2026-02-23-resource-api-evidence.md`
- N4：`docs/ops/2026-02-23-frontend-citation-evidence.md`
- N5：`docs/ops/2026-02-23-production-drill-evidence.md`

## 6. 本次会话验证说明

本会话未重新执行测试或演练命令，以上结论基于已有证据文档与提交记录。

## 7. 后续建议（按优先级）

1. N2：完成 LangGraph 真 runtime 图执行替换，并补齐集成测试。
2. N1：对接对象存储 WORM 合规保全 API（如 S3 Object Lock/Retention）。
3. N4：补齐前端 E2E（上传->评估->HITL->报告、DLQ 操作）。
4. N3：规则包与主链路联动的规则版本与冲突处理。
