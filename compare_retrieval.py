
from retrieval import retrieve_runbooks
from semantic_retrieval import retrieve_runbooks_semantic
from retrieval_eval import EVALUATION_CASES


def evaluate_retriever(name, retriever):
    results = []

    print(f"\n{'=' * 60}")
    print(f"{name}")
    print("=" * 60)

    for case in EVALUATION_CASES:
        question = case["question"]
        expected = case["expected_source"]

        retrieved = retriever(question, top_k=3)
        sources = [item["source"] for item in retrieved]

        top1_correct = bool(sources) and sources[0] == expected
        top3_correct = expected in sources

        results.append({
            "top1": top1_correct,
            "top3": top3_correct,
        })

        print(f"\nQuestion: {question}")
        print(f"Expected: {expected}")
        print(f"Retrieved: {sources}")
        print(f"Top 1: {'PASS' if top1_correct else 'FAIL'}")
        print(f"Top 3: {'PASS' if top3_correct else 'FAIL'}")

    total = len(results)

    summary = {
        "name": name,
        "recall_at_1": (
            sum(item["top1"] for item in results) / total
            if total else 0.0
        ),
        "recall_at_3": (
            sum(item["top3"] for item in results) / total
            if total else 0.0
        ),
    }

    print(f"\nRecall@1: {summary['recall_at_1']:.0%}")
    print(f"Recall@3: {summary['recall_at_3']:.0%}")

    return summary


if __name__ == "__main__":
    keyword = evaluate_retriever(
        "Keyword retrieval",
        retrieve_runbooks,
    )

    semantic = evaluate_retriever(
        "Semantic retrieval",
        retrieve_runbooks_semantic,
    )

    print("\n" + "=" * 60)
    print("FINAL COMPARISON")
    print("=" * 60)

    for metric in ("recall_at_1", "recall_at_3"):
        print(
            f"{metric}: "
            f"keyword={keyword[metric]:.0%}, "
            f"semantic={semantic[metric]:.0%}"
        )
