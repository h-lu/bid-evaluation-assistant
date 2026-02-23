# N6 真实 WORM API 接入证据

> 日期：2026-02-23  
> 分支：`codex/n6-n10-implementation`

## 1. 目标

1. 接入真实对象存储 WORM/Retention/Legal Hold API。
2. 保全状态查询与审计记录可追溯。
3. cleanup 删除行为被真实保全策略阻断。

## 1.1 SSOT 对齐要点

1. 合规约束：审计日志不可篡改，legal hold 对象不可被自动清理。
2. 高风险动作需双人复核（legal hold release）。

## 2. 变更点

1. 对象存储适配层增加 retention 与删除阻断。
2. legal hold 生命周期与保全状态联动。
3. 保全状态可由 `storage_uri/report_uri` 追溯。

## 3. 测试命令与结果（待执行）

```bash
pytest -q tests/test_object_storage_worm.py
```

结果：通过（local backend）

```bash
pytest -q tests/test_legal_hold_api.py
```

结果：通过

## 4. 结论

当前验证基于 local backend 与流程阻断语义，真实对象存储合规保全 API 接入仍需补齐。
