
import json

from langchain_core.messages import AIMessage

import diagnose


def make_state():
    return {
        "incident_id": "incident-001",
        "status": "INVESTIGATING",
        "alert": {"name": "HighPaymentLatency"},
        "symptoms": ["Payment requests are slow"],
        "evidence": [
            {
                "id": "ev-001",
                "source": "metrics",
                "value": "Payment latency is elevated",
            }
        ],
        "investigation_summary": "Payment latency increased.",
    }


def mock_response(monkeypatch, payload):
    monkeypatch.setattr(
        diagnose,
        "invoke_with_fallback",
        lambda messages, role: AIMessage(content=json.dumps(payload)),
    )


def valid_payload():
    return {
        "component": "payment",
        "cause": "dependency latency",
        "confidence": 0.9,
        "reasoning": "The supplied metric shows elevated payment latency.",
        "evidence_ids": ["ev-001"],
    }


def test_valid_diagnosis_is_accepted(monkeypatch):
    mock_response(monkeypatch, valid_payload())

    result = diagnose.diagnose_incident(make_state())

    assert result["status"] == "DIAGNOSED"
    assert result["diagnosed_component"] == "payment"
    assert result["cited_evidence_ids"] == ["ev-001"]


def test_unknown_evidence_id_causes_escalation(monkeypatch):
    payload = valid_payload()
    payload["evidence_ids"] = ["ev-does-not-exist"]
    mock_response(monkeypatch, payload)

    result = diagnose.diagnose_incident(make_state())

    assert result["status"] == "ESCALATED"
    assert "not supplied" in result["escalation_reason"]


def test_low_confidence_causes_escalation(monkeypatch):
    payload = valid_payload()
    payload["confidence"] = 0.4
    mock_response(monkeypatch, payload)

    result = diagnose.diagnose_incident(make_state())

    assert result["status"] == "ESCALATED"
    assert result["confidence"] == 0.4


def test_missing_evidence_causes_escalation(monkeypatch):
    payload = valid_payload()
    payload["evidence_ids"] = []
    mock_response(monkeypatch, payload)

    result = diagnose.diagnose_incident(make_state())

    assert result["status"] == "ESCALATED"
    assert "no cited evidence" in result["escalation_reason"]


def test_invalid_json_causes_escalation(monkeypatch):
    monkeypatch.setattr(
        diagnose,
        "invoke_with_fallback",
        lambda messages, role: AIMessage(content="not JSON"),
    )

    result = diagnose.diagnose_incident(make_state())

    assert result["status"] == "ESCALATED"
    assert "valid JSON" in result["escalation_reason"]
