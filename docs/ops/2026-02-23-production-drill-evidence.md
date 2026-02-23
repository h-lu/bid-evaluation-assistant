# N5 生产演练证据归档

> 日期：2026-02-23  
> 环境：local（无 staging，可复现实验）  
> 分支：`main`

## 1. SLO 探针与故障注入

### 1.1 健康检查（正常）

命令：

```bash
python3 scripts/run_slo_probe.py \
  --url http://127.0.0.1:8000/healthz \
  --requests 30 \
  --concurrency 5 \
  --p95-limit-ms 1500 \
  --error-rate-limit 0.01
```

输出：

```json
{"url": "http://127.0.0.1:8000/healthz", "requests": 30, "concurrency": 5, "summary": {"count": 30, "error_count": 0, "error_rate": 0.0, "p50_ms": 8.948374015744776, "p95_ms": 20.339809008874, "max_ms": 21.455109992530197, "avg_ms": 10.445754098085066}, "gate": {"passed": true, "failed_reasons": [], "p95_limit_ms": 1500.0, "error_rate_limit": 0.01}}
```

### 1.2 故障注入（服务停止）

命令：

```bash
python3 scripts/run_slo_probe.py \
  --url http://127.0.0.1:8000/healthz \
  --requests 10 \
  --concurrency 2 \
  --p95-limit-ms 1500 \
  --error-rate-limit 0.01
```

输出：

```json
{"url": "http://127.0.0.1:8000/healthz", "requests": 10, "concurrency": 2, "summary": {"count": 10, "error_count": 10, "error_rate": 1.0, "p50_ms": 0.26218098355457187, "p95_ms": 4.248148994520307, "max_ms": 4.248148994520307, "avg_ms": 1.1052769899833947}, "gate": {"passed": false, "failed_reasons": ["error_rate exceeded: 1.0000 > 0.0100"], "p95_limit_ms": 1500.0, "error_rate_limit": 0.01}}
```

### 1.3 恢复后健康检查

命令同 1.1。输出：

```json
{"url": "http://127.0.0.1:8000/healthz", "requests": 30, "concurrency": 5, "summary": {"count": 30, "error_count": 0, "error_rate": 0.0, "p50_ms": 8.954090997576714, "p95_ms": 18.80105899181217, "max_ms": 31.616293010301888, "avg_ms": 10.327784528878206}, "gate": {"passed": true, "failed_reasons": [], "p95_limit_ms": 1500.0, "error_rate_limit": 0.01}}
```

### 1.4 故障窗口

1. 开始：`2026-02-23T01:30:05Z`
2. 结束：`2026-02-23T01:30:10Z`

## 2. SLO 探针（检索类）

命令：

```bash
python3 scripts/run_slo_probe.py \
  --url http://127.0.0.1:8000/api/v1/retrieval/query \
  --method POST \
  --header "x-tenant-id:tenant_perf" \
  --header "x-trace-id:trace_perf_probe" \
  --json-body '{"project_id":"prj_perf","supplier_id":"sup_perf","query":"price","query_type":"fact","top_k":10,"enable_rerank":false}' \
  --requests 30 \
  --concurrency 5 \
  --p95-limit-ms 4000 \
  --error-rate-limit 0.01
```

输出：

```json
{"url": "http://127.0.0.1:8000/api/v1/retrieval/query", "requests": 30, "concurrency": 5, "summary": {"count": 30, "error_count": 0, "error_rate": 0.0, "p50_ms": 11.322945007123053, "p95_ms": 26.568902016151696, "max_ms": 26.83567302301526, "avg_ms": 13.067966361995786}, "gate": {"passed": true, "failed_reasons": [], "p95_limit_ms": 4000.0, "error_rate_limit": 0.01}}
```

## 3. 安全合规演练

输入审计日志快照：

1. `artifacts/audit_logs_release_window.json`

执行命令：

```bash
python3 scripts/security_compliance_drill.py \
  --audit-json artifacts/audit_logs_release_window.json
```

输出：

```json
{"passed": true, "violations": [], "audit_log_count": 3, "required_fields_missing": 0, "high_risk_actions_total": 2, "high_risk_actions_with_dual_review": 2}
```

## 4. 结论

1. SLO 探针与故障恢复演练在本地环境通过。
2. 安全合规演练通过，双人复核覆盖率满足要求。
