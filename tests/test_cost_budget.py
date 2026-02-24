"""Tests for per-task cost budget tracking (SSOT §7.4).

Validates CostBudgetTracker thresholds, degradation, and blocking behaviour.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from app.llm_provider import CostBudgetTracker, LLMUsage

# ---------------------------------------------------------------------------
# CostBudgetTracker unit tests
# ---------------------------------------------------------------------------


class TestCostBudgetTrackerRecording:
    def test_record_single_usage(self):
        tracker = CostBudgetTracker(task_id="t1", max_tokens_budget=10000)
        tracker.record_usage(LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        assert tracker.total_tokens == 150
        assert tracker._cumulative_prompt_tokens == 100
        assert tracker._cumulative_completion_tokens == 50

    def test_record_cumulative_usage(self):
        tracker = CostBudgetTracker(task_id="t2", max_tokens_budget=10000)
        tracker.record_usage(LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        tracker.record_usage(LLMUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280))
        assert tracker.total_tokens == 430
        assert tracker._cumulative_prompt_tokens == 300
        assert tracker._cumulative_completion_tokens == 130

    def test_record_zero_usage(self):
        tracker = CostBudgetTracker(task_id="t3", max_tokens_budget=10000)
        tracker.record_usage(LLMUsage())
        assert tracker.total_tokens == 0


class TestCheckBudgetStatuses:
    def test_ok_when_under_warn_threshold(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=5000))
        assert tracker.check_budget() == "ok"

    def test_degrade_at_warn_threshold(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=8000))
        assert tracker.check_budget() == "degrade"

    def test_degrade_persists_after_first_trigger(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=8000))
        assert tracker.check_budget() == "degrade"
        assert tracker.check_budget() == "degrade"

    def test_blocked_at_hard_threshold(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=12001))
        assert tracker.check_budget() == "blocked"

    def test_blocked_persists(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=15000))
        assert tracker.check_budget() == "blocked"
        assert tracker.check_budget() == "blocked"

    def test_exactly_at_warn_boundary(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=8000))
        assert tracker.check_budget() == "degrade"

    def test_exactly_at_hard_boundary(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=12000))
        status = tracker.check_budget()
        assert status in ("degrade", "blocked")

    def test_transition_from_ok_to_degrade_to_blocked(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=10000,
            warn_threshold_ratio=0.8, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=5000))
        assert tracker.check_budget() == "ok"

        tracker.record_usage(LLMUsage(total_tokens=4000))
        assert tracker.check_budget() == "degrade"

        tracker.record_usage(LLMUsage(total_tokens=4000))
        assert tracker.check_budget() == "blocked"


class TestUnlimitedBudget:
    def test_budget_zero_always_ok(self):
        tracker = CostBudgetTracker(task_id="t1", max_tokens_budget=0)
        tracker.record_usage(LLMUsage(total_tokens=999999))
        assert tracker.check_budget() == "ok"

    def test_is_over_budget_false_when_unlimited(self):
        tracker = CostBudgetTracker(task_id="t1", max_tokens_budget=0)
        tracker.record_usage(LLMUsage(total_tokens=999999))
        assert not tracker.is_over_budget

    def test_should_degrade_false_when_unlimited(self):
        tracker = CostBudgetTracker(task_id="t1", max_tokens_budget=0)
        tracker.record_usage(LLMUsage(total_tokens=999999))
        assert not tracker.should_degrade


class TestProperties:
    def test_is_over_budget(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=1000, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=1201))
        assert tracker.is_over_budget

    def test_not_over_budget(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=1000, hard_threshold_ratio=1.2,
        )
        tracker.record_usage(LLMUsage(total_tokens=1100))
        assert not tracker.is_over_budget

    def test_should_degrade_true(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=1000, warn_threshold_ratio=0.8,
        )
        tracker.record_usage(LLMUsage(total_tokens=800))
        assert tracker.should_degrade

    def test_should_degrade_false(self):
        tracker = CostBudgetTracker(
            task_id="t1", max_tokens_budget=1000, warn_threshold_ratio=0.8,
        )
        tracker.record_usage(LLMUsage(total_tokens=700))
        assert not tracker.should_degrade


class TestSSOTAlignment:
    """Verify default thresholds match SSOT §7.4 requirements."""

    def test_default_hard_ratio_is_1_2x(self):
        with mock.patch.dict(os.environ, {
            "TASK_TOKEN_BUDGET": "50000",
            "TASK_COST_WARN_RATIO": "0.8",
            "TASK_COST_HARD_RATIO": "1.2",
        }):
            tracker = CostBudgetTracker(task_id="ssot")
            assert tracker.hard_threshold_ratio == 1.2, (
                "SSOT §7.4: hard threshold must be 1.2x baseline"
            )

    def test_default_warn_ratio_is_0_8(self):
        with mock.patch.dict(os.environ, {
            "TASK_COST_WARN_RATIO": "0.8",
        }):
            tracker = CostBudgetTracker(task_id="ssot")
            assert tracker.warn_threshold_ratio == 0.8

    def test_default_budget_from_env(self):
        with mock.patch.dict(os.environ, {"TASK_TOKEN_BUDGET": "75000"}):
            from importlib import reload

            import app.llm_provider as mod
            reload(mod)
            tracker = mod.CostBudgetTracker(task_id="ssot")
            assert tracker.max_tokens_budget == 75000
            reload(mod)


class TestEnvConfiguration:
    def test_custom_env_budget(self):
        with mock.patch.dict(os.environ, {
            "TASK_TOKEN_BUDGET": "20000",
            "TASK_COST_WARN_RATIO": "0.7",
            "TASK_COST_HARD_RATIO": "1.5",
        }):
            from importlib import reload

            import app.llm_provider as mod
            reload(mod)
            tracker = mod.CostBudgetTracker(task_id="env_test")
            assert tracker.max_tokens_budget == 20000
            assert tracker.warn_threshold_ratio == 0.7
            assert tracker.hard_threshold_ratio == 1.5
            reload(mod)
