
from pathlib import Path
import re


RUNBOOK_DIR = Path(__file__).resolve().parent / "runbooks"
STOP_WORDS = {"a", "an", "do", "how", "i", "the"}


def tokenize(text: str) -> set[str]:
    """Convert text into a set of lowercase words."""
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def retrieve_runbooks(
    question: str,
    top_k: int = 2,
) -> list[dict[str, str | int]]:
    """Return the most relevant runbook sections for a question."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer.")

    if not RUNBOOK_DIR.exists():
        raise RuntimeError("Runbook directory does not exist.")

    question_words = tokenize(question) - STOP_WORDS
    results = []

    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")

        # Split each document into sections using Markdown headings.
        sections = re.split(r"(?m)(?=^##? )", content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_words = tokenize(section)
            score = len(question_words & section_words)

            if score > 0:
                results.append(
                    {
                        "source": path.name,
                        "section": section.splitlines()[0].lstrip("# ").strip(),
                        "score": score,
                        "content": section,
                    }
                )

    # Higher keyword overlap first; deterministic tie-breaking.
    results.sort(
        key=lambda item: (
            -int(item["score"]),
            -len(
                question_words
                & tokenize(str(item["section"]))
            ),
            str(item["source"]),
            str(item["section"]),
        )
    )

    return results[:top_k]
