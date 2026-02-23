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

## 3.1 真实对象存储验证（MinIO Object Lock）

```bash
docker run -d --name bea-minio -p 9000:9000 -p 9001:9001 \\
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \\
  minio/minio server /data --console-address \":9001\"

/tmp/mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
/tmp/mc mb --with-lock local/bea
```

验证脚本（S3 backend + retention + legal hold）：

```bash
python3 - <<'PY'
import os
from app.object_storage import create_object_storage_from_env

os.environ.update({
    "BEA_OBJECT_STORAGE_BACKEND": "s3",
    "OBJECT_STORAGE_BUCKET": "bea",
    "OBJECT_STORAGE_ENDPOINT": "http://127.0.0.1:9000",
    "OBJECT_STORAGE_ACCESS_KEY": "minioadmin",
    "OBJECT_STORAGE_SECRET_KEY": "minioadmin",
    "OBJECT_STORAGE_FORCE_PATH_STYLE": "true",
    "OBJECT_STORAGE_RETENTION_DAYS": "1",
    "OBJECT_STORAGE_RETENTION_MODE": "GOVERNANCE",
})

store = create_object_storage_from_env(os.environ)
uri = store.put_object(
    tenant_id="tenant_demo",
    object_type="document",
    object_id="doc_demo",
    filename="demo.txt",
    content_bytes=b"demo",
    content_type="text/plain",
)
print("uri", uri)
print("retention", store.get_retention(storage_uri=uri))
print("retention_active", store.is_retention_active(storage_uri=uri))
print("apply_hold", store.apply_legal_hold(storage_uri=uri))
print("hold_active", store.is_legal_hold_active(storage_uri=uri))
try:
    store.delete_object(storage_uri=uri)
    print("delete_ok")
except Exception as exc:
    print("delete_error", type(exc).__name__, getattr(exc, "code", None))
print("release_hold", store.release_legal_hold(storage_uri=uri))
try:
    store.delete_object(storage_uri=uri)
    print("delete_ok")
except Exception as exc:
    print("delete_error", type(exc).__name__, getattr(exc, "code", None))
PY
```

结果摘要：

1. retention 查询返回 `GOVERNANCE` + `retain_until`。
2. legal hold 生效后删除返回 `LEGAL_HOLD_ACTIVE`。
3. release 后仍被 retention 阻断，返回 `RETENTION_ACTIVE`。

## 4. 结论

已验证 MinIO Object Lock 下 legal hold/retention 阻断行为。删除需等待 retention 过期或具备治理旁路权限。
