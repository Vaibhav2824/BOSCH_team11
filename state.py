
"""Shared state definition for the Incident Zero agent."""

from typing import Any, Literal, TypedDict


IncidentStatus = Literal[
    "NEW",
    "INVESTIGATING",
    "DIAGNOSED",
    "AWAITING_APPROVAL",
    "ESCALATED",
    "REJECTED",
    "CLOSED",
    "APPROVED",
    "EXECUTING",
    "VERIFYING",
    "RESOLVED",
    "RECOVERY_UNCONFIRMED",
    "ROLLED_BACK",
]


class IncidentState(TypedDict, total=False):
    """Information shared between nodes in the incident workflow.

    Nodes read the fields they need and return updates to the state.
    """

    # Incident identification and current status
    incident_id: str
    status: IncidentStatus

    # Initial alert and observed symptoms
    alert: dict[str, Any]
    symptoms: list[str]

    # Evidence collected from logs, metrics and traces
    evidence: list[dict[str, Any]]
    cited_evidence_ids: list[str]

    # Investigation progress
    investigation_steps: int
    investigation_summary: str

    # Diagnosis produced by the diagnosis node
    diagnosed_component: str
    suspected_cause: str
    confidence: float
    diagnosis_reasoning: str

    # Escalation and reviewer feedback
    escalation_reason: str
    reviewer_agrees: bool
    reviewer_feedback: str

    # Additional context for later workflow stages
    action_proposal: dict[str, Any]
    verification_result: dict[str, Any]
    report: dict[str, Any]
