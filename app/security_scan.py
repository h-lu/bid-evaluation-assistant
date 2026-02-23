from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("generic_api_key", re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ("generic_secret", re.compile(r"(?i)secret\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
)

TEXT_FILE_SUFFIXES = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".env",
    ".txt",
    ".sh",
}


def _is_text_candidate(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith(".") and path.suffix == "":
        return False
    if path.suffix.lower() in TEXT_FILE_SUFFIXES:
        return True
    if path.name in {"Dockerfile", "Makefile"}:
        return True
    return False


def _scan_file(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    findings: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    {
                        "file": str(path),
                        "line": idx,
                        "pattern": pattern_name,
                        "snippet": line[:200],
                    }
                )
    return findings


def scan_paths(paths: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for raw in paths:
        root = Path(raw).expanduser()
        if not root.exists():
            continue
        if root.is_file():
            if _is_text_candidate(root):
                findings.extend(_scan_file(root))
            continue
        for path in root.rglob("*"):
            if ".git" in path.parts or ".pytest_cache" in path.parts or "__pycache__" in path.parts:
                continue
            if _is_text_candidate(path):
                findings.extend(_scan_file(path))
    return findings
