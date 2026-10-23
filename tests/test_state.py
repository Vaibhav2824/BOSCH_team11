
from state import IncidentState


def test_incident_state_accepts_initial_status():
    state: IncidentState = {
        "incident_id": "test-001",
        "status": "NEW",
    }

    assert state["incident_id"] == "test-001"
    assert state["status"] == "NEW"


def test_incident_state_accepts_diagnosis_fields():
    state: IncidentState = {
        "status": "DIAGNOSED",
        "diagnosed_component": "payment",
        "suspected_cause": "dependency failure",
        "confidence": 0.85,
        "cited_evidence_ids": ["ev-001", "ev-002"],
    }

    assert state["diagnosed_component"] == "payment"
    assert state["confidence"] == 0.85
    assert len(state["cited_evidence_ids"]) == 2
