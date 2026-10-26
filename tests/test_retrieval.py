
import pytest

from retrieval import retrieve_runbooks, tokenize


def test_tokenize_normalizes_words():
    assert tokenize("Inventory FAILURE, SKU-101!") == {
        "inventory",
        "failure",
        "sku",
        "101",
    }


def test_retrieves_inventory_runbook():
    results = retrieve_runbooks(
        "How do I investigate an inventory discrepancy?"
    )

    assert results
    assert any(
        result["source"] == "inventory_discrepancy.md"
        for result in results
    )


def test_retrieves_integration_failure_runbook():
    results = retrieve_runbooks(
        "What should I check when an API times out?"
    )

    assert results
    assert any(
        result["source"] == "integration_failure.md"
        for result in results
    )


def test_results_are_ranked_highest_score_first():
    results = retrieve_runbooks(
        "inventory API failure stock inventory"
    )

    scores = [result["score"] for result in results]
    assert scores == sorted(scores, reverse=True)


def test_empty_question_is_rejected():
    with pytest.raises(ValueError):
        retrieve_runbooks("   ")


def test_invalid_top_k_is_rejected():
    with pytest.raises(ValueError):
        retrieve_runbooks("inventory", top_k=0)


def test_boolean_top_k_is_rejected():
    with pytest.raises(ValueError):
        retrieve_runbooks("inventory", top_k=True)
