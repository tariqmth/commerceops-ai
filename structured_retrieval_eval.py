
import json
from pathlib import Path

from retrieval import retrieve_runbooks
from semantic_retrieval import retrieve_runbooks_semantic


DATASET_PATH = Path(__file__).resolve().parent / "evaluation_cases.json"

RETRIEVERS = {
    "Keyword": retrieve_runbooks,
    "Semantic": retrieve_runbooks_semantic,
}


def load_retrieval_cases() -> list[dict]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    cases = [
        case
        for case in dataset["cases"]
        if case.get("category") == "retrieval"
    ]

    if not cases:
        raise ValueError("No retrieval evaluation cases were found.")

    for case in cases:
        for field in ("id", "question", "expected_source", "expected_section"):
            if not case.get(field):
                raise ValueError(
                    f"Retrieval case is missing {field}: {case}"
                )

    return cases


def evaluate_retriever(retriever, cases: list[dict], top_k: int = 3) -> dict:
    results = []

    for case in cases:
        retrieved = retriever(case["question"], top_k=top_k)

        expected_source = case["expected_source"]
        expected_section = case["expected_section"]

        def is_expected(item: dict) -> bool:
            return (
                item.get("source") == expected_source
                and item.get("section") == expected_section
            )

        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_source": expected_source,
                "expected_section": expected_section,
                "hit_at_1": bool(retrieved) and is_expected(retrieved[0]),
                "hit_at_3": any(is_expected(item) for item in retrieved[:3]),
                "retrieved": [
                    f"{item.get('source')} :: {item.get('section')}"
                    for item in retrieved[:top_k]
                ],
            }
        )

    total = len(results)

    return {
        "total": total,
        "hit_at_1": sum(item["hit_at_1"] for item in results),
        "hit_at_3": sum(item["hit_at_3"] for item in results),
        "results": results,
    }


def print_report(name: str, report: dict) -> None:
    total = report["total"]

    print(f"\n{'=' * 65}")
    print(f"{name} retrieval")
    print("=" * 65)

    for result in report["results"]:
        status = "PASS" if result["hit_at_3"] else "FAIL"

        print(f"\n[{status}] {result['id']}: {result['question']}")
        print(
            "  Expected: "
            f"{result['expected_source']} :: {result['expected_section']}"
        )
        print(f"  Retrieved: {result['retrieved']}")
        print(f"  Hit@1: {result['hit_at_1']}")
        print(f"  Hit@3: {result['hit_at_3']}")

    print("\nSummary")
    print(
        f"  Hit@1: {report['hit_at_1']}/{total} "
        f"({report['hit_at_1'] / total:.0%})"
    )
    print(
        f"  Hit@3: {report['hit_at_3']}/{total} "
        f"({report['hit_at_3'] / total:.0%})"
    )


def main() -> int:
    cases = load_retrieval_cases()
    all_passed = True

    for name, retriever in RETRIEVERS.items():
        report = evaluate_retriever(retriever, cases, top_k=3)
        print_report(name, report)

        if report["hit_at_3"] != report["total"]:
            all_passed = False

    print("\nOverall:", "PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
