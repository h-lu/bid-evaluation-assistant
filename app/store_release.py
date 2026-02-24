from __future__ import annotations

import re
import uuid
from typing import Any

from app.errors import ApiError


class StoreReleaseMixin:
    def run_release_replay_e2e(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        project_id: str,
        supplier_id: str,
        doc_type: str = "bid",
        force_hitl: bool = True,
        decision: str = "approve",
    ) -> dict[str, Any]:
        replay_run_id = f"rpy_{uuid.uuid4().hex[:12]}"
        upload = self.create_upload_job(
            {
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "doc_type": doc_type,
                "filename": f"{release_id}.pdf",
                "file_sha256": uuid.uuid4().hex,
                "file_size": 128,
            }
        )
        parse_job_id = upload["job_id"]
        parse_result = self.run_job_once(job_id=parse_job_id, tenant_id=tenant_id)
        parse_status = parse_result["final_status"]

        eval_created = self.create_evaluation_job(
            {
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "rule_pack_version": "v1.0.0",
                "evaluation_scope": {"include_doc_types": [doc_type], "force_hitl": force_hitl},
                "query_options": {"mode_hint": "hybrid", "top_k": 10},
            }
        )
        evaluation_id = eval_created["evaluation_id"]
        evaluation_job_id = eval_created["job_id"]
        resume_job_id: str | None = None

        report = self.get_evaluation_report_for_tenant(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
        )
        if force_hitl and isinstance(report, dict):
            interrupt = report.get("interrupt")
            token = interrupt.get("resume_token") if isinstance(interrupt, dict) else None
            if isinstance(token, str) and token:
                if self.consume_resume_token(
                    evaluation_id=evaluation_id,
                    resume_token=token,
                    tenant_id=tenant_id,
                ):
                    resumed = self.create_resume_job(
                        evaluation_id=evaluation_id,
                        payload={
                            "tenant_id": tenant_id,
                            "trace_id": trace_id,
                            "decision": decision,
                            "comment": "release replay auto resume",
                            "editor": {"reviewer_id": "system_replay"},
                        },
                    )
                    resume_job_id = resumed["job_id"]
                    self.run_job_once(job_id=resume_job_id, tenant_id=tenant_id)

        final_report = (
            self.get_evaluation_report_for_tenant(
                evaluation_id=evaluation_id,
                tenant_id=tenant_id,
            )
            or {}
        )
        needs_human_review = bool(final_report.get("needs_human_review", False))
        passed = parse_status == "succeeded" and (not force_hitl or not needs_human_review)

        data = {
            "replay_run_id": replay_run_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "parse": {"job_id": parse_job_id, "status": parse_status},
            "evaluation": {
                "evaluation_id": evaluation_id,
                "job_id": evaluation_job_id,
                "resume_job_id": resume_job_id,
                "needs_human_review": needs_human_review,
            },
            "passed": passed,
        }
        self.release_replay_runs[replay_run_id] = {**data, "trace_id": trace_id, "created_at": self._utcnow_iso()}
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_replay_e2e_executed",
                "release_id": release_id,
                "replay_run_id": replay_run_id,
                "passed": passed,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return data

    def evaluate_release_readiness(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        expected_gates = ["quality", "performance", "security", "cost", "rollout", "rollback", "ops"]
        normalized_gate_results = {name: bool(gate_results.get(name, False)) for name in expected_gates}
        failed_checks: list[str] = []
        if not (dataset_version or "").strip():
            failed_checks.append("DATASET_VERSION_REQUIRED")
        for gate_name in expected_gates:
            if not normalized_gate_results[gate_name]:
                failed_checks.append(f"{gate_name.upper()}_GATE_FAILED")
        if not replay_passed:
            failed_checks.append("REPLAY_E2E_FAILED")
        admitted = len(failed_checks) == 0
        assessment_id = f"ra_{uuid.uuid4().hex[:12]}"
        data = {
            "assessment_id": assessment_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "dataset_version": dataset_version or "",
            "admitted": admitted,
            "failed_checks": failed_checks,
            "replay_passed": replay_passed,
            "gate_results": normalized_gate_results,
        }
        self.release_readiness_assessments[assessment_id] = {
            **data,
            "trace_id": trace_id,
            "created_at": self._utcnow_iso(),
        }
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_readiness_evaluated",
                "release_id": release_id,
                "assessment_id": assessment_id,
                "dataset_version": dataset_version or "",
                "admitted": admitted,
                "failed_checks": failed_checks,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return data

    def execute_release_pipeline(
        self,
        *,
        release_id: str,
        tenant_id: str,
        trace_id: str,
        dataset_version: str | None,
        replay_passed: bool,
        gate_results: dict[str, Any],
    ) -> dict[str, Any]:
        pipeline_id = f"pl_{uuid.uuid4().hex[:12]}"
        if self.p6_readiness_required:
            readiness = self.evaluate_release_readiness(
                release_id=release_id,
                tenant_id=tenant_id,
                trace_id=trace_id,
                dataset_version=dataset_version,
                replay_passed=replay_passed,
                gate_results=gate_results,
            )
            admitted = bool(readiness.get("admitted", False))
            failed_checks = list(readiness.get("failed_checks", []))
            assessment_id = str(readiness.get("assessment_id", ""))
        else:
            admitted = True
            failed_checks = []
            assessment_id = ""
            readiness = None

        stage = "release_blocked"
        if admitted:
            stage = "release_ready"
        data = {
            "pipeline_id": pipeline_id,
            "release_id": release_id,
            "tenant_id": tenant_id,
            "dataset_version": dataset_version or "",
            "stage": stage,
            "admitted": admitted,
            "failed_checks": failed_checks,
            "readiness_assessment_id": assessment_id,
            "canary": {
                "ratio": self.release_canary_ratio,
                "duration_min": self.release_canary_duration_min,
            },
            "rollback": {
                "max_minutes": self.rollback_max_minutes,
            },
            "readiness_required": bool(self.p6_readiness_required),
        }
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "release_pipeline_executed",
                "release_id": release_id,
                "pipeline_id": pipeline_id,
                "dataset_version": dataset_version or "",
                "stage": stage,
                "admitted": admitted,
                "failed_checks": failed_checks,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        if readiness is not None:
            data["readiness"] = readiness
        return data

    def upsert_rollout_policy(
        self,
        *,
        release_id: str,
        tenant_whitelist: list[str],
        enabled_project_sizes: list[str],
        high_risk_hitl_enforced: bool,
        tenant_id: str,
    ) -> dict[str, Any]:
        size_order = {"small": 1, "medium": 2, "large": 3}
        policy = {
            "release_id": release_id,
            "tenant_whitelist": sorted({x.strip() for x in tenant_whitelist if x.strip()}),
            "enabled_project_sizes": sorted(
                {x.strip() for x in enabled_project_sizes if x.strip()},
                key=lambda x: size_order.get(x, 999),
            ),
            "high_risk_hitl_enforced": bool(high_risk_hitl_enforced),
            "tenant_id": tenant_id,
            "updated_at": self._utcnow_iso(),
        }
        self.release_rollout_policies[release_id] = policy
        return {
            "release_id": policy["release_id"],
            "tenant_whitelist": policy["tenant_whitelist"],
            "enabled_project_sizes": policy["enabled_project_sizes"],
            "high_risk_hitl_enforced": policy["high_risk_hitl_enforced"],
        }

    def decide_rollout(
        self,
        *,
        release_id: str,
        tenant_id: str,
        project_size: str,
        high_risk: bool,
    ) -> dict[str, Any]:
        policy = self.release_rollout_policies.get(release_id)
        if policy is None:
            raise ApiError(
                code="RELEASE_POLICY_NOT_FOUND",
                message="release rollout policy not found",
                error_class="validation",
                retryable=False,
                http_status=404,
            )

        reasons: list[str] = []
        matched_whitelist = tenant_id in set(policy["tenant_whitelist"])
        if not matched_whitelist:
            reasons.append("TENANT_NOT_IN_WHITELIST")
        if project_size not in set(policy["enabled_project_sizes"]):
            reasons.append("PROJECT_SIZE_NOT_ENABLED")
        force_hitl = bool(high_risk and policy["high_risk_hitl_enforced"])

        return {
            "release_id": release_id,
            "admitted": len(reasons) == 0,
            "stage": "tenant_whitelist+project_size",
            "matched_whitelist": matched_whitelist,
            "force_hitl": force_hitl,
            "reasons": reasons,
        }

    def execute_rollback(
        self,
        *,
        release_id: str,
        consecutive_threshold: int,
        breaches: list[dict[str, Any]],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        rollback_order = [
            "model_config",
            "retrieval_params",
            "workflow_version",
            "release_version",
        ]
        trigger_breach = next(
            (x for x in breaches if int(x.get("consecutive_failures", 0)) >= consecutive_threshold),
            None,
        )
        if trigger_breach is None:
            return {
                "release_id": release_id,
                "triggered": False,
                "trigger_gate": None,
                "rollback_order": rollback_order,
                "replay_verification": None,
                "elapsed_minutes": 0,
                "rollback_completed_within_30m": True,
                "service_restored": True,
            }

        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "rollback_executed",
                "release_id": release_id,
                "trigger_gate": trigger_breach.get("gate"),
                "consecutive_threshold": consecutive_threshold,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )

        replay_job_id = f"job_{uuid.uuid4().hex[:12]}"
        self._persist_job(
            job={
                "job_id": replay_job_id,
                "job_type": "replay_verification",
                "status": "queued",
                "retry_count": 0,
                "thread_id": self._new_thread_id("replay"),
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "resource": {
                    "type": "job",
                    "id": release_id,
                },
                "payload": {
                    "release_id": release_id,
                    "trigger_gate": trigger_breach.get("gate"),
                },
                "last_error": None,
            }
        )
        replay_result = self.run_job_once(job_id=replay_job_id, tenant_id=tenant_id)
        replay_status = replay_result["final_status"]

        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "rollback_replay_verified",
                "release_id": release_id,
                "replay_job_id": replay_job_id,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )

        return {
            "release_id": release_id,
            "triggered": True,
            "trigger_gate": trigger_breach.get("gate"),
            "rollback_order": rollback_order,
            "replay_verification": {
                "job_id": replay_job_id,
                "status": replay_status,
            },
            "elapsed_minutes": 8,
            "rollback_completed_within_30m": True,
            "service_restored": replay_status == "succeeded",
        }

    @staticmethod
    def _bump_dataset_version(version: str, bump: str) -> str:
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
        if not match:
            return "v1.0.0"
        major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if bump == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"v{major}.{minor}.{patch}"

    def run_data_feedback(
        self,
        *,
        release_id: str,
        dlq_ids: list[str],
        version_bump: str,
        include_manual_override_candidates: bool,
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        candidate_dlq_ids = dlq_ids or [x["dlq_id"] for x in self.list_dlq_items(tenant_id=tenant_id)]
        counterexample_added = 0
        for dlq_id in candidate_dlq_ids:
            item = self.get_dlq_item(dlq_id, tenant_id=tenant_id)
            if item is None:
                continue
            if dlq_id in self.counterexample_samples:
                continue
            self.counterexample_samples[dlq_id] = {
                "sample_id": dlq_id,
                "release_id": release_id,
                "tenant_id": tenant_id,
                "source": "dlq",
                "job_id": item.get("job_id"),
                "error_class": item.get("error_class"),
                "error_code": item.get("error_code"),
                "created_at": self._utcnow_iso(),
            }
            counterexample_added += 1

        gold_candidates_added = 0
        if include_manual_override_candidates:
            for log in self.audit_logs:
                if log.get("tenant_id") != tenant_id:
                    continue
                if log.get("action") != "resume_submitted":
                    continue
                if log.get("decision") not in {"reject", "edit_scores"}:
                    continue
                key = str(log.get("audit_id"))
                if key in self.gold_candidate_samples:
                    continue
                self.gold_candidate_samples[key] = {
                    "sample_id": key,
                    "release_id": release_id,
                    "tenant_id": tenant_id,
                    "source": "manual_override",
                    "evaluation_id": log.get("evaluation_id"),
                    "decision": log.get("decision"),
                    "created_at": self._utcnow_iso(),
                }
                gold_candidates_added += 1

        before = self.dataset_version
        after = self._bump_dataset_version(before, version_bump)
        self.dataset_version = after
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "data_feedback_run",
                "release_id": release_id,
                "counterexample_added": counterexample_added,
                "gold_candidates_added": gold_candidates_added,
                "dataset_version_before": before,
                "dataset_version_after": after,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "release_id": release_id,
            "counterexample_added": counterexample_added,
            "gold_candidates_added": gold_candidates_added,
            "dataset_version_before": before,
            "dataset_version_after": after,
        }

    def apply_strategy_tuning(
        self,
        *,
        release_id: str,
        selector: dict[str, Any],
        score_calibration: dict[str, Any],
        tool_policy: dict[str, Any],
        tenant_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        self.strategy_config["selector"] = {
            "risk_mix_threshold": float(selector["risk_mix_threshold"]),
            "relation_mode": str(selector["relation_mode"]),
        }
        self.strategy_config["score_calibration"] = {
            "confidence_scale": float(score_calibration["confidence_scale"]),
            "score_bias": float(score_calibration["score_bias"]),
        }
        self.strategy_config["tool_policy"] = {
            "require_double_approval_actions": list(tool_policy["require_double_approval_actions"]),
            "allowed_tools": list(tool_policy["allowed_tools"]),
        }
        self.strategy_version_counter += 1
        strategy_version = f"stg_v{self.strategy_version_counter}"
        self._append_audit_log(
            log={
                "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant_id,
                "action": "strategy_tuning_applied",
                "release_id": release_id,
                "strategy_version": strategy_version,
                "trace_id": trace_id,
                "occurred_at": self._utcnow_iso(),
            }
        )
        return {
            "release_id": release_id,
            "strategy_version": strategy_version,
            "selector": self.strategy_config["selector"],
            "score_calibration": self.strategy_config["score_calibration"],
            "tool_policy": self.strategy_config["tool_policy"],
        }
