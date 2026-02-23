# N6 真实 WORM API 接入证据

> 日期：2026-02-23  
> 分支：`codex/n1-n5-closeout`

## 1. 目标

1. 接入真实对象存储 WORM/Retention/Legal Hold API。
2. 保全状态查询与审计记录可追溯。
3. cleanup 删除行为被真实保全策略阻断。

## 1.1 SSOT 对齐要点

1. 合规约束：审计日志不可篡改，legal hold 对象不可被自动清理。
2. 高风险动作需双人复核（legal hold release）。

## 2. 变更点（待补齐）

1. 对象存储适配层新增 WORM/Retention/Legal Hold API 调用。
2. legal hold 生命周期与合规保全状态统一。
3. 审计事件增加保全策略字段。
4. 保全状态查询对齐 `storage_uri` 与 `report_uri` 的一致性追溯。

## 3. 测试命令与结果（待执行）

```bash
pytest -q tests/test_object_storage_worm.py
```

结果：待执行

```bash
pytest -q tests/test_legal_hold_api.py
```

结果：待执行

## 4. 结论

尚未验证。完成真实 WORM API 对接后需补齐命令输出与结论。
