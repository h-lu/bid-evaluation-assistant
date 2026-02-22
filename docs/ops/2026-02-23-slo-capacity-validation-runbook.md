# SLO 与容量验证 Runbook（P6+）

> 日期：2026-02-23  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 目标

1. 对关键查询接口执行延迟与错误率探针。
2. 输出可归档的门禁结果（`passed/failed`）。
3. 为 staging/prod 回放提供统一命令模板。

## 2. 执行前准备

1. 准备目标 URL（建议 staging）。
2. 准备租户请求头（如需鉴权可附带 Bearer token）。
3. 确认目标环境已经启用 `x-trace-id` 透传。

## 3. 探针命令

### 3.1 GET 探针（健康/查询类）

```bash
python3 scripts/run_slo_probe.py \
  --url http://localhost:8000/healthz \
  --requests 200 \
  --concurrency 20 \
  --p95-limit-ms 1500 \
  --error-rate-limit 0.01
```

### 3.2 POST 探针（检索类）

```bash
python3 scripts/run_slo_probe.py \
  --url http://localhost:8000/api/v1/retrieval/query \
  --method POST \
  --header "x-tenant-id:tenant_perf" \
  --header "x-trace-id:trace_perf_probe" \
  --json-body '{"project_id":"prj_perf","query_text":"price","mode_hint":"hybrid"}' \
  --requests 100 \
  --concurrency 10 \
  --p95-limit-ms 4000 \
  --error-rate-limit 0.01
```

输出为 JSON，包含：

1. `summary`：`count/error_rate/p50/p95/max/avg`。
2. `gate`：`passed` 与失败原因。

## 4. 故障注入与恢复计时

1. 在 staging 触发单点故障（如下线 1 个 worker）。
2. 立即执行 `run_slo_probe.py` 观测错误率与 P95。
3. 恢复服务后再次执行探针，确认门禁恢复。
4. 记录故障窗口起止时间，形成恢复时间证据。

## 5. 归档模板

1. 执行命令与参数。
2. 输出 JSON 原文。
3. 是否通过门禁。
4. 故障注入与恢复耗时。
