
from fastapi.testclient import TestClient
import main


client = TestClient(main.app)


def test_ai_endpoint_returns_answer(monkeypatch):
    def fake_ask(question):
        assert question == "Compare online stock with ERP"
        return "SKU-101 has 5 more units online."

    monkeypatch.setattr(main, "ask_commerceops", fake_ask)

    response = client.post(
        "/ai/ask",
        json={"question": "Compare online stock with ERP"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "answer": "SKU-101 has 5 more units online."
    }


def test_ai_endpoint_handles_inventory_failure(monkeypatch):
    def fake_ask(question):
        raise ValueError("Internal inventory details")

    monkeypatch.setattr(main, "ask_commerceops", fake_ask)

    response = client.post(
        "/ai/ask",
        json={"question": "Compare stock"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Inventory data could not be retrieved safely."
    }
    assert "Internal inventory details" not in response.text


def test_ai_endpoint_rejects_empty_question():
    response = client.post(
        "/ai/ask",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_ai_api_returns_503_when_ollama_is_unavailable(
    monkeypatch
):
    import ollama
    import main
    from fastapi.testclient import TestClient

    def fake_ask_commerceops(question):
        raise ollama.RequestError("Ollama is not running")

    monkeypatch.setattr(
        main, "ask_commerceops", fake_ask_commerceops
    )

    response = client.post(
        "/ai/ask",
        json={"question": "Compare inventory"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The AI service is unavailable. Please try again."
    )


def test_ai_api_returns_502_when_ollama_returns_an_error(
   monkeypatch
):
    import ollama
    import main
    from fastapi.testclient import TestClient


    def fake_ask_commerceops(question):
        raise ollama.ResponseError(
            "Model failed", status_code=500
        )

    monkeypatch.setattr(
        main, "ask_commerceops", fake_ask_commerceops
    )

    response = client.post(
        "/ai/ask",
        json={"question": "Compare inventory"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The AI "
        "service returned an error."
    )


def test_ai_endpoint_does_not_expose_runtime_error_details(monkeypatch):
    def fake_ask(question):
        raise RuntimeError(
            "Sensitive internal detail: http://internal-erp:8002"
        )

    monkeypatch.setattr(main, "ask_commerceops", fake_ask)

    response = client.post(
        "/ai/ask",
        json={"question": "Compare stock"},
    )

    assert response.status_code == 502
    assert "internal-erp" not in response.text
    assert "Sensitive internal detail" not in response.text


def test_ai_endpoint_returns_504_when_request_times_out(monkeypatch):
    import httpx

    def fake_ask(question):
        raise httpx.TimeoutException("Internal timeout details")

    monkeypatch.setattr(main, "ask_commerceops", fake_ask)

    response = client.post(
        "/ai/ask",
        json={"question": "Compare stock"},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == (
        "The AI request timed out. Please try again."
    )
    assert "Internal timeout details" not in response.text
