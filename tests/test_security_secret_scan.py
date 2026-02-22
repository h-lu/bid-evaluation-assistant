from __future__ import annotations

from pathlib import Path

from app.security_scan import scan_paths


def test_secret_scan_reports_no_findings_for_clean_files(tmp_path: Path):
    clean = tmp_path / "clean.md"
    clean.write_text("this is safe text\nno credentials here\n", encoding="utf-8")
    findings = scan_paths([str(tmp_path)])
    assert findings == []


def test_secret_scan_detects_leaked_openai_like_key(tmp_path: Path):
    leaked = tmp_path / "leak.py"
    leaked.write_text('API_TOKEN = "sk-' + ("A" * 32) + '"\n', encoding="utf-8")
    findings = scan_paths([str(tmp_path)])
    assert findings
    assert any(item["pattern"] == "openai_key" for item in findings)
