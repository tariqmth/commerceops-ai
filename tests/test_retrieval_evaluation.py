
import pytest

from retrieval import retrieve_runbooks
from retrieval_eval import EVALUATION_CASES


@pytest.mark.parametrize("case", EVALUATION_CASES)
def test_expected_runbook_is_ranked_first(case):
    results = retrieve_runbooks(
        case["question"],
        top_k=1,
    )

    assert results, (
        f"No runbook retrieved for: {case['question']}"
    )

    assert results[0]["source"] == case["expected_source"], (
        f"Question: {case['question']}\n"
        f"Expected: {case['expected_source']}\n"
        f"Actual: {results[0]['source']}"
    )
