# 业务资源 API 证据（N3）

> 日期：2026-02-23  
> 分支：`main`

## 1. 目标

1. Projects/Suppliers/Rules 资源 CRUD 可用。
2. 租户隔离保持一致。
3. REST/OpenAPI 契约同步更新。

## 2. 变更点

1. 新增 Projects/Suppliers/Rules 接口与存储逻辑。
2. OpenAPI 与 REST 文档补齐资源契约。
3. 数据模型补齐 `rule_packs` 结构。

## 3. 测试命令与结果

```bash
pytest -q tests/test_projects_suppliers_rules_api.py
```

结果：通过

## 4. 结论

资源 CRUD 与租户隔离具备回归证据。
