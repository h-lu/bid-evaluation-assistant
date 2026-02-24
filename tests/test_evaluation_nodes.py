"""Tests for app.evaluation_nodes – real graph node functions (SSOT §2-§4)."""

from __future__ import annotations

import pytest

from app.evaluation_nodes import (
    EvaluationState,
    _compute_model_stability,
    node_evaluate_rules,
    node_finalize_report,
    node_load_context,
    node_persist_result,
    node_quality_gate,
    node_retrieve_evidence,
    node_score_with_llm,
    run_evaluation_nodes_sequentially,
)


@pytest.fixture()
def store():
    from app.store import InMemoryStore

    s = InMemoryStore()
    s.create_rule_pack(payload={
        "tenant_id": "t1",
        "rule_pack_version": "v1",
        "name": "test_pack",
        "rules": {
            "criteria": [
                {"criteria_id": "quality", "max_score": 30.0, "weight": 1.0,
                 "requirement_text": "quality assessment"},
                {"criteria_id": "price", "max_score": 20.0, "weight": 0.5,
                 "requirement_text": "price evaluation"},
            ],
        },
    })
    return s


def _initial_state(*, force_hitl: bool = False) -> EvaluationState:
    return {
        "tenant_id": "t1",
        "project_id": "prj_1",
        "evaluation_id": "ev_test001",
        "supplier_id": "sup_1",
        "trace_id": "tr_1",
        "thread_id": "th_1",
        "job_id": "job_1",
        "payload": {
            "project_id": "prj_1",
            "supplier_id": "sup_1",
            "rule_pack_version": "v1",
            "evaluation_scope": {
                "include_doc_types": ["bid"],
                "force_hitl": force_hitl,
            },
        },
        "rule_pack_version": "v1",
        "include_doc_types": ["bid"],
        "force_hitl": force_hitl,
        "status": "running",
        "errors": [],
        "retry_count": 0,
    }


# ---------------------------------------------------------------------------
# Individual node tests
# ---------------------------------------------------------------------------

class TestNodeLoadContext:
    def test_loads_rule_pack_and_criteria(self, store):
        state = _initial_state()
        updates = node_load_context(state, store=store)
        assert "rule_pack" in updates
        assert "criteria_defs" in updates
        assert len(updates["criteria_defs"]) == 2
        assert updates["hard_constraint_pass"] is True

    def test_default_criteria_when_no_rule_pack(self, store):
        state = _initial_state()
        state["rule_pack_version"] = "nonexistent"
        state["tenant_id"] = "unknown_tenant"
        updates = node_load_context(state, store=store)
        assert len(updates["criteria_defs"]) >= 1

    def test_criteria_weights_populated(self, store):
        state = _initial_state()
        updates = node_load_context(state, store=store)
        assert "quality" in updates["criteria_weights"]
        assert "price" in updates["criteria_weights"]


