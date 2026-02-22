from __future__ import annotations

from typing import Any

REQUIRED_AUDIT_FIELDS = {"audit_id", "tenant_id", "action", "trace_id", "occurred_at"}
HIGH_RISK_ACTIONS = {"dlq_discard", "release_publish", "legal_hold_release"}


def evaluate_security_drill(*, audit_logs: list[dict[str, Any]]) -> dict[str, Any]:
    violations: list[str] = []
    high_risk_total = 0
    high_risk_dual_review = 0
    required_fields_missing = 0

    for row in audit_logs:
        missing = sorted(field for field in REQUIRED_AUDIT_FIELDS if not row.get(field))
        if missing:
            required_fields_missing += len(missing)
            violations.append(
                f"audit log {row.get('audit_id', '<unknown>')} missing required fields: {','.join(missing)}"
            )

        action = str(row.get("action", "")).strip()
        if action in HIGH_RISK_ACTIONS:
            high_risk_total += 1
            reviewers = row.get("approval_reviewers", [])
            if isinstance(reviewers, list) and len(reviewers) >= 2:
                high_risk_dual_review += 1
            else:
                violations.append(
                    f"high risk action {action} missing dual review (audit_id={row.get('audit_id', '<unknown>')})"
                )

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "audit_log_count": len(audit_logs),
        "required_fields_missing": required_fields_missing,
        "high_risk_actions_total": high_risk_total,
        "high_risk_actions_with_dual_review": high_risk_dual_review,
    }
