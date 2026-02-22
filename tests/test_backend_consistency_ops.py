from __future__ import annotations

from app.ops.backend_consistency import compare_store_payloads


def test_compare_store_payloads_reports_match():
    left = {"jobs": {"job_1": {"status": "queued"}}, "audit_logs": [{"a": 1}]}
    right = {"jobs": {"job_1": {"status": "queued"}}, "audit_logs": [{"a": 1}]}
    result = compare_store_payloads(left, right, sections=["jobs", "audit_logs"])
    assert result["all_matched"] is True
    assert result["mismatch_sections"] == []


def test_compare_store_payloads_reports_mismatch_sections():
    left = {"jobs": {"job_1": {"status": "queued"}}, "audit_logs": []}
    right = {"jobs": {"job_1": {"status": "failed"}}, "audit_logs": []}
    result = compare_store_payloads(left, right, sections=["jobs", "audit_logs"])
    assert result["all_matched"] is False
    assert result["mismatch_sections"] == ["jobs"]
    job_row = next(x for x in result["sections"] if x["section"] == "jobs")
    assert job_row["matched"] is False
    assert job_row["sqlite_count"] == 1
    assert job_row["postgres_count"] == 1
