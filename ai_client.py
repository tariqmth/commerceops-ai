
import ollama


def ask_ai(question: str) -> str:
    response = ollama.chat(
        model="qwen3:4b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are CommerceOps AI, a retail operations "
                    "assistant. Be concise. Never invent inventory "
                    "facts. Explain when evidence is missing."
                ),
            },
            {"role": "user", "content": question},
        ],
    )

    return response.message.content or ""