class TestNodeRetrieveEvidence:
    def test_retrieves_evidence_per_criteria(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        updates = node_retrieve_evidence(state, store=store)
        assert "criteria_evidence" in updates
        assert "citations_all_ids" in updates
        for cid in ["quality", "price"]:
            assert cid in updates["criteria_evidence"]
            assert len(updates["criteria_evidence"][cid]) >= 1


class TestNodeEvaluateRules:
    def test_no_redline_by_default(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        updates = node_evaluate_rules(state, store=store)
        assert updates["redline_conflict"] is False

    def test_detects_redline_conflict(self, store):
        state = _initial_state()
        state["rules"] = {"redlines": [{"violated": True}]}
        state["include_doc_types_normalized"] = {"bid"}
        updates = node_evaluate_rules(state, store=store)
        assert updates["redline_conflict"] is True


class TestNodeScoreWithLlm:
    def test_produces_criteria_results(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        updates = node_score_with_llm(state, store=store)
        assert "criteria_results" in updates
        assert len(updates["criteria_results"]) == 2
        for cr in updates["criteria_results"]:
            assert "score" in cr
            assert "max_score" in cr
            assert "reason" in cr
            assert "citations" in cr


class TestNodeQualityGate:
    def test_pass_without_hitl(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        updates = node_quality_gate(state, store=store)
        assert "total_score" in updates
        assert "confidence" in updates
        assert "needs_human_review" in updates
        assert isinstance(updates["hitl_reasons"], list)

    def test_force_hitl_triggers_review(self, store):
        state = _initial_state(force_hitl=True)
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        updates = node_quality_gate(state, store=store)
        assert updates["needs_human_review"] is True
        assert "force_hitl" in updates["hitl_reasons"]
        assert updates["interrupt_payload"] is not None
        assert updates["interrupt_payload"]["type"] == "human_review"


class TestNodeFinalizeReport:
    def test_assembles_report(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        state.update(node_quality_gate(state, store=store))
        updates = node_finalize_report(state, store=store)
        report = updates["report"]
        assert report["evaluation_id"] == "ev_test001"
        assert report["tenant_id"] == "t1"
        assert "criteria_results" in report
        assert "citations" in report
        assert "needs_human_review" in report


class TestNodePersistResult:
    def test_persists_report(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        state.update(node_quality_gate(state, store=store))
        state.update(node_finalize_report(state, store=store))
        updates = node_persist_result(state, store=store)
        assert updates["status"] == "persisted"
        report = store.evaluation_reports.get("ev_test001")
        assert report is not None


# ---------------------------------------------------------------------------
# Sequential pipeline
# ---------------------------------------------------------------------------

class TestRunSequentially:
    def test_full_pipeline_produces_report(self, store):
        state = _initial_state()
        final = run_evaluation_nodes_sequentially(state, store=store)
        assert final["status"] == "persisted"
        report = store.evaluation_reports.get("ev_test001")
        assert report is not None
        assert report["evaluation_id"] == "ev_test001"
        assert len(report["criteria_results"]) == 2

    def test_hitl_pipeline(self, store):
        state = _initial_state(force_hitl=True)
        final = run_evaluation_nodes_sequentially(state, store=store)
        report = store.evaluation_reports.get("ev_test001")
        assert report["needs_human_review"] is True
        assert report["interrupt"] is not None

    def test_state_type_keys_match_ssot(self, store):
        """EvaluationState TypedDict should have identity/trace/inputs/retrieval/scoring/review fields."""
        keys = set(EvaluationState.__annotations__.keys())
        assert "tenant_id" in keys
        assert "evaluation_id" in keys
        assert "thread_id" in keys
        assert "trace_id" in keys
        assert "criteria_defs" in keys
        assert "criteria_evidence" in keys
        assert "criteria_results" in keys
        assert "total_score" in keys
        assert "confidence" in keys
        assert "needs_human_review" in keys
        assert "hitl_reasons" in keys
        assert "errors" in keys
        assert "retry_count" in keys
        assert "resume_payload" in keys


# ---------------------------------------------------------------------------
# P1-8: Dynamic model_stability
# ---------------------------------------------------------------------------

class TestComputeModelStability:
    def test_uniform_scores_high_stability(self):
        results = [{"score": 10.0}, {"score": 10.0}, {"score": 10.0}]
        s = _compute_model_stability(results, hard_constraint_pass=True)
        assert s == 1.0

    def test_varied_scores_lower_stability(self):
        results = [{"score": 5.0}, {"score": 15.0}, {"score": 25.0}]
        s = _compute_model_stability(results, hard_constraint_pass=True)
        assert 0.5 <= s < 1.0

    def test_hard_constraint_fail_penalty(self):
        results = [{"score": 10.0}, {"score": 10.0}]
        s_pass = _compute_model_stability(results, hard_constraint_pass=True)
        s_fail = _compute_model_stability(results, hard_constraint_pass=False)
        assert s_fail <= s_pass - 0.14

    def test_single_score_default(self):
        results = [{"score": 10.0}]
        s = _compute_model_stability(results, hard_constraint_pass=True)
        assert s == 0.75

    def test_empty_scores_default(self):
        s = _compute_model_stability([], hard_constraint_pass=True)
        assert s == 0.75

    def test_floor_at_half(self):
        results = [{"score": 1.0}, {"score": 100.0}]
        s = _compute_model_stability(results, hard_constraint_pass=False)
        assert s >= 0.5

    def test_zero_scores(self):
        results = [{"score": 0.0}, {"score": 0.0}]
        s = _compute_model_stability(results, hard_constraint_pass=True)
        assert s == 1.0


# ---------------------------------------------------------------------------
# P1-9: Merge edited_scores from resume
# ---------------------------------------------------------------------------

class TestFinalizeReportEditedScores:
    def test_edited_scores_merged(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        state.update(node_quality_gate(state, store=store))

        state["resume_payload"] = {"edited_scores": {"quality": 99.0}}
        updates = node_finalize_report(state, store=store)
        report = updates["report"]

        quality_cr = next(
            cr for cr in report["criteria_results"] if cr["criteria_id"] == "quality"
        )
        assert quality_cr["score"] == 99.0
        assert quality_cr["human_edited"] is True

    def test_unedited_criteria_unchanged(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        state.update(node_quality_gate(state, store=store))

        original_price = next(
            cr["score"]
            for cr in state["criteria_results"]
            if cr["criteria_id"] == "price"
        )
        state["resume_payload"] = {"edited_scores": {"quality": 50.0}}
        updates = node_finalize_report(state, store=store)
        report = updates["report"]

        price_cr = next(
            cr for cr in report["criteria_results"] if cr["criteria_id"] == "price"
        )
        assert price_cr["score"] == original_price
        assert price_cr.get("human_edited") is not True

    def test_no_resume_payload_no_change(self, store):
        state = _initial_state()
        state.update(node_load_context(state, store=store))
        state.update(node_retrieve_evidence(state, store=store))
        state.update(node_evaluate_rules(state, store=store))
        state.update(node_score_with_llm(state, store=store))
        state.update(node_quality_gate(state, store=store))

        updates = node_finalize_report(state, store=store)
        report = updates["report"]
        for cr in report["criteria_results"]:
            assert cr.get("human_edited") is not True
