def _performance_payload(
    *,
    api_p95_s: float = 1.2,
    retrieval_p95_s: float = 3.5,
    parse_50p_p95_s: float = 170.0,
    evaluation_p95_s: float = 100.0,
    queue_dlq_rate: float = 0.006,
    cache_hit_rate: float = 0.75,
) -> dict:
    return {
        "dataset_id": "ds_perf_smoke",
        "metrics": {
            "api_p95_s": api_p95_s,
            "retrieval_p95_s": retrieval_p95_s,
            "parse_50p_p95_s": parse_50p_p95_s,
            "evaluation_p95_s": evaluation_p95_s,
            "queue_dlq_rate": queue_dlq_rate,
            "cache_hit_rate": cache_hit_rate,
        },
    }


def _security_payload(
    *,
    tenant_scope_violations: int = 0,
    auth_bypass_findings: int = 0,
    high_risk_approval_coverage: float = 1.0,
    log_redaction_failures: int = 0,
    secret_scan_findings: int = 0,
) -> dict:
    return {
        "dataset_id": "ds_security_smoke",
        "metrics": {
            "tenant_scope_violations": tenant_scope_violations,
            "auth_bypass_findings": auth_bypass_findings,
            "high_risk_approval_coverage": high_risk_approval_coverage,
            "log_redaction_failures": log_redaction_failures,
            "secret_scan_findings": secret_scan_findings,
        },
    }


def _cost_payload(
    *,
    task_cost_p95: float = 1.08,
    baseline_task_cost_p95: float = 1.0,
    routing_degrade_passed: bool = True,
    degrade_availability: float = 0.997,
    budget_alert_coverage: float = 1.0,
) -> dict:
    return {
        "dataset_id": "ds_cost_smoke",
        "metrics": {
            "task_cost_p95": task_cost_p95,
            "baseline_task_cost_p95": baseline_task_cost_p95,
            "routing_degrade_passed": routing_degrade_passed,
            "degrade_availability": degrade_availability,
            "budget_alert_coverage": budget_alert_coverage,
        },
    }


def test_performance_gate_pass(client):
    resp = client.post(
        "/api/v1/internal/performance-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_performance_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gate"] == "performance"
    assert data["passed"] is True
    assert data["failed_checks"] == []


def test_performance_gate_block(client):
    resp = client.post(
        "/api/v1/internal/performance-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_performance_payload(api_p95_s=1.8, queue_dlq_rate=0.02, cache_hit_rate=0.6),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["passed"] is False
    assert "API_P95_EXCEEDED" in data["failed_checks"]
    assert "QUEUE_DLQ_RATE_HIGH" in data["failed_checks"]
    assert "CACHE_HIT_RATE_LOW" in data["failed_checks"]


def test_performance_gate_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/performance-gates/evaluate",
        json=_performance_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_security_gate_pass(client):
    resp = client.post(
        "/api/v1/internal/security-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_security_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gate"] == "security"
    assert data["passed"] is True
    assert data["failed_checks"] == []


def test_security_gate_block(client):
    resp = client.post(
        "/api/v1/internal/security-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_security_payload(
            tenant_scope_violations=1,
            auth_bypass_findings=2,
            high_risk_approval_coverage=0.9,
            log_redaction_failures=1,
            secret_scan_findings=1,
        ),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["passed"] is False
    assert "TENANT_SCOPE_VIOLATION_FOUND" in data["failed_checks"]
    assert "AUTH_BYPASS_FOUND" in data["failed_checks"]
    assert "HIGH_RISK_APPROVAL_COVERAGE_LOW" in data["failed_checks"]
    assert "LOG_REDACTION_FAILURE_FOUND" in data["failed_checks"]
    assert "SECRET_SCAN_FINDING_FOUND" in data["failed_checks"]


def test_security_gate_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/security-gates/evaluate",
        json=_security_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_cost_gate_pass(client):
    resp = client.post(
        "/api/v1/internal/cost-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_cost_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gate"] == "cost"
    assert data["passed"] is True
    assert data["failed_checks"] == []


def test_cost_gate_block(client):
    resp = client.post(
        "/api/v1/internal/cost-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_cost_payload(
            task_cost_p95=1.25,
            baseline_task_cost_p95=1.0,
            routing_degrade_passed=False,
            degrade_availability=0.98,
            budget_alert_coverage=0.9,
        ),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["passed"] is False
    assert "TASK_COST_P95_RATIO_HIGH" in data["failed_checks"]
    assert "ROUTING_DEGRADE_FAILED" in data["failed_checks"]
    assert "DEGRADE_AVAILABILITY_LOW" in data["failed_checks"]
    assert "BUDGET_ALERT_COVERAGE_LOW" in data["failed_checks"]


def test_cost_gate_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/cost-gates/evaluate",
        json=_cost_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_cost_gate_rejects_non_positive_baseline(client):
    resp = client.post(
        "/api/v1/internal/cost-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_cost_payload(baseline_task_cost_p95=0),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "REQ_VALIDATION_FAILED"
