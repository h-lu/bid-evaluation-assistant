import pytest

from app.errors import ApiError
from app.store import store


def test_valid_state_transitions_follow_sequence():
    created = store.create_evaluation_job({"trace_id": "trace_test"})
    job_id = created["job_id"]

    store.transition_job_status(job_id=job_id, new_status="running")
    store.transition_job_status(job_id=job_id, new_status="retrying")
    store.transition_job_status(job_id=job_id, new_status="running")
    store.transition_job_status(job_id=job_id, new_status="succeeded")

    assert store.get_job(job_id)["status"] == "succeeded"


def test_invalid_transition_raises_state_error():
    created = store.create_evaluation_job({"trace_id": "trace_test"})
    job_id = created["job_id"]

    with pytest.raises(ApiError) as exc:
        store.transition_job_status(job_id=job_id, new_status="failed")

    assert exc.value.code == "WF_STATE_TRANSITION_INVALID"
    assert exc.value.http_status == 409


def test_failed_must_come_after_dlq_recorded():
    created = store.create_evaluation_job({"trace_id": "trace_test"})
    job_id = created["job_id"]

    store.transition_job_status(job_id=job_id, new_status="running")
    store.transition_job_status(job_id=job_id, new_status="retrying")
    store.transition_job_status(job_id=job_id, new_status="dlq_pending")
    store.transition_job_status(job_id=job_id, new_status="dlq_recorded")
    store.transition_job_status(job_id=job_id, new_status="failed")

    assert store.get_job(job_id)["status"] == "failed"
