
import httpx
import pytest
from groq import RateLimitError
from langchain_core.messages import AIMessage, HumanMessage

import llm


def test_replay_cache_saves_and_loads(monkeypatch, tmp_path):
    """A saved response can be loaded from the replay cache."""
    monkeypatch.setenv("INCIDENT_ZERO_REPLAY_CACHE", "1")
    monkeypatch.setenv("INCIDENT_ZERO_REPLAY_CACHE_DIR", str(tmp_path))

    messages = [HumanMessage(content="test incident")]

    llm.save_replay(
        messages,
        AIMessage(content="payment service is failing"),
    )

    response = llm.load_replay(messages)

    assert response is not None
    assert response.content == "payment service is failing"


def test_replay_cache_is_disabled_by_default(monkeypatch):
    """No cached response is returned when replay mode is disabled."""
    monkeypatch.delenv("INCIDENT_ZERO_REPLAY_CACHE", raising=False)

    messages = [HumanMessage(content="test incident")]

    assert llm.load_replay(messages) is None


def test_invoke_uses_cached_response(monkeypatch, tmp_path):
    """A cache hit must not create or call either model."""
    monkeypatch.setenv("INCIDENT_ZERO_REPLAY_CACHE", "1")
    monkeypatch.setenv("INCIDENT_ZERO_REPLAY_CACHE_DIR", str(tmp_path))

    messages = [HumanMessage(content="cached incident")]

    llm.save_replay(
        messages,
        AIMessage(content="saved answer"),
    )

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("Model should not be called on a cache hit")

    monkeypatch.setattr(llm, "get_model", should_not_be_called)
    monkeypatch.setattr(llm, "get_fallback_model", should_not_be_called)

    response = llm.invoke_with_fallback(messages)

    assert response.content == "saved answer"


def test_invoke_uses_fallback_after_rate_limit(monkeypatch):
    """A simulated HTTP 429 on the primary model triggers fallback."""
    monkeypatch.delenv("INCIDENT_ZERO_REPLAY_CACHE", raising=False)

    class FakeModel:
        def __init__(self, result=None, error=None):
            self.result = result
            self.error = error

        def invoke(self, messages):
            if self.error is not None:
                raise self.error
            return self.result

    # Construct a valid simulated HTTP 429 response.
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions",
    )
    response_429 = httpx.Response(429, request=request)

    rate_limit_error = RateLimitError(
        "rate limited",
        response=response_429,
        body=None,
    )

    primary = FakeModel(error=rate_limit_error)
    fallback = FakeModel(
        result=AIMessage(content="fallback answer"),
    )

    monkeypatch.setattr(llm, "get_model", lambda role: primary)
    monkeypatch.setattr(llm, "get_fallback_model", lambda: fallback)

    result = llm.invoke_with_fallback(
        [HumanMessage(content="new incident")]
    )

    assert result.content == "fallback answer"


def test_unknown_role_is_rejected(monkeypatch):
    """An unsupported model role raises ValueError."""
    monkeypatch.setenv("GROQ_API_KEY", "test-only-not-a-real-key")

    with pytest.raises(ValueError, match="Unknown model role"):
        llm.get_model("unknown")
