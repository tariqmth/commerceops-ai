
import json

import ai_agent


def message_value(message, key, default=None):
    if isinstance(message, dict):
        return message.get(key, default)
    return getattr(message, key, default)


class FakeMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeFunction:
    def __init__(self, name, arguments=None):
        self.name = name
        self.arguments = arguments or {}


class FakeToolCall:
    def __init__(self):
        self.function = FakeFunction(
            "get_inventory_discrepancies"
        )


class FakeResponse:
    def __init__(self, message):
        self.message = message


class FakeOllamaClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def run_agent_with_mocks(monkeypatch, runbooks):
    client = FakeOllamaClient([
        FakeResponse(FakeMessage(
            tool_calls=[FakeToolCall()]
        )),
        FakeResponse(FakeMessage(
            content=(
                "SKU-101 has a difference of 5 units. "
                "Check the inventory discrepancy runbook."
            )
        )),
    ])

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        lambda **kwargs: client,
    )

    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        lambda: {
            "total_skus": 3,
            "discrepancy_count": 1,
            "discrepancies": [
                {
                    "sku": "SKU-101",
                    "difference": 5,
                    "status": "discrepancy",
                }
            ],
        },
    )

    monkeypatch.setattr(
        ai_agent,
        "retrieve_runbooks_semantic",
        lambda question, top_k=3: runbooks,
    )

    answer = ai_agent.ask_commerceops(
        "Why is online stock different from ERP?"
    )

    return answer, client


def test_agent_includes_retrieved_runbook_evidence(monkeypatch):
    runbooks = [
        {
            "source": "inventory_discrepancy.md",
            "section": "Common causes",
            "score": 3,
            "content": (
                "## Common causes\n"
                "A delayed synchronisation job may cause "
                "inventory differences."
            ),
        }
    ]

    answer, client = run_agent_with_mocks(
        monkeypatch,
        runbooks,
    )

    assert "SKU-101" in answer

    first_messages = client.calls[0]["messages"]
    combined = "\n".join(
        message_value(message, "content", "")
        for message in first_messages
    )

    assert "inventory_discrepancy.md" in combined
    assert "delayed synchronisation job" in combined


def test_agent_handles_no_retrieved_runbooks(monkeypatch):
    answer, client = run_agent_with_mocks(
        monkeypatch,
        [],
    )

    assert answer
    combined = "\n".join(
        message_value(message, "content", "")
        for message in client.calls[0]["messages"]
    )

    assert "No relevant runbook sections were found" in combined


def test_agent_still_supplies_inventory_tool_result(monkeypatch):
    _, client = run_agent_with_mocks(
        monkeypatch,
        [],
    )

    final_messages = client.calls[1]["messages"]

    tool_messages = [
        message
        for message in final_messages
        if message_value(message, "role") == "tool"
    ]

    assert tool_messages

    tool_result = json.loads(message_value(tool_messages[0], "content"))

    assert tool_result["discrepancy_count"] == 1
    assert tool_result["discrepancies"][0]["sku"] == "SKU-101"
