from __future__ import annotations

import os
import uuid
from typing import Any

from app.errors import ApiError
from app.mock_llm import MOCK_LLM_ENABLED, mock_retrieve_evidence
from app.runtime_profile import true_stack_required


class StoreEvalMixin:
    def create_evaluation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.evaluation_nodes import EvaluationState, run_evaluation_nodes_sequentially

        evaluation_id = f"ev_{uuid.uuid4().hex[:12]}"
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        thread_id = self._new_thread_id("eval")
        tenant_id = payload.get("tenant_id", "tenant_default")

        initial_state: EvaluationState = {
            "tenant_id": tenant_id,
            "project_id": str(payload.get("project_id") or ""),
            "evaluation_id": evaluation_id,
            "supplier_id": str(payload.get("supplier_id") or ""),
            "trace_id": str(payload.get("trace_id") or ""),
            "thread_id": thread_id,
            "job_id": job_id,
            "payload": payload,
            "rule_pack_version": str(payload.get("rule_pack_version") or ""),
            "include_doc_types": payload.get("evaluation_scope", {}).get("include_doc_types", []),
            "force_hitl": bool(payload.get("evaluation_scope", {}).get("force_hitl", False)),
            "status": "running",
            "errors": [],
            "retry_count": 0,
        }

        final_state = run_evaluation_nodes_sequentially(initial_state, store=self)

        self._persist_job(
            job={
                "job_id": job_id,
                "job_type": "evaluation",
                "status": "queued",
                "retry_count": 0,
                "thread_id": thread_id,
                "tenant_id": tenant_id,
                "trace_id": payload.get("trace_id"),
                "resource": {
                    "type": "evaluation",
                    "id": evaluation_id,
                },
                "payload": payload,
                "last_error": None,
                "errors": [],
            }
        )
        self.append_outbox_event(
            tenant_id=tenant_id,
            event_type="job.created",
            aggregate_type="job",
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "job_type": "evaluation",
                "resource_type": "evaluation",
                "resource_id": evaluation_id,
            },
        )
        return {
            "evaluation_id": evaluation_id,
            "job_id": job_id,
            "status": "queued",
        }

    def get_evaluation_report_for_tenant(
        self,
        *,
        evaluation_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        report = None
        get_any = getattr(self.evaluation_reports_repository, "get_any", None)
        if callable(get_any):
            report = get_any(evaluation_id=evaluation_id)
        if report is None:
            report = self.evaluation_reports_repository.get(
                tenant_id=tenant_id,
                evaluation_id=evaluation_id,
            )
        if report is None:
            return None
        self._assert_tenant_scope(report.get("tenant_id", "tenant_default"), tenant_id)
        # Resolve citations to full objects per SSOT spec
        raw_citations = report.get("citations", [])
        if raw_citations and isinstance(raw_citations[0], str):
            # Old format: list of chunk_ids -> resolve to objects
            resolved_citations = self._resolve_citations_batch(raw_citations, include_quote=True)
        else:
            # Already resolved or empty
            resolved_citations = raw_citations

        # Resolve criteria_results citations (without quote per SSOT)
        raw_criteria = report.get("criteria_results", [])
        resolved_criteria = []
        for item in raw_criteria:
            item_copy = dict(item)
            item_citations = item_copy.get("citations", [])
            if item_citations and isinstance(item_citations[0], str):
                item_copy["citations"] = self._resolve_citations_batch(item_citations, include_quote=False)
            # Remove extra fields not in SSOT
            item_copy.pop("weight", None)
            item_copy.pop("citations_count", None)
            resolved_criteria.append(item_copy)

        return {
            "evaluation_id": report["evaluation_id"],
            "supplier_id": report["supplier_id"],
            "total_score": report["total_score"],
            "confidence": report["confidence"],
            "citation_coverage": report.get("citation_coverage", 0.0),
            "risk_level": report["risk_level"],
            "criteria_results": resolved_criteria,
            "citations": resolved_citations,
            "needs_human_review": report["needs_human_review"],
            "trace_id": report["trace_id"],
            "interrupt": report.get("interrupt"),
            "report_uri": report.get("report_uri"),
        }

    def _run_evaluation_workflow(
        self,
        *,
        job: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        evaluation_id = str(job.get("resource", {}).get("id") or "")
        thread_id = str(job.get("thread_id") or self._new_thread_id("eval"))
        trace_id = str(job.get("trace_id") or "")
        report: dict[str, Any] | None = None
        if evaluation_id:
            report = self.evaluation_reports.get(evaluation_id)
            if report is None:
                report = self.get_evaluation_report_for_tenant(evaluation_id=evaluation_id, tenant_id=tenant_id)
        needs_human_review = bool(report.get("needs_human_review", False)) if isinstance(report, dict) else False
        interrupt_payload = report.get("interrupt") if isinstance(report, dict) else None

        def _base_state() -> dict[str, Any]:
            return {
                "identity": {
                    "tenant_id": tenant_id,
                    "evaluation_id": evaluation_id,
                    "project_id": report.get("project_id") if isinstance(report, dict) else None,
                    "supplier_id": report.get("supplier_id") if isinstance(report, dict) else None,
                },
                "trace": {"trace_id": trace_id, "thread_id": thread_id},
                "review": {
                    "requires_human_review": needs_human_review,
                    "human_review_payload": interrupt_payload,
                },
                "output": {"status": "running"},
            }

        mode, langgraph_module = self._workflow_runtime_mode()
        state = _base_state()

        def _node(name: str, payload: dict[str, Any] | None = None):
            def _inner(current: dict[str, Any]) -> dict[str, Any]:
                self._append_node_checkpoint(
                    thread_id=thread_id,
                    job_id=str(job.get("job_id") or ""),
                    tenant_id=tenant_id,
                    node=name,
                    payload=payload,
                )
                return current

            return _inner

        if mode != "langgraph" and needs_human_review:
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="load_context",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="retrieve_evidence",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="evaluate_rules",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="score_with_llm",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="quality_gate",
                status="hitl",
                payload={"decision": "hitl"},
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=str(job.get("job_id") or ""),
                tenant_id=tenant_id,
                node="human_review_interrupt",
                status="needs_manual_decision",
                payload=interrupt_payload if isinstance(interrupt_payload, dict) else {},
            )
            job = self.transition_job_status(
                job_id=str(job.get("job_id") or ""),
                new_status="needs_manual_decision",
                tenant_id=tenant_id,
            )
            return {
                "job_id": str(job.get("job_id") or ""),
                "final_status": "needs_manual_decision",
                "thread_id": thread_id,
                "evaluation_id": evaluation_id,
            }

        if mode == "langgraph" and langgraph_module is not None:
            try:
                from app.langgraph_runtime import run_evaluation_graph

                return run_evaluation_graph(store=self, job=job, tenant_id=tenant_id)
            except Exception:
                if true_stack_required(os.environ):
                    raise
                mode = "compat"

        if mode != "langgraph":
            job_id_str = str(job.get("job_id") or "")
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="load_context",
                payload={"evaluation_id": evaluation_id, "project_id": report.get("project_id") if report else None},
            )

            retrieved_chunks: list[dict[str, Any]] = []
            if report and report.get("criteria_results"):
                for cr in report["criteria_results"]:
                    for cit in cr.get("citations") or []:
                        if isinstance(cit, dict) and cit.get("chunk_id"):
                            retrieved_chunks.append(cit)
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="retrieve_evidence",
                payload={"retrieved_count": len(retrieved_chunks)},
            )

            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="evaluate_rules",
                payload={"redline_conflict": report.get("redline_conflict", False) if report else False},
            )

            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="score_with_llm",
                payload={
                    "total_score": report.get("total_score") if report else None,
                    "confidence": report.get("confidence") if report else None,
                },
            )

            quality_decision = "pass"
            if report and report.get("needs_human_review"):
                quality_decision = "hitl"
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="quality_gate",
                payload={"decision": quality_decision},
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="finalize_report",
            )
            self._append_node_checkpoint(
                thread_id=thread_id,
                job_id=job_id_str,
                tenant_id=tenant_id,
                node="persist_result",
            )

        job = self.transition_job_status(
            job_id=str(job.get("job_id") or ""),
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        return {
            "job_id": str(job.get("job_id") or ""),
            "final_status": "succeeded",
            "thread_id": thread_id,
            "evaluation_id": evaluation_id,
        }

    def _run_resume_workflow(
        self,
        *,
        job: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        thread_id = str(job.get("thread_id") or self._new_thread_id("resume"))
        job_id = str(job.get("job_id") or "")
        mode, langgraph_module = self._workflow_runtime_mode()
        if mode == "langgraph" and langgraph_module is not None:
            try:
                from app.langgraph_runtime import run_resume_graph

                return run_resume_graph(store=self, job=job, tenant_id=tenant_id)
            except Exception:
                if true_stack_required(os.environ):
                    raise
                mode = "compat"

        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="resume_received",
        )
        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="finalize_report",
        )
        self._append_node_checkpoint(
            thread_id=thread_id,
            job_id=job_id,
            tenant_id=tenant_id,
            node="persist_result",
        )
        job = self.transition_job_status(
            job_id=job_id,
            new_status="succeeded",
            tenant_id=tenant_id,
        )
        return {
            "job_id": job_id,
            "final_status": "succeeded",
            "thread_id": thread_id,
        }

    def _retrieve_evidence_for_criteria(
        self,
        *,
        query: str,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        doc_scope: list[str],
        top_k: int = 5,
        criteria_id: str = "",
        evaluation_id: str = "",
        hard_constraint_pass: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence for a criteria: Chroma vector search > Mock LLM > stub."""
        if project_id and supplier_id:
            chroma_results = self._query_lightrag(
                tenant_id=tenant_id,
                project_id=project_id,
                supplier_id=supplier_id,
                query=query or criteria_id,
                selected_mode="hybrid",
                top_k=top_k,
                doc_scope=doc_scope,
            )
            if chroma_results:
                evidence: list[dict[str, Any]] = []
                for item in chroma_results:
                    chunk_id = str(item.get("chunk_id") or "")
                    if not chunk_id:
                        continue
                    meta = item.get("metadata", {})
                    evidence.append(
                        {
                            "chunk_id": chunk_id,
                            "page": int(meta.get("page", 1)),
                            "bbox": meta.get("bbox", [0.0, 0.0, 1.0, 1.0]),
                            "text": item.get("text", ""),
                            "score_raw": float(item.get("score_raw", 0.5)),
                            "tenant_id": tenant_id,
                            "supplier_id": supplier_id,
                            "document_id": str(meta.get("document_id", "")),
                        }
                    )
                if evidence:
                    return evidence

        if MOCK_LLM_ENABLED:
            return mock_retrieve_evidence(
                query=query,
                top_k=top_k,
                tenant_id=tenant_id,
                supplier_id=supplier_id,
                doc_scope=doc_scope,
            )

        citation_id = f"ck_{criteria_id}_{evaluation_id[:6]}" if hard_constraint_pass else "ck_rule_block_1"
        return [
            {
                "chunk_id": citation_id,
                "page": 1,
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "text": "stub citation",
                "score_raw": 0.78,
                "tenant_id": tenant_id,
                "supplier_id": supplier_id,
            }
        ]
