
"""LLM configuration and invocation helpers for Incident Zero."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from groq import RateLimitError
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq


# Model IDs can be overridden using environment variables.
PRIMARY_MODEL = os.getenv(
    "INCIDENT_ZERO_PRIMARY_MODEL",
    "openai/gpt-oss-120b",
)

REVIEWER_MODEL = os.getenv(
    "INCIDENT_ZERO_REVIEWER_MODEL",
    "qwen/qwen3.8-27b",
)

FALLBACK_MODEL = os.getenv(
    "INCIDENT_ZERO_FALLBACK_MODEL",
    "openai/gpt-oss-20b",
)


class AllModelsRateLimited(RuntimeError):
    """Raised when the primary and fallback models are rate-limited."""


def get_model(role: str = "investigate") -> ChatGroq:
    """Create a configured Groq model for the requested agent role."""
    if role in ("investigate", "diagnose"):
        model_name = PRIMARY_MODEL
    elif role == "review":
        model_name = REVIEWER_MODEL
    else:
        raise ValueError(
            f"Unknown model role: {role!r}. "
            "Use 'investigate', 'diagnose', or 'review'."
        )

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError(
            "GROQ_API_KEY is not set. Configure it before calling Groq."
        )

    return ChatGroq(
        model=model_name,
        temperature=0,
        max_retries=0,
        timeout=30,
    )


def get_fallback_model() -> ChatGroq:
    """Create the configured fallback Groq model."""
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError(
            "GROQ_API_KEY is not set. Configure it before calling Groq."
        )

    return ChatGroq(
        model=FALLBACK_MODEL,
        temperature=0,
        max_retries=0,
        timeout=30,
    )


def _replay_cache_dir() -> Path:
    """Return the development replay-cache directory."""
    directory = Path(
        os.getenv(
            "INCIDENT_ZERO_REPLAY_CACHE_DIR",
            r"D:\uv\incident-zero-replay-cache",
        )
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _replay_cache_key(messages: list, role: str) -> str:
    """Generate a stable key from the role, format, and input messages."""
    serializable_messages = []

    for message in messages:
        serializable_messages.append(
            {
                "type": getattr(
                    message, "type", type(message).__name__
                ),
                "content": str(
                    getattr(message, "content", message)
                ),
            }
        )

    payload = json.dumps(
        {
            "role": role,
            "response_format": (
                "json_object" if role == "diagnose" else None
            ),
            "messages": serializable_messages,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_replay(messages: list, role: str = "investigate"):
    """Load a cached AI response when replay mode is enabled."""
    if os.getenv("INCIDENT_ZERO_REPLAY_CACHE", "0") != "1":
        return None

    cache_file = (
        _replay_cache_dir()
        / f"{_replay_cache_key(messages, role)}.json"
    )

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return AIMessage(content=data["content"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        # An invalid cache entry should not crash the agent.
        return None


def save_replay(
    messages: list,
    response: Any,
    role: str = "investigate",
) -> None:
    """Save a text response when replay mode is enabled."""
    if os.getenv("INCIDENT_ZERO_REPLAY_CACHE", "0") != "1":
        return

    content = getattr(response, "content", str(response))

    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)

    cache_file = (
        _replay_cache_dir()
        / f"{_replay_cache_key(messages, role)}.json"
    )

    cache_file.write_text(
        json.dumps({"content": content}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _retry_after_seconds(exc: Exception) -> float:
    """Read a numeric Retry-After header from a rate-limit exception."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}
    retry_after = headers.get("retry-after")

    try:
        return max(0.0, float(retry_after)) if retry_after else 0.0
    except (TypeError, ValueError):
        return 0.0


def _invoke_model(model: ChatGroq, messages: list, role: str):
    """Invoke a model, enforcing JSON output for diagnosis."""
    if role == "diagnose":
        # The diagnosis parser expects a JSON object, not prose.
        model = model.bind(
            response_format={"type": "json_object"}
        )

    return model.invoke(messages)


def invoke_with_fallback(messages: list, role: str = "investigate"):
    """Use replay cache, then primary model, then fallback model.

    Diagnosis calls use JSON mode on both models.
    Only rate-limit errors trigger fallback. Other API errors are allowed
    to propagate so the caller can handle them appropriately.
    """
    if role not in ("investigate", "diagnose", "review"):
        raise ValueError(
            f"Unknown model role: {role!r}. "
            "Use 'investigate', 'diagnose', or 'review'."
        )

    # Check cache before creating models or requiring an API key.
    cached = load_replay(messages, role)
    if cached is not None:
        return cached

    for model_name in ("primary", "fallback"):
        model = (
            get_model(role)
            if model_name == "primary"
            else get_fallback_model()
        )

        try:
            response = _invoke_model(model, messages, role)
            save_replay(messages, response, role)
            return response

        except RateLimitError as exc:
            if model_name == "fallback":
                raise AllModelsRateLimited(
                    "Primary and fallback models were rate-limited. "
                    "Escalate the incident instead of guessing a diagnosis."
                ) from exc

            # Wait only for short delays, then try the fallback.
            delay = _retry_after_seconds(exc)
            if 0 < delay <= 2:
                time.sleep(delay)

    raise AllModelsRateLimited(
        "No model could complete the request."
    )
