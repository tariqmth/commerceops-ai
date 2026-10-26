
from pathlib import Path
import math
import re
from functools import lru_cache

import ollama


RUNBOOK_DIR = Path(__file__).resolve().parent / "runbooks"
EMBEDDING_MODEL = "nomic-embed-text"

@lru_cache(maxsize=1)
def _get_ollama_client():
    """Reuse one Ollama client per running process."""
    return ollama.Client(timeout=60.0)

def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def _split_sections(content: str) -> list[str]:
    sections = re.split(r"(?m)(?=^##? )", content)

    return [
        section.strip()
        for section in sections
        if section.strip()
    ]


@lru_cache(maxsize=512)
def _embed_text(text: str) -> list[float]:
    """Create and cache an embedding using local Ollama."""

    response = _get_ollama_client().embed(
        model=EMBEDDING_MODEL,
        input=text,
    )

    if not response.embeddings:
        raise RuntimeError("Embedding model returned no embedding.")

    return list(response.embeddings[0])


def _cosine_similarity(
    first: list[float],
    second: list[float],
) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("Embeddings must have matching dimensions.")

    dot_product = sum(a * b for a, b in zip(first, second))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))

    if first_norm == 0 or second_norm == 0:
        return 0.0

    return dot_product / (first_norm * second_norm)


def retrieve_runbooks_semantic(
    question: str,
    top_k: int = 2,
) -> list[dict[str, str | float]]:
    """Retrieve runbook sections by semantic similarity."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer.")

    if not RUNBOOK_DIR.exists():
        raise RuntimeError("Runbook directory does not exist.")

    documents = []

    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")

        for section in _split_sections(content):
            documents.append({
                "source": path.name,
                "section": section.splitlines()[0]
                .lstrip("# ")
                .strip(),
                "content": section,
            })

    if not documents:
        return []

    # Fail clearly if the local embedding service is unavailable.
    query_embedding = _embed_text(question)
    results = []

    for document in documents:
        document_embedding = _embed_text(document["content"])

        score = _cosine_similarity(
            query_embedding,
            document_embedding,
        )

        results.append({
            **document,
            "score": score,
        })

    results.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["source"]),
            str(item["section"]),
        )
    )

    return results[:top_k]
