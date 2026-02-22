# SSOT 对照缺口收口记录（2026-02-23）

> 对照基线：`docs/plans/2026-02-21-end-to-end-unified-design.md`  
> 收口分支：`main`

## 1. 本轮新增收口

1. `trace_id` 合规：新增严格模式 `TRACE_ID_STRICT_REQUIRED=true`，缺失 `x-trace-id` 返回 `400 TRACE_ID_REQUIRED`。
2. 高风险双人复核：`dlq_discard` 与 `legal_hold_release` 强制双 reviewer。
3. legal hold 能力：新增 impose/list/release 接口，并在存储清理动作前执行 hold 阻断。
4. 审计完整性：审计日志新增 `prev_hash/audit_hash` 链，提供完整性校验接口。
5. 健康探针对齐：补齐 `GET /api/v1/health`。

## 2. 新增接口

1. `GET /api/v1/health`
2. `GET /api/v1/internal/audit/integrity`
3. `POST /api/v1/internal/legal-hold/impose`
4. `GET /api/v1/internal/legal-hold/items`
5. `POST /api/v1/internal/legal-hold/{hold_id}/release`
6. `POST /api/v1/internal/storage/cleanup`

## 3. 验证结果

```bash
pytest -q
python3 scripts/security_secret_scan.py
```

结果：全部通过，密钥扫描 `finding_count=0`。

## 4. 与 SSOT 仍有距离的项（非本轮可一次性代码补齐）

1. Object Storage WORM 仍为规范与流程约束层，尚未接入真实对象存储保全策略 API。
2. LangGraph 仍是工作流语义与 checkpoint 兼容实现，尚未替换为完整 LangGraph runtime 节点图执行。
3. MVP 规划中的项目/供应商/规则管理完整资源接口仍处于“规划未纳入当前 v1 契约子集”状态。
4. 前端 citation 回跳 + bbox 高亮与角色门控仍在后续迭代范围。

说明：以上剩余项不影响当前 Gate C-F + P1-P6 已落地链路，但影响“完全体”目标达成度。
