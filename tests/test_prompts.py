
from langchain_core.messages import HumanMessage, SystemMessage

from prompts import (
    build_diagnosis_messages,
    build_investigation_messages,
    build_reviewer_messages,
)


def test_investigation_messages_include_alert_and_evidence():
    messages = build_investigation_messages(
        alert={"name": "HighPaymentLatency"},
        symptoms=["Payment requests are slow"],
        evidence=[{"id": "ev-001", "value": "latency increased"}],
    )

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert "HighPaymentLatency" in messages[1].content
    assert "ev-001" in messages[1].content


def test_diagnosis_messages_include_instructions_and_summary():
    messages = build_diagnosis_messages(
        alert={"name": "PaymentFailure"},
        investigation_summary="Payment dependency is returning errors",
    )

    assert "evidence" in messages[0].content.lower()
    assert "PaymentFailure" in messages[1].content
    assert "dependency" in messages[1].content


def test_reviewer_messages_include_diagnosis():
    messages = build_reviewer_messages(
        diagnosis={
            "component": "payment",
            "cause": "dependency failure",
        },
        evidence=[{"id": "ev-002", "value": "dependency errors"}],
    )

    assert isinstance(messages[0], SystemMessage)
    assert "reviewer" in messages[0].content.lower()
    assert "ev-002" in messages[1].content
