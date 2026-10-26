
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ai_agent


@pytest.fixture(autouse=True)
def mock_semantic_retrieval(monkeypatch):
    monkeypatch.setattr(
        ai_agent,
        "retrieve_runbooks_semantic",
        lambda question, top_k=3: [],
    )


def make_response(content="", tool_calls=None):
    """Build a fake Ollama response for testing."""
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
    )
    return SimpleNamespace(message=message)


def make_tool_call(name="get_inventory_discrepancies"):
    """Build a fake tool request from the model."""
    return SimpleNamespace(
        function=SimpleNamespace(name=name)
    )


def test_agent_executes_inventory_tool(monkeypatch):
    # Arrange: pretend the model requests our inventory tool.
    first_response = make_response(
        tool_calls=[make_tool_call()]
    )
    final_response = make_response(
        content="SKU-101 has 5 more units online than in ERP."
    )

    mock_chat = Mock(
        side_effect=[first_response, final_response]
    )

    mock_client = Mock()
    mock_client.chat.side_effect = [
        first_response,
        final_response,
    ]

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        Mock(return_value=mock_client),
    )

    mock_tool = Mock(
        return_value={
            "total_skus": 3,
            "discrepancy_count": 1,
            "discrepancies": [
                {"sku": "SKU-101", "difference": 5}
            ],
        }
    )
    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        mock_tool,
    )

    # Act: ask the agent a question.
    answer = ai_agent.ask_commerceops(
        "Explain the stock differences."
    )

    assert mock_client.chat.call_count == 2
    assert mock_client.chat.call_args_list[1].args == ()

    # Assert: the tool ran and the final answer was returned.
    mock_tool.assert_called_once_with()
    assert "SKU-101" in answer


def test_agent_does_not_answer_without_tool_evidence(monkeypatch):
    # Arrange: the model answers without requesting a tool.
    first_response = make_response(
        content="The stock difference is probably 5 units."
    )

    mock_client = Mock()
    mock_client.chat.return_value = first_response

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        Mock(return_value=mock_client),
    )


    mock_tool = Mock()
    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        mock_tool,
    )

    # Act and assert: the agent should refuse to answer
    # an inventory question without calling the tool.
    with pytest.raises(RuntimeError, match="inventory tool"):
        ai_agent.ask_commerceops(
            "Explain the actual stock differences."
        )

    mock_tool.assert_not_called()
    mock_client.chat.assert_called_once()


def test_agent_stops_if_inventory_tool_fails(monkeypatch):
    # Arrange: the model requests the inventory tool.
    first_response = make_response(
        tool_calls=[make_tool_call()]
    )

    mock_client = Mock()
    mock_client.chat.return_value = first_response
    mock_client_factory = Mock(return_value=mock_client)

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        mock_client_factory,
    )


    # Simulate the inventory service failing.
    mock_tool = Mock(
        side_effect=ValueError("Inventory data is invalid")
    )
    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        mock_tool,
    )

    # Act and assert: the error must stop the agent.
    with pytest.raises(
        ValueError,
        match="Inventory data is invalid",
    ):
        ai_agent.ask_commerceops(
            "Explain the actual stock differences."
        )

    mock_tool.assert_called_once_with()

    # The model should not be asked to explain missing evidence.
    
    assert mock_client.chat.call_count == 1


def test_agent_does_not_make_second_ai_call_after_tool_failure(monkeypatch):
    first_response = make_response(
        tool_calls=[make_tool_call()]
    )

    mock_client = Mock()
    mock_client.chat.return_value = first_response
    mock_client_factory = Mock(return_value=mock_client)

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        mock_client_factory,
    )

    mock_tool = Mock(
        side_effect=ValueError("Inventory data is invalid")
    )
    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        mock_tool,
    )

    with pytest.raises(ValueError, match="Inventory data is invalid"):
        ai_agent.ask_commerceops(
            "Explain the actual stock differences."
        )

    assert mock_client.chat.call_count == 1
    mock_tool.assert_called_once_with()

    
def test_agent_rejects_multiple_tool_calls(monkeypatch):
    first_response = make_response(
        tool_calls=[
            make_tool_call(),
            make_tool_call(),
        ]
    )

    mock_client = Mock()
    mock_client.chat.return_value = first_response

    monkeypatch.setattr(
        ai_agent.ollama,
        "Client",
        Mock(return_value=mock_client),
    )

    mock_tool = Mock()
    monkeypatch.setattr(
        ai_agent,
        "get_inventory_discrepancies",
        mock_tool,
    )

    with pytest.raises(
        RuntimeError,
        match="exactly one inventory tool call",
    ):
        ai_agent.ask_commerceops(
            "Explain the actual stock differences."
        )

    mock_tool.assert_not_called()
    assert mock_client.chat.call_count == 1
