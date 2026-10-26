
import pytest

import semantic_retrieval as semantic


def test_cosine_similarity_of_identical_vectors():
    score = semantic._cosine_similarity(
        [1.0, 0.0],
        [1.0, 0.0],
    )

    assert score == pytest.approx(1.0)


def test_cosine_similarity_of_orthogonal_vectors():
    score = semantic._cosine_similarity(
        [1.0, 0.0],
        [0.0, 1.0],
    )

    assert score == pytest.approx(0.0)


def test_cosine_similarity_rejects_mismatched_dimensions():
    with pytest.raises(ValueError):
        semantic._cosine_similarity([1.0], [1.0, 2.0])


def test_empty_question_is_rejected():
    with pytest.raises(ValueError):
        semantic.retrieve_runbooks_semantic("   ")


def test_invalid_top_k_is_rejected():
    with pytest.raises(ValueError):
        semantic.retrieve_runbooks_semantic(
            "inventory",
            top_k=0,
        )


def test_boolean_top_k_is_rejected():
    with pytest.raises(ValueError):
        semantic.retrieve_runbooks_semantic(
            "inventory",
            top_k=True,
        )


def test_semantic_retriever_ranks_by_similarity(
    monkeypatch,
    tmp_path,
):
    runbook = tmp_path / "example.md"
    runbook.write_text(
        "# Example\n"
        "## Stock investigation\n"
        "Investigate inventory mismatches.\n"
        "## API failures\n"
        "Investigate service timeouts.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(semantic, "RUNBOOK_DIR", tmp_path)

    def fake_embed(text):
        if text == "stock out of sync":
            return [1.0, 0.0]

        if "Stock investigation" in text:
            return [0.99, 0.01]

        return [0.0, 1.0]

    monkeypatch.setattr(semantic, "_embed_text", fake_embed)

    results = semantic.retrieve_runbooks_semantic(
        "stock out of sync",
        top_k=2,
    )

    assert len(results) == 2
    assert results[0]["section"] == "Stock investigation"
    assert results[0]["score"] > results[1]["score"]


def test_embedding_is_cached(monkeypatch):
    calls = []

    class FakeEmbedding:
        embeddings = [[0.5, 0.5]]

    class FakeClient:
        def embed(self, **kwargs):
            calls.append(kwargs["input"])
            return FakeEmbedding()

    semantic._embed_text.cache_clear()
    semantic._get_ollama_client.cache_clear()

    monkeypatch.setattr(
        semantic,
        "_get_ollama_client",
        lambda: FakeClient(),
    )

    try:
        first = semantic._embed_text("inventory discrepancy")
        second = semantic._embed_text("inventory discrepancy")

        assert first == second
        assert calls == ["inventory discrepancy"]
    finally:
        semantic._embed_text.cache_clear()
