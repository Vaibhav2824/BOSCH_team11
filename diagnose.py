
"""Evidence-based diagnosis for the Incident Zero agent."""

import json
import os
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from llm import invoke_with_fallback
from prompts import build_diagnosis_messages
from state import IncidentState


class DiagnosisResult(BaseModel):
    """Structured diagnosis returned by the language model."""

    component: str = Field(min_length=1)
    cause: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


def _parse_diagnosis(content: Any) -> DiagnosisResult:
    """Parse and validate a JSON diagnosis from the model response."""
    if not isinstance(content, str):
        raise ValueError("The model response must be text.")

    text = content.strip()

    # Allow JSON enclosed in a Markdown code block.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("The model did not return valid JSON.") from exc

    return DiagnosisResult.model_validate(data)


def diagnose_incident(state: IncidentState) -> dict[str, Any]:
    """Diagnose an incident and return updates to the shared graph state.

    The model response is validated before its diagnosis is accepted.
    Invalid or unsupported diagnoses are escalated.
    """
    alert = state.get("alert", {})
    symptoms = state.get("symptoms", [])
    evidence = state.get("evidence", [])
    investigation_summary = state.get("investigation_summary", "")

    messages = build_diagnosis_messages(
        alert=alert,
        symptoms=symptoms,
        evidence=evidence,
        investigation_summary=investigation_summary,
    )

    try:
        response = invoke_with_fallback(messages, role="diagnose")
        diagnosis = _parse_diagnosis(response.content)

    except (ValueError, ValidationError, TypeError) as exc:
        return {
            "status": "ESCALATED",
            "escalation_reason": (
                f"Diagnosis output could not be validated: {exc}"
            ),
            "diagnosis_reasoning": (
                "No validated diagnosis was produced."
            ),
        }

    # Build the set of evidence IDs supplied to the diagnosis model.
    available_ids = {
        str(item["id"])
        for item in evidence
        if isinstance(item, dict) and item.get("id") is not None
    }

    # Reject any evidence references that were not actually supplied.
    invalid_ids = sorted(
        set(diagnosis.evidence_ids) - available_ids
    )

    if invalid_ids:
        return {
            "status": "ESCALATED",
            "escalation_reason": (
                "Diagnosis cited evidence IDs that were not supplied: "
                + ", ".join(invalid_ids)
            ),
            "diagnosis_reasoning": diagnosis.reasoning,
        }

    # A diagnosis must cite evidence to be accepted.
    if not diagnosis.evidence_ids:
        return {
            "status": "ESCALATED",
            "escalation_reason": (
                "Diagnosis contains no cited evidence."
            ),
            "diagnosis_reasoning": diagnosis.reasoning,
        }

    # Use the configured confidence threshold, defaulting to 0.7.
    try:
        threshold = float(
            os.getenv("INCIDENT_ZERO_CONFIDENCE_THRESHOLD", "0.7")
        )
    except ValueError:
        threshold = 0.7

    if not 0.0 <= threshold <= 1.0:
        threshold = 0.7

    # Escalate when the diagnosis is not sufficiently confident.
    if diagnosis.confidence < threshold:
        return {
            "status": "ESCALATED",
            "escalation_reason": (
                f"Diagnosis confidence {diagnosis.confidence:.2f} "
                f"is below the threshold {threshold:.2f}."
            ),
            "diagnosed_component": diagnosis.component,
            "suspected_cause": diagnosis.cause,
            "confidence": diagnosis.confidence,
            "diagnosis_reasoning": diagnosis.reasoning,
            "cited_evidence_ids": diagnosis.evidence_ids,
        }

    # Return a validated diagnosis for the next graph node.
    return {
        "status": "DIAGNOSED",
        "diagnosed_component": diagnosis.component,
        "suspected_cause": diagnosis.cause,
        "confidence": diagnosis.confidence,
        "diagnosis_reasoning": diagnosis.reasoning,
        "cited_evidence_ids": diagnosis.evidence_ids,
    }
