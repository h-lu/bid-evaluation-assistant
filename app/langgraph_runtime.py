from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.errors import ApiError

try:  # pragma: no cover - optional dependency at runtime
    from langgraph.checkpoint.base import BaseCheckpointSaver  # type: ignore
except Exception:  # pragma: no cover - langgraph not installed
    BaseCheckpointSaver = object  # type: ignore


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _safe_interrupt_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        data: dict[str, Any] = payload
    elif payload is None:
        data = {}
    else:
        data = {"value": payload}
    try:
        json.dumps(data, ensure_ascii=True)
    except TypeError:
        data = {"value": str(payload)}
    return data


@dataclass(frozen=True)
class WorkflowIdentity:
    thread_id: str
    job_id: str
    tenant_id: str


class StoreCheckpointSaver(BaseCheckpointSaver):  # type: ignore[misc]
    def __init__(self, *, store: Any) -> None:
        super().__init__()
        self._store = store

    def get_tuple(self, config):  # type: ignore[override]
        from langgraph.checkpoint.base import CheckpointTuple, get_checkpoint_id  # type: ignore

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        tenant_id = config["configurable"].get("tenant_id", "tenant_default")
        checkpoint_id = get_checkpoint_id(config)
        record = self._store.get_langgraph_checkpoint_record(
            thread_id=thread_id,
            tenant_id=tenant_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
        )
        if record is None:
            return None
        parent = record.get("parent_checkpoint_id")
        parent_config = (
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns, "checkpoint_id": parent}}
            if parent
            else None
        )
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": record.get("checkpoint_id"),
                    "tenant_id": tenant_id,
                }
            },
            checkpoint=record.get("checkpoint"),
            metadata=record.get("metadata", {}),
            parent_config=parent_config,
            pending_writes=record.get("pending_writes", []),
        )

    def list(self, config, *, filter=None, before=None, limit=None):  # type: ignore[override]
        from langgraph.checkpoint.base import CheckpointTuple, get_checkpoint_id  # type: ignore

        if config is None:
            return iter(())
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        tenant_id = config["configurable"].get("tenant_id", "tenant_default")
        checkpoint_id = get_checkpoint_id(config)
        items = self._store.list_langgraph_checkpoints(
            thread_id=thread_id,
            tenant_id=tenant_id,
            checkpoint_ns=checkpoint_ns,
        )
        if checkpoint_id:
            items = [item for item in items if item.get("checkpoint_id") == checkpoint_id]
        if before:
            before_id = get_checkpoint_id(before)
            if before_id:
                items = [item for item in items if item.get("checkpoint_id") < before_id]
        if limit is not None:
            items = items[: max(0, limit)]
        for record in items:
            parent = record.get("parent_checkpoint_id")
            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent,
                    }
                }
                if parent
                else None
            )
            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": record.get("checkpoint_id"),
                        "tenant_id": tenant_id,
                    }
                },
                checkpoint=record.get("checkpoint"),
                metadata=record.get("metadata", {}),
                parent_config=parent_config,
                pending_writes=record.get("pending_writes", []),
            )

    def put(self, config, checkpoint, metadata, new_versions):  # type: ignore[override]
        from langgraph.checkpoint.base import get_checkpoint_metadata  # type: ignore

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        tenant_id = config["configurable"].get("tenant_id", "tenant_default")
        record = {
            "kind": "langgraph_state",
            "thread_id": thread_id,
            "tenant_id": tenant_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint["id"],
            "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
            "checkpoint": checkpoint,
            "metadata": get_checkpoint_metadata(config, metadata),
            "pending_writes": [],
            "created_at": _utcnow_iso(),
        }
        self._store.upsert_langgraph_checkpoint(record=record)
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
                "tenant_id": tenant_id,
            }
        }

    def put_writes(self, config, writes, task_id, task_path=""):  # type: ignore[override]
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        tenant_id = config["configurable"].get("tenant_id", "tenant_default")
        checkpoint_id = config["configurable"].get("checkpoint_id")
        if not checkpoint_id:
            return
        record = self._store.get_langgraph_checkpoint_record(
            thread_id=thread_id,
            tenant_id=tenant_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
        )
        if record is None:
            return
        pending = list(record.get("pending_writes", []))
        for channel, value in writes:
            pending.append((task_id, channel, value))
        record["pending_writes"] = pending
        record["updated_at"] = _utcnow_iso()
        self._store.upsert_langgraph_checkpoint(record=record)

    def delete_thread(self, thread_id: str) -> None:  # type: ignore[override]
        self._store.delete_langgraph_checkpoints(thread_id=thread_id)


