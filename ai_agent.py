
import json
import logging
from pyexpat.errors import messages
import ollama
import httpx
from ai_tools import get_inventory_discrepancies
logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory_discrepancies",
            "description": (
                "Read the online store and ERP inventory comparison. "
                "Use this when asked about stock discrepancies."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]


def ask_commerceops(question: str) -> str:
    logger.info("Starting CommerceOps AI request")
    messages = [
        {
            "role": "system",
            "content": (
                "You are CommerceOps AI, a retail operations assistant. "
                "Use the inventory tool for questions about actual stock "
                "discrepancies. Base factual claims on tool results. "
                "Never invent inventory figures. The tool is read-only."
            ),
        },
        {"role": "user", "content": question},
    ]

    client = ollama.Client(timeout=60.0)
    
    response = client.chat(
        model="qwen3:4b",
        messages=messages,
        tools=TOOLS,
    )

    logger.info("Initial AI response received")

    # Inventory questions require actual inventory evidence.
    tool_calls = response.message.tool_calls or []

    if not tool_calls:
        logger.warning(
            "AI did not request the inventory tool; refusing to answer"
        )
        raise RuntimeError(
            "The model did not request the inventory tool. "
            "Cannot answer without inventory evidence."
        )

    if len(tool_calls) != 1:
        logger.warning(
            "AI returned an unexpected number of tool calls: %s",
            len(tool_calls),
        )
        raise RuntimeError(
            "Expected exactly one inventory tool call."
        )


    # Execute recognised tool requests.
    for tool_call in tool_calls:
        if tool_call.function.name != "get_inventory_discrepancies":
            logger.warning("AI did not request the inventory tool; refusing to answer")
            raise RuntimeError(
                f"Unsupported tool requested: "
                f"{tool_call.function.name}"
            )

        result = get_inventory_discrepancies()

        logger.info("Executing inventory discrepancy tool")

        messages.append(response.message)
        messages.append(
            {
                "role": "tool",
                "name": "get_inventory_discrepancies",
                "content": json.dumps(result),
            }
        )

    # Ask the model to explain the returned evidence.
    final_response = client.chat(
        model="qwen3:4b",
        messages=messages,
    )

    logger.info("CommerceOps AI request completed")

    return final_response.message.content or ""


if __name__ == "__main__":
    question = (
        "Compare the online store and ERP stock. "
        "Explain every discrepancy and the quantity difference."
    )
    print(ask_commerceops(question))
