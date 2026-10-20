# CommerceOps AI

An AI-assisted retail operations project that compares online-store and ERP inventory, identifies discrepancies using deterministic Python logic, and uses a local large language model to explain the results using read-only tools.

## Project goals

- Build practical Python and FastAPI skills using an existing PHP/Laravel engineering background.
- Simulate common retail integration problems across e-commerce and ERP systems.
- Use AI to explain verified operational data rather than inventing facts.
- Apply automated testing, input validation, logging, and safe error handling.
- Develop a portfolio project relevant to AI engineering and Forward Deployed Engineer (FDE) roles.

## Current architecture

```text
Client
  |
  v
FastAPI application (main.py)
  |
  +---- Inventory endpoints
  |       |
  |       v
  |    inventory.py
  |    Deterministic stock comparison
  |
  +---- POST /ai/ask
          |
          v
       ai_agent.py
          |
          v
       Ollama / qwen3:4b
          |
          | Requests read-only inventory tool
          v
       ai_tools.py
          |
          v
       Inventory comparison results
          |
          v
       AI explanation based on tool evidence
```

## Technology stack

- Python 3.14
- FastAPI
- Pydantic
- Ollama with `qwen3:4b`
- pytest
- VS Code on Windows 11

## Implemented functionality

### Inventory comparison

- Compare online-store and ERP stock quantities.
- Identify discrepancies and SKUs missing from a system.
- Calculate the difference as online quantity minus ERP quantity.
- Validate SKU records and reject invalid quantities.

### HTTP API

- `GET /health` — health check.
- `GET /inventory/discrepancies` — report stock discrepancies.
- `GET /inventory/summary` — inventory summary.
- `POST /inventory/compare` — compare submitted inventory data.
- `POST /ai/ask` — request an AI-generated explanation.

### AI agent

- Connect to a locally running Ollama model.
- Request inventory evidence through a read-only tool.
- Pass the tool results back to the model for explanation.
- Refuse to answer when the expected tool evidence is missing.
- Reject unsupported tool requests and unexpected multiple tool calls.
- Avoid requesting a second AI response when tool execution fails.

### Reliability and testing

- Automated tests for inventory calculations and API endpoints.
- Validation tests for negative, string and boolean quantities.
- AI agent tests for tool execution and failure scenarios.
- HTTP error mapping for AI service failures.
- Logging for important agent and API events.

## Sample inventory results

| SKU | Online | ERP | Difference |
|---|---:|---:|---:|
| SKU-101 | 20 | 15 | +5 |
| SKU-102 | 8 | 8 | 0 |
| SKU-103 | 12 | 10 | +2 |

The sample dataset contains three SKUs and two inventory discrepancies.

## Local setup

Create and activate a virtual environment in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Ensure Ollama is installed and the `qwen3:4b` model is available locally.

Run the API:

```powershell
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API.

Run automated tests:

```powershell
python -m pytest -v
```

## Planned roadmap

1. Finish agent tool-call validation and reliability tests.
2. Add stronger validation for model-generated tool arguments and responses.
3. Build mock e-commerce and ERP HTTP integrations.
4. Add order and inventory workflows.
5. Add retrieval-augmented generation (RAG) for operational runbooks.
6. Introduce human approval and an audit trail for proposed actions.
7. Improve testing, evaluation, logging and observability.
8. Containerise the application with Docker and prepare an AWS deployment.
9. Create a portfolio demo, architecture documentation and FDE interview examples.

## Safety boundaries

The current project uses simulated inventory data and read-only tools. It does not make live inventory changes, process payments, or issue refunds. Any future operational changes should require explicit authorisation, validation and audit logging.

## Learning approach

This project is developed incrementally, with explanations aimed at an experienced PHP/Laravel engineer transitioning into Python, AI agents and enterprise FDE work.
