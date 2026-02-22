def test_success_response_contains_trace_id_and_success_envelope(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("x-trace-id")
    assert resp.headers.get("x-request-id")

    body = resp.json()
    assert body["success"] is True
    assert body["data"] == {"status": "ok"}
    assert "trace_id" in body["meta"]
    assert body["meta"]["trace_id"]


def test_error_response_contains_standard_error_object(client):
    resp = client.get("/route-not-exists")
    assert resp.status_code == 404
    assert resp.headers.get("x-trace-id")
    assert resp.headers.get("x-request-id")

    body = resp.json()
    assert body["success"] is False
    assert set(body["error"].keys()) >= {"code", "message", "retryable", "class"}
    assert "trace_id" in body["meta"]
    assert body["meta"]["trace_id"]
