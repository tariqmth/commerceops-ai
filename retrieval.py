
from pathlib import Path
import re


RUNBOOK_DIR = Path(__file__).resolve().parent / "runbooks"

STOP_WORDS = {
    "a", "an", "are", "can", "do", "does", "for", "how",
    "i", "in", "is", "it", "of", "on", "should", "the",
    "to", "was", "we", "what", "when", "where", "which",
    "with", "would",
}

# Small, explicit normalisation rules.
# This is not a full linguistic stemmer.
WORD_NORMALISATIONS = {
    "retried": "retry",
    "retrying": "retry",
    "retries": "retry",
    "checks": "check",
    "checking": "check",
    "checked": "check",
    "failures": "failure",
    "failing": "fail",
    "failed": "fail",
    "differences": "difference",
    "discrepancies": "discrepancy",
    "investigating": "investigate",
    "investigation": "investigate",
    "investigations": "investigate",
    "quantities": "quantity",
    "services": "service",
    "systems": "system",
    "requests": "request",
    "logs": "log",
}


def tokenize(text: str) -> set[str]:
    """Convert text into a set of normalised lowercase words."""
    words = re.findall(r"\b[a-z0-9]+\b", text.lower())

    return {
        WORD_NORMALISATIONS.get(word, word)
        for word in words
        if word not in STOP_WORDS
    }


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

    question_words = tokenize(question)
    results = []

    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")

        # Only ## headings start searchable sections.
        # The document's # title is metadata, not its own chunk.
        sections = re.split(r"(?m)(?=^## )", content)

        for section in sections:
            section = section.strip()

            if not section.startswith("## "):
                continue

            lines = section.splitlines()
            heading = lines[0][3:].strip()
            body = "\n".join(lines[1:])

            heading_words = tokenize(heading)
            body_words = tokenize(body)

            heading_matches = question_words & heading_words
            body_matches = question_words & body_words

            # A heading match is worth more than a body match.
            score = (3 * len(heading_matches)) + len(body_matches)

            if score > 0:
                results.append(
                    {
                        "source": path.name,
                        "section": heading,
                        "score": score,
                        "content": section,
                    }
                )

    # Higher score first, then stronger heading overlap.
    # Filename and section provide deterministic tie-breaking.
    results.sort(
        key=lambda item: (
            -int(item["score"]),
            -len(question_words & tokenize(str(item["section"]))),
            str(item["source"]),
            str(item["section"]),
        )
    )

    return results[:top_k]
