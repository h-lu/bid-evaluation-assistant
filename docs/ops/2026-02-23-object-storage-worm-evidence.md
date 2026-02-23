# 对象存储 WORM 证据

> 日期：2026-02-23  
> 分支：`main`

## 1. 目标

1. 原始文档写入对象存储并可追溯。
2. 评估报告写入对象存储并可读取。
3. legal hold 阻断 cleanup 删除。

## 2. 变更点

1. 新增对象存储适配层（`local/s3`）。
2. 上传文档写入对象存储并记录 `storage_uri`。
3. 评估报告归档写入对象存储并记录 `report_uri`。
4. legal hold 与 storage cleanup 联动对象存储。

## 3. 测试命令与结果

```bash
pytest -q tests/test_object_storage_worm.py
```

结果：通过

```bash
pytest -q tests/test_legal_hold_api.py
```

结果：通过

## 4. 结论

对象存储 WORM、legal hold 与 cleanup 联动具备可回归测试证据。
