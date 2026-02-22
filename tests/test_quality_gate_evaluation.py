def _payload(
    *,
    context_precision: float = 0.82,
    context_recall: float = 0.81,
    faithfulness: float = 0.91,
    response_relevancy: float = 0.87,
    hallucination_rate: float = 0.03,
    citation_resolvable_rate: float = 0.99,
) -> dict:
    return {
        "dataset_id": "ds_gate_d_smoke",
        "metrics": {
            "ragas": {
                "context_precision": context_precision,
                "context_recall": context_recall,
                "faithfulness": faithfulness,
                "response_relevancy": response_relevancy,
            },
            "deepeval": {"hallucination_rate": hallucination_rate},
            "citation": {"resolvable_rate": citation_resolvable_rate},
        },
    }


def test_quality_gate_passes_when_all_metrics_meet_thresholds(client):
    resp = client.post(
        "/api/v1/internal/quality-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["gate"] == "quality"
    assert data["dataset_id"] == "ds_gate_d_smoke"
    assert data["passed"] is True
    assert data["failed_checks"] == []
    assert data["ragchecker"]["triggered"] is False
    assert data["ragchecker"]["reason_codes"] == []


def test_quality_gate_blocks_and_triggers_ragchecker_when_metrics_degrade(client):
    resp = client.post(
        "/api/v1/internal/quality-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_payload(
            context_precision=0.79,
            hallucination_rate=0.06,
            citation_resolvable_rate=0.97,
        ),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["passed"] is False
    assert "RAGAS_CONTEXT_PRECISION_LOW" in data["failed_checks"]
    assert "DEEPEVAL_HALLUCINATION_RATE_HIGH" in data["failed_checks"]
    assert "CITATION_RESOLVABLE_RATE_LOW" in data["failed_checks"]
    assert data["ragchecker"]["triggered"] is True
    assert set(data["ragchecker"]["reason_codes"]) == set(data["failed_checks"])


def test_quality_gate_requires_internal_header(client):
    resp = client.post(
        "/api/v1/internal/quality-gates/evaluate",
        json=_payload(),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"


def test_quality_gate_rejects_invalid_metric_range(client):
    resp = client.post(
        "/api/v1/internal/quality-gates/evaluate",
        headers={"x-internal-debug": "true"},
        json=_payload(context_precision=1.2),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "REQ_VALIDATION_FAILED"
