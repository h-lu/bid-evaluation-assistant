# Observability & Deploy 生产化证据（P5）

> 日期：2026-02-23  
> 分支：`codex/p5-observability-deploy`

## 1. 覆盖范围

1. 发布流水线统一执行入口（pipeline execute）。
2. Readiness 强制与可配置绕过（用于演练场景）。
3. Canary/Rollback 关键配置收口与指标暴露。
4. 请求链路标识头（`x-trace-id` / `x-request-id`）。

## 2. 关键变更

1. `app/store.py`：
   - 新增 `execute_release_pipeline`。
   - 新增观测与发布配置字段（namespace/canary/rollback/readiness）。
   - `summarize_ops_metrics` 新增 `observability` 视图。
2. `app/main.py`：
   - 新增 `POST /api/v1/internal/release/pipeline/execute`。
   - 中间件统一写入响应头 `x-trace-id` 与 `x-request-id`。
3. `docs/design/2026-02-21-openapi-v1.yaml`：
   - 新增 pipeline path 与 schema。
   - 新增 observability summary schema。

## 3. 验证命令与结果

```bash
pytest -q tests/test_release_pipeline_api.py tests/test_response_envelope.py tests/test_release_readiness_api.py tests/test_observability_metrics_api.py
```

结果：`通过`

```bash
pytest -q
```

结果：`全量通过`

## 4. 结论

1. P5-S1/S2：观测口径与请求链路标识可统一追踪。
2. P5-S3/S4/S5：发布流水线具备自动阻断与可配置 canary/rollback 控制面。
3. P5-S6：Gate F 闭环能力保持可执行，且未回归。
