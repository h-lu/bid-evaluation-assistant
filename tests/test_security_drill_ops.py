from __future__ import annotations

from app.ops.security_drill import evaluate_security_drill


def test_security_drill_detects_missing_audit_fields_and_approval_gap():
    audit_logs = [
        {
            "audit_id": "audit_1",
            "tenant_id": "tenant_a",
            "action": "dlq_discard",
            "trace_id": "trace_1",
            "occurred_at": "2026-02-23T01:00:00+00:00",
            "approval_reviewers": ["r1"],
        },
        {
            "audit_id": "audit_2",
            "tenant_id": "tenant_a",
            "action": "release_publish",
            "trace_id": "trace_2",
            "occurred_at": "2026-02-23T01:05:00+00:00",
            "approval_reviewers": ["r1", "r2"],
        },
    ]

    result = evaluate_security_drill(audit_logs=audit_logs)
    assert result["passed"] is False
    assert result["high_risk_actions_total"] == 2
    assert result["high_risk_actions_with_dual_review"] == 1
    assert any("dual review" in item for item in result["violations"])


def test_security_drill_passes_when_required_fields_and_dual_review_present():
    audit_logs = [
        {
            "audit_id": "audit_10",
            "tenant_id": "tenant_a",
            "action": "dlq_discard",
            "trace_id": "trace_10",
            "occurred_at": "2026-02-23T02:00:00+00:00",
            "approval_reviewers": ["r1", "r2"],
        }
    ]
    result = evaluate_security_drill(audit_logs=audit_logs)
    assert result["passed"] is True
    assert result["violations"] == []