def build_evaluation_graph(*, store: Any, identity: WorkflowIdentity):
    from langgraph.graph import END, StateGraph  # type: ignore
    from langgraph.types import interrupt  # type: ignore

    def _node(name: str, payload: dict[str, Any] | None = None, status: str = "succeeded"):
        def _inner(state: dict[str, Any]) -> dict[str, Any]:
            store._append_node_checkpoint(
                thread_id=identity.thread_id,
                job_id=identity.job_id,
                tenant_id=identity.tenant_id,
                node=name,
                status=status,
                payload=payload or {},
            )
            return state

        return _inner

    def _quality_gate(state: dict[str, Any]) -> dict[str, Any]:
        review = state.get("review", {})
        requires_human_review = bool(review.get("requires_human_review", False))
        if requires_human_review:
            payload = _safe_interrupt_payload(review.get("human_review_payload"))
            store._append_node_checkpoint(
                thread_id=identity.thread_id,
                job_id=identity.job_id,
                tenant_id=identity.tenant_id,
                node="quality_gate",
                status="hitl",
                payload={"decision": "hitl"},
            )
            store._append_node_checkpoint(
                thread_id=identity.thread_id,
                job_id=identity.job_id,
                tenant_id=identity.tenant_id,
                node="human_review_interrupt",
                status="needs_manual_decision",
                payload=payload,
            )
            interrupt(payload)
        return _node("quality_gate", {"decision": "pass"})(state)

    graph = StateGraph(dict)
    graph.add_node("load_context", _node("load_context"))
    graph.add_node("retrieve_evidence", _node("retrieve_evidence"))
    graph.add_node("evaluate_rules", _node("evaluate_rules"))
    graph.add_node("score_with_llm", _node("score_with_llm"))
    graph.add_node("quality_gate", _quality_gate)
    graph.add_node("finalize_report", _node("finalize_report"))
    graph.add_node("persist_result", _node("persist_result"))
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "evaluate_rules")
    graph.add_edge("evaluate_rules", "score_with_llm")
    graph.add_edge("score_with_llm", "quality_gate")
    graph.add_edge("quality_gate", "finalize_report")
    graph.add_edge("finalize_report", "persist_result")
    graph.add_edge("persist_result", END)
    return graph


def run_evaluation_graph(*, store: Any, job: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    from langgraph.errors import GraphInterrupt  # type: ignore

    evaluation_id = str(job.get("resource", {}).get("id") or "")
    thread_id = str(job.get("thread_id") or store._new_thread_id("eval"))
    trace_id = str(job.get("trace_id") or "")
    report: dict[str, Any] | None = None
    if evaluation_id:
        report = store.evaluation_reports.get(evaluation_id)
        if report is None:
            report = store.get_evaluation_report_for_tenant(
                evaluation_id=evaluation_id, tenant_id=tenant_id
            )
    needs_human_review = bool(report.get("needs_human_review", False)) if isinstance(report, dict) else False
    interrupt_payload = report.get("interrupt") if isinstance(report, dict) else None
    state = {
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
    identity = WorkflowIdentity(thread_id=thread_id, job_id=str(job.get("job_id") or ""), tenant_id=tenant_id)
    graph = build_evaluation_graph(store=store, identity=identity)
    compiled = graph.compile(checkpointer=StoreCheckpointSaver(store=store))
    try:
        compiled.invoke(
            state,
            config={"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}},
        )
        job = store.transition_job_status(
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
    except GraphInterrupt:
        job = store.transition_job_status(
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


def run_resume_graph(*, store: Any, job: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    from langgraph.errors import GraphInterrupt  # type: ignore
    from langgraph.types import Command  # type: ignore

    thread_id = str(job.get("thread_id") or store._new_thread_id("resume"))
    payload = job.get("payload", {})
    resume_payload = {
        "decision": payload.get("decision"),
        "comment": payload.get("comment"),
        "editor": payload.get("editor"),
        "edited_scores": payload.get("edited_scores", []),
    }
    identity = WorkflowIdentity(thread_id=thread_id, job_id=str(job.get("job_id") or ""), tenant_id=tenant_id)
    graph = build_evaluation_graph(store=store, identity=identity)
    compiled = graph.compile(checkpointer=StoreCheckpointSaver(store=store))
    try:
        compiled.invoke(
            Command(resume=resume_payload),
            config={"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}},
        )
    except GraphInterrupt:
        raise ApiError(
            code="WF_INTERRUPT_RESUME_INVALID",
            message="resume rejected by workflow",
            error_class="business_rule",
            retryable=False,
            http_status=409,
        )
    job = store.transition_job_status(
        job_id=str(job.get("job_id") or ""),
        new_status="succeeded",
        tenant_id=tenant_id,
    )
    return {
        "job_id": str(job.get("job_id") or ""),
        "final_status": "succeeded",
        "thread_id": thread_id,
    }
