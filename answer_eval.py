
import re

from ai_agent import ask_commerceops


EVALUATION_CASES = [
    {
        "question": (
            "Which SKUs have inventory discrepancies? "
            "Give the online quantity, ERP quantity, and difference."
        ),
        "expected": {
            "SKU-101": {"20", "15", "5"},
            "SKU-103": {"12", "10", "2"},
        },
    },
    {
        "question": (
            "Explain the inventory discrepancy for SKU-101. "
            "State the online quantity, ERP quantity, and difference."
        ),
        "expected": {
            "SKU-101": {"20", "15", "5"},
        },
    },
]


def contains_number(text: str, number: str) -> bool:
    pattern = rf"(?<!\w){re.escape(number)}(?!\w)"
    return re.search(pattern, text) is not None


def check_sku_facts(answer: str, expected: dict) -> list[str]:
    failures = []
    normalized = answer.lower()

    for sku, required_numbers in expected.items():
        sku_lower = sku.lower()
        position = normalized.find(sku_lower)

        if position == -1:
            failures.append(f"{sku}: SKU not mentioned")
            continue

        # Inspect text near the SKU, rather than searching the
        # entire answer for quantities that may belong to another SKU.
        start = max(0, position - 100)
        end = min(len(normalized), position + 180)
        context = normalized[start:end]

        missing = [
            number
            for number in sorted(required_numbers)
            if not contains_number(context, number)
        ]

        if missing:
            failures.append(
                f"{sku}: expected quantities {missing} near the SKU"
            )

    return failures


def evaluate_answers() -> dict:
    results = []

    for case in EVALUATION_CASES:
        print(f"\nQuestion: {case['question']}")

        try:
            answer = ask_commerceops(case["question"])
            failures = check_sku_facts(answer, case["expected"])
            passed = not failures

            print("\nAI answer:")
            print(answer)
            print("\nResult:", "PASS" if passed else "FAIL")

            for failure in failures:
                print("  -", failure)

            results.append(passed)

        except Exception as exc:
            print(f"\nERROR: {type(exc).__name__}: {exc}")
            results.append(False)

    passed_count = sum(results)
    total = len(results)

    print("\n" + "=" * 50)
    print(f"SKU association evaluation: {passed_count}/{total} passed")
    print("=" * 50)

    return {
        "passed": passed_count,
        "total": total,
        "success": passed_count == total,
    }


if __name__ == "__main__":
    evaluate_answers()
