from __future__ import annotations

from typing import Any

SECURITY_THRESHOLDS: dict[str, float] = {
    "tenant_scope_violations_max": 0,
    "auth_bypass_findings_max": 0,
    "high_risk_approval_coverage_min": 1.0,
    "log_redaction_failures_max": 0,
    "secret_scan_findings_max": 0,
}


def evaluate_security_gate(*, dataset_id: str, metrics: dict[str, float | int]) -> dict[str, Any]:
    tenant_scope_violations = int(metrics["tenant_scope_violations"])
    auth_bypass_findings = int(metrics["auth_bypass_findings"])
    high_risk_approval_coverage = float(metrics["high_risk_approval_coverage"])
    log_redaction_failures = int(metrics["log_redaction_failures"])
    secret_scan_findings = int(metrics["secret_scan_findings"])

    failed_checks: list[str] = []
    if tenant_scope_violations > SECURITY_THRESHOLDS["tenant_scope_violations_max"]:
        failed_checks.append("TENANT_SCOPE_VIOLATION_FOUND")
    if auth_bypass_findings > SECURITY_THRESHOLDS["auth_bypass_findings_max"]:
        failed_checks.append("AUTH_BYPASS_FOUND")
    if high_risk_approval_coverage < SECURITY_THRESHOLDS["high_risk_approval_coverage_min"]:
        failed_checks.append("HIGH_RISK_APPROVAL_COVERAGE_LOW")
    if log_redaction_failures > SECURITY_THRESHOLDS["log_redaction_failures_max"]:
        failed_checks.append("LOG_REDACTION_FAILURE_FOUND")
    if secret_scan_findings > SECURITY_THRESHOLDS["secret_scan_findings_max"]:
        failed_checks.append("SECRET_SCAN_FINDING_FOUND")

    return {
        "gate": "security",
        "dataset_id": dataset_id,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "thresholds": dict(SECURITY_THRESHOLDS),
        "values": {
            "tenant_scope_violations": tenant_scope_violations,
            "auth_bypass_findings": auth_bypass_findings,
            "high_risk_approval_coverage": high_risk_approval_coverage,
            "log_redaction_failures": log_redaction_failures,
            "secret_scan_findings": secret_scan_findings,
        },
    }
