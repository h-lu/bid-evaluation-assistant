"""Tests for app.constraint_extractor – entity / numeric / time extraction."""

from __future__ import annotations

import pytest

from app.constraint_extractor import extract_constraints


# ---------------------------------------------------------------------------
# Entity constraints
# ---------------------------------------------------------------------------

class TestEntityExtraction:
    def test_company_name(self):
        r = extract_constraints("中国建设工程公司是否具有一级资质")
        companies = [e for e in r["entity_constraints"] if e["type"] == "company"]
        assert len(companies) >= 1
        assert "建设工程公司" in companies[0]["value"]

    def test_qualification_level(self):
        r = extract_constraints("投标人应具有一级资质")
        quals = [e for e in r["entity_constraints"] if e["type"] == "qualification"]
        assert any("一级" in q["value"] for q in quals)

    def test_certification(self):
        r = extract_constraints("供应商应提供ISO9001:2015认证")
        certs = [e for e in r["entity_constraints"] if e["type"] == "certification"]
        assert any("ISO9001" in c["value"] for c in certs)

    def test_no_false_positives_on_plain_text(self):
        r = extract_constraints("请提供产品说明书")
        assert r["entity_constraints"] == []


# ---------------------------------------------------------------------------
# Numeric constraints
# ---------------------------------------------------------------------------

class TestNumericExtraction:
    def test_amount_wan_yuan(self):
        r = extract_constraints("注册资本不少于500万元")
        amounts = [n for n in r["numeric_constraints"] if n["type"] == "amount"]
        assert any(n["value"] == 5_000_000 for n in amounts)

    def test_amount_yuan(self):
        r = extract_constraints("报价不超过100元")
        amounts = [n for n in r["numeric_constraints"] if n["type"] == "amount"]
        assert any(n["value"] == 100 for n in amounts)

    def test_percentage(self):
        r = extract_constraints("质量评分占比30%")
        pcts = [n for n in r["numeric_constraints"] if n["type"] == "percentage"]
        assert any(n["value"] == 30.0 for n in pcts)

    def test_range(self):
        r = extract_constraints("交付期限为30到60天")
        ranges = [n for n in r["numeric_constraints"] if n["type"] == "range"]
        assert any(n["min"] == 30 and n["max"] == 60 for n in ranges)

    def test_min_bound(self):
        r = extract_constraints("项目经验不少于5个")
        bounds = [n for n in r["numeric_constraints"] if n["type"] == "min_bound"]
        assert any(n["value"] == 5 for n in bounds)

    def test_max_bound(self):
        r = extract_constraints("工期不超过120天")
        bounds = [n for n in r["numeric_constraints"] if n["type"] == "max_bound"]
        assert any(n["value"] == 120 for n in bounds)

    def test_no_false_positives(self):
        r = extract_constraints("请提供投标文件")
        assert r["numeric_constraints"] == []


# ---------------------------------------------------------------------------
# Time constraints
# ---------------------------------------------------------------------------

class TestTimeExtraction:
    def test_iso_date(self):
        r = extract_constraints("截止日期为2026-03-15")
        dates = [t for t in r["time_constraints"] if t["type"] == "date"]
        assert any(d["value"] == "2026-03-15" for d in dates)

    def test_chinese_date(self):
        r = extract_constraints("开标时间为2026年3月15日")
        dates = [t for t in r["time_constraints"] if t["type"] == "date"]
        assert any(d["value"] == "2026-03-15" for d in dates)

    def test_chinese_date_without_day(self):
        r = extract_constraints("计划2026年6月完成")
        dates = [t for t in r["time_constraints"] if t["type"] == "date"]
        assert any(d["value"] == "2026-06-01" for d in dates)

    def test_duration(self):
        r = extract_constraints("工期为12个月")
        durations = [t for t in r["time_constraints"] if t["type"] == "duration"]
        assert any(d["value"] == 12 and d["unit"] == "月" for d in durations)

    def test_deadline(self):
        r = extract_constraints("须在30天以内完成")
        deadlines = [t for t in r["time_constraints"] if t["type"] == "deadline"]
        assert any(d["value"] == 30 for d in deadlines)

    def test_no_false_positives(self):
        r = extract_constraints("请提供完整技术方案")
        assert r["time_constraints"] == []


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestExtractConstraintsIntegration:
    def test_returns_all_three_keys(self):
        r = extract_constraints("简单查询")
        assert "entity_constraints" in r
        assert "numeric_constraints" in r
        assert "time_constraints" in r

    def test_complex_query(self):
        q = "中国建设工程公司注册资本不少于500万元，一级资质，工期不超过180天，截止2026-06-30"
        r = extract_constraints(q)
        assert len(r["entity_constraints"]) >= 2
        assert len(r["numeric_constraints"]) >= 2
        assert len(r["time_constraints"]) >= 1

    def test_empty_query(self):
        r = extract_constraints("")
        assert r == {
            "entity_constraints": [],
            "numeric_constraints": [],
            "time_constraints": [],
        }
