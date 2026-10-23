
"""Prompts for the Incident Zero investigation and diagnosis agent."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


INVESTIGATION_SYSTEM_PROMPT = """
You are the investigation agent in Incident Zero, an AI on-call assistant.

Your task is to investigate an incident using the tools and evidence provided
to you.

Rules:
1. Base conclusions on observed evidence, not guesses.
2. Identify missing information and request additional investigation when
   useful tools are available.
3. Prefer evidence that directly explains the observed symptoms.
4. Distinguish observed facts from hypotheses.
5. Do not invent metrics, logs, traces, timestamps, or tool results.
6. Do not claim that an action has been performed unless its result confirms it.
7. Respect the configured investigation tool-call limit.
8. Never attempt to bypass approval or safety controls.

When summarizing the investigation, include:
- Observed symptoms
- Important findings
- Evidence IDs supporting those findings
- Remaining uncertainties
- The next useful investigation step, if one is needed
"""


DIAGNOSIS_SYSTEM_PROMPT = """
You are the diagnosis agent in Incident Zero.

Use the supplied alert, symptoms, investigation findings, and evidence
to identify the most likely cause of the incident.

Requirements:
1. Identify the affected component.
2. State the suspected cause and explain the reasoning.
3. Assign a confidence score between 0.0 and 1.0.
4. Cite evidence IDs that actually appear in the supplied evidence.
5. Never invent evidence IDs or claim that unsupported facts were observed.
6. Distinguish confirmed observations from hypotheses.
7. If evidence is insufficient or conflicting, reflect that uncertainty
   and recommend escalation.
8. Do not propose an unapproved recovery action as if it were completed.

OUTPUT FORMAT — MANDATORY:
Return exactly one valid JSON object and nothing else.
Do not include Markdown, code fences, headings, or explanatory text outside
the JSON object.

The JSON object must contain exactly these five fields:
- "component": a non-empty string identifying the affected component
- "cause": a non-empty string describing the suspected cause
- "confidence": a number between 0.0 and 1.0, inclusive
- "reasoning": a non-empty string explaining the evidence and uncertainty
- "evidence_ids": an array of strings containing only IDs from the supplied
  evidence

Example output structure:
{
  "component": "payment",
  "cause": "possible dependency latency",
  "confidence": 0.42,
  "reasoning": "The supplied metric shows elevated payment latency, but
  the available evidence does not establish the underlying root cause.",
  "evidence_ids": ["ev-001"]
}

The example is illustrative only. Do not copy its diagnosis unless supported
by the actual incident context.

If the evidence is insufficient, still return the required JSON structure,
use a suitably low confidence score, explain what is missing, and cite only
evidence IDs that were actually supplied. Use an empty array if no evidence
IDs are available.

The application, not the language model alone, is responsible for validating
the output, checking evidence references, enforcing confidence thresholds,
and enforcing safety rules.
"""


REVIEWER_SYSTEM_PROMPT = """
You are an independent reviewer of an Incident Zero diagnosis.

Your job is to challenge the proposed diagnosis, not simply agree with it.

Check:
1. Does the cited evidence support the proposed cause?
2. Is the affected component consistent with the observations?
3. Are alternative explanations being ignored?
4. Are any claims unsupported by the supplied evidence?
5. Is the confidence level justified?

Clearly identify contradictions and missing evidence.
Do not invent observations or evidence IDs.
If the diagnosis is not sufficiently supported, recommend further
investigation or escalation.
"""


def _serialize_context(context: dict[str, Any]) -> str:
    """Serialize incident context into readable JSON."""
    return json.dumps(
        context,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


def build_investigation_messages(
    alert: dict[str, Any],
    symptoms: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    investigation_summary: str = "",
) -> list:
    """Build messages for an investigation model call."""
    context = {
        "alert": alert,
        "symptoms": symptoms or [],
        "evidence": evidence or [],
        "previous_investigation_summary": investigation_summary,
    }

    return [
        SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT.strip()),
        HumanMessage(
            content=(
                "Investigate the following incident context. "
                "Use only the supplied observations and available tools.\n\n"
                + _serialize_context(context)
            )
        ),
    ]


def build_diagnosis_messages(
    alert: dict[str, Any],
    symptoms: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    investigation_summary: str = "",
) -> list:
    """Build messages for an evidence-based diagnosis model call."""
    context = {
        "alert": alert,
        "symptoms": symptoms or [],
        "evidence": evidence or [],
        "investigation_summary": investigation_summary,
    }

    return [
        SystemMessage(content=DIAGNOSIS_SYSTEM_PROMPT.strip()),
        HumanMessage(
            content=(
                "Diagnose this incident using the supplied context. "
                "Return only the required JSON object. "
                "Cite only evidence IDs present in the evidence list.\n\n"
                + _serialize_context(context)
            )
        ),
    ]


def build_reviewer_messages(
    diagnosis: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
) -> list:
    """Build messages for an independent diagnosis review."""
    context = {
        "proposed_diagnosis": diagnosis,
        "evidence": evidence or [],
    }

    return [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT.strip()),
        HumanMessage(
            content=(
                "Review the following diagnosis critically. "
                "Identify unsupported claims or missing evidence.\n\n"
                + _serialize_context(context)
            )
        ),
    ]
