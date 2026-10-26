
import pytest

import ai_agent


def test_semantic_retrieval_failure_stops_agent(monkeypatch):
    def retrieval_failure(question, top_k=3):
        raise RuntimeError("Embedding service unavailable")

    def unexpected_ollama_client(**kwargs):
        pytest.fail(
            "The AI client should not start after retrieval fails."
        )

    monkeypatch.setattr(
        ai_agent,
        "retrieve_runbooks_semantic",
        retrieval_failure,
    )

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        unexpected_ollama_client,
    )

    with pytest.raises(
        RuntimeError,
        match="Embedding service unavailable",
    ):
        ai_agent.ask_commerceops(
            "How should I investigate an inventory mismatch?"
        )


def test_semantic_retrieval_receives_user_question(monkeypatch):
    received = {}

    def fake_retrieval(question, top_k=3):
        received["question"] = question
        received["top_k"] = top_k
        return []

    monkeypatch.setattr(
        ai_agent,
        "retrieve_runbooks_semantic",
        fake_retrieval,
    )

    # Stop execution immediately after retrieval so this test
    # does not need Ollama or a live inventory service.
    class RetrievalReached(Exception):
        pass

    def stop_after_retrieval():
        raise RetrievalReached()

    monkeypatch.setattr(
        ai_agent,
        "logger",
        ai_agent.logger,
    )

    # Replace the Ollama client with a minimal stub that fails
    # only when the first chat call is reached.
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat(self, **kwargs):
            raise RetrievalReached()

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        FakeClient,
    )

    with pytest.raises(RetrievalReached):
        ai_agent.ask_commerceops(
            "Why is online stock out of sync?"
        )

    assert received["question"] == (
        "Why is online stock out of sync?"
    )
    assert received["top_k"] == 3
