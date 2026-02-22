def _valid_eval_payload() -> dict:
    return {
        "project_id": "prj_001",
        "supplier_id": "sup_001",
        "rule_pack_version": "v1.0.0",
        "evaluation_scope": {
            "include_doc_types": ["bid", "attachment"],
            "force_hitl": False,
        },
        "query_options": {
            "mode_hint": "hybrid",
            "top_k": 60,
        },
    }


def test_missing_idempotency_key_returns_400(client):
    resp = client.post("/api/v1/evaluations", json=_valid_eval_payload())
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "IDEMPOTENCY_MISSING"


def test_same_key_same_body_returns_same_response(client):
    headers = {"Idempotency-Key": "idem_eval_1"}
    payload = _valid_eval_payload()

    first = client.post("/api/v1/evaluations", json=payload, headers=headers)
    second = client.post("/api/v1/evaluations", json=payload, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"] == second.json()["data"]


def test_same_key_different_body_returns_409(client):
    headers = {"Idempotency-Key": "idem_eval_2"}
    payload = _valid_eval_payload()
    payload_diff = _valid_eval_payload()
    payload_diff["query_options"]["top_k"] = 80

    first = client.post("/api/v1/evaluations", json=payload, headers=headers)
    second = client.post("/api/v1/evaluations", json=payload_diff, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
