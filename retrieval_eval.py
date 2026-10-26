
from retrieval import retrieve_runbooks
from semantic_retrieval import retrieve_runbooks_semantic


EVALUATION_CASES = [
    {
        "question": "Investigate an inventory discrepancy and check SKU mapping",
        "expected_source": "inventory_discrepancy.md",
    },
    {
        "question": "What should I do when an API times out or returns HTTP 5xx?",
        "expected_source": "integration_failure.md",
    },
    {
        "question": "Check stock differences and determine which system is authoritative",
        "expected_source": "inventory_discrepancy.md",
    },
    {
        "question": "Investigate invalid JSON and check upstream service health",
        "expected_source": "integration_failure.md",
    },
    {
        "question": "Why do online store and ERP quantities disagree?",
        "expected_source": "inventory_discrepancy.md",
    },
    {
        "question": "How should I investigate a failed connection to an external API?",
        "expected_source": "integration_failure.md",
    },
    {
        "question": "Verify SKU mapping before investigating a stock mismatch",
        "expected_source": "inventory_discrepancy.md",
    },
    {
        "question": "What checks should I perform when an upstream service is unavailable?",
        "expected_source": "integration_failure.md",
    },
    {
        "question": "How do I safely compare inventory across two systems?",
        "expected_source": "inventory_discrepancy.md",
    },
    {
        "question": "How should I troubleshoot malformed API responses?",
        "expected_source": "integration_failure.md",
    },
]


RETRIEVERS = {
    "Keyword": retrieve_runbooks,
    "Semantic": retrieve_runbooks_semantic,
}


def evaluate_retriever(retriever, top_k=3):
    results = []

    for case in EVALUATION_CASES:
        retrieved = retriever(case["question"], top_k=top_k)

        # A question is a hit if its expected runbook appears
        # within the first k retrieved sections.
        sources = [item["source"] for item in retrieved]

        hit_at_1 = (
            bool(sources)
            and sources[0] == case["expected_source"]
        )
        hit_at_3 = case["expected_source"] in sources[:3]

        results.append(
            {
                "question": case["question"],
                "expected": case["expected_source"],
                "retrieved": sources,
                "hit_at_1": hit_at_1,
                "hit_at_3": hit_at_3,
            }
        )

    total = len(results)

    return {
        "total": total,
        "hit_at_1": sum(r["hit_at_1"] for r in results),
        "hit_at_3": sum(r["hit_at_3"] for r in results),
        "results": results,
    }


def print_report(name, report):
    total = report["total"]

    print("\n" + "=" * 60)
    print(f"{name} retrieval evaluation")
    print("=" * 60)

    for result in report["results"]:
        status = "PASS" if result["hit_at_1"] else "MISS"

        print(f"\n[{status}] {result['question']}")
        print(f"  Expected:  {result['expected']}")
        print(f"  Retrieved: {result['retrieved']}")
        print(f"  Hit@1:     {result['hit_at_1']}")
        print(f"  Hit@3:     {result['hit_at_3']}")

    hit_at_1 = report["hit_at_1"]
    hit_at_3 = report["hit_at_3"]

    print("\nSummary")
    print(f"  Hit@1 / Recall@1: {hit_at_1}/{total} ({hit_at_1 / total:.0%})")
    print(f"  Hit@3 / Recall@3: {hit_at_3}/{total} ({hit_at_3 / total:.0%})")


def main():
    for name, retriever in RETRIEVERS.items():
        report = evaluate_retriever(retriever, top_k=3)
        print_report(name, report)


if __name__ == "__main__":
    main()
