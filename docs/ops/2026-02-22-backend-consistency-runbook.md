# 双写一致性比对 Runbook

> 版本：v2026.02.22-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-22-persistence-and-queue-production-spec.md`

## 1. 目的

1. 在双写观察窗口内，比较 `sqlite` 与 `postgres` 的关键状态一致性。
2. 形成可审计的比对结果。

## 2. 前置条件

1. sqlite 状态库路径可访问（`store_state` 表）。
2. postgres 可访问，且有状态表（默认 `bea_store_state`）。

## 3. 执行命令

```bash
python scripts/compare_store_backends.py \
  --sqlite-path .runtime/bea-store.sqlite3 \
  --postgres-dsn "$POSTGRES_DSN" \
  --postgres-table bea_store_state
```

可选仅比较部分分区：

```bash
python scripts/compare_store_backends.py \
  --sqlite-path .runtime/bea-store.sqlite3 \
  --postgres-dsn "$POSTGRES_DSN" \
  --sections jobs,documents,parse_manifests,evaluation_reports
```

## 4. 结果判读

1. `all_matched=true`：本次比对通过。
2. `all_matched=false`：查看 `mismatch_sections`，按分区排查。
3. 脚本返回码：
   - `0`：一致
   - `2`：不一致

## 5. 证据模板

1. 执行时间：`YYYY-MM-DDTHH:MM:SSZ`
2. 环境：`staging/prod-canary`
3. 脚本命令（原文）
4. 输出摘要：
   - `all_matched`
   - `mismatch_sections`
5. 后续动作：
   - 继续灰度 / 暂停写流量 / 触发回退
