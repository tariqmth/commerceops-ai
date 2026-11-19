# CommerceOps AI

An AI-assisted retail operations platform prototype that connects
simulated e-commerce and ERP systems, reconciles inventory using
deterministic Python logic, and uses a local large language model to
explain verified results. It also includes operational runbooks,
retrieval-augmented generation (RAG), integration resilience, request
tracing, structured logging, health checks, and in-memory service
metrics.

The project is being developed as a practical portfolio project for AI
engineering and Forward Deployed Engineer (FDE) roles, building on an
experienced PHP/Laravel and e-commerce integration background.

## Project goals

-   Build practical Python, FastAPI and AI engineering skills.
-   Simulate enterprise retail integrations between an online store and
    an ERP.
-   Use deterministic business logic for critical inventory
    calculations.
-   Ground AI explanations in verified tool results and operational
    documentation.
-   Demonstrate safe, read-only AI agent behaviour.
-   Apply automated testing, evaluation, validation, observability and
    integration resilience.
-   Build a credible, demonstrable project relevant to enterprise AI and
    FDE work.

## Architecture

``` text
                         Client
                           |
                           v
                  CommerceOps AI API
                       FastAPI
                       main.py
                           |
          +----------------+------------------+
          |                |                  |
          v                v                  v
   Inventory APIs      AI question API    Operational APIs
   /inventory/...       POST /ai/ask       /health/*
          |                |
          v                v
   Inventory service    AI agent
          |                |
      +---+---+       +----+----------------+
      |       |       |                     |
      v       v       v                     v
 Online     ERP     Ollama              Runbook RAG
 Store      API    qwen3:4b          semantic/hybrid retrieval
 API                  |
      |               v
      +--------> Read-only tools
                       |
                       v
              Verified inventory data
                       |
                       v
              Evidence-based AI answer

 Cross-cutting capabilities:
 - Request ID generation and propagation
 - Structured JSON logging
 - Retry handling for transient integration failures
 - Integration health checks
 - In-memory request and latency metrics
 - Automated tests and evaluation datasets
```

## Technology stack

-   Python 3.14
-   FastAPI and Uvicorn
-   Pydantic
-   HTTPX for service-to-service HTTP requests
-   Ollama with `qwen3:4b` for local language-model inference
-   Ollama with `nomic-embed-text` for semantic embeddings
-   pytest and FastAPI TestClient
-   VS Code on Windows 11

## Completed milestones

### 1. Core inventory domain and API

-   Implemented deterministic comparison of online-store and ERP stock
    quantities.
-   Calculate the difference as online quantity minus ERP quantity.
-   Identify matched and discrepant SKUs.
-   Validate inventory records and reject invalid quantities, including
    negative values and invalid boolean/string inputs.
-   Added inventory endpoints and API-level tests.

### 2. Local AI agent and read-only tool calling

-   Connected the application to a locally running Ollama model.
-   Implemented a read-only inventory discrepancy tool.
-   Require tool evidence for questions about actual inventory
    discrepancies.
-   Ground AI explanations in the returned inventory data rather than
    allowing the model to invent stock figures.
-   Handle missing evidence, unsupported tool requests, unexpected
    multiple tool calls and tool execution failures.
-   Avoid making a second model call after a tool failure.
-   Added agent tests covering expected behaviour and failure cases.

### 3. Mock enterprise integrations

-   Created separate FastAPI services to simulate an online store and an
    ERP.
-   Added health and inventory endpoints to both mock services.
-   Implemented HTTP clients for each service.
-   Added an inventory integration service that fetches both datasets
    and compares them.
-   Connected the main application to these mock services.

### 4. Operational runbooks and RAG

-   Created Markdown runbooks for inventory discrepancies and
    integration failures.
-   Implemented runbook section retrieval.
-   Added keyword-based and semantic retrieval using local embeddings.
-   Added hybrid retrieval to combine semantic relevance with keyword
    and heading matches.
-   Integrated retrieved operational guidance into AI agent responses.
-   Added structured retrieval evaluation cases, including expected
    runbook sections and unsupported questions.
-   Instructed the agent to use only the retrieved evidence and not
    invent runbook citations or links.

### 5. Integration resilience

-   Added a shared HTTP request helper for the online-store and ERP
    clients.
-   Retry transient connection and timeout failures.
-   Retry server-side HTTP 5xx responses.
-   Do not retry client-side HTTP 4xx responses or invalid JSON
    responses.
-   Use a bounded retry count and increasing delays between attempts.
-   Added automated tests for retry success, exhausted retries and
    non-retryable failures.

### 6. Integration health checks

-   Added health-check logic for the online-store and ERP services.
-   Added `GET /health/integrations` to report each dependency as
    healthy or unhealthy.
-   Return an overall healthy or degraded status.
-   Tested both healthy and unavailable dependency scenarios.

### 7. Request ID tracking and propagation

-   Generate a request ID for incoming requests to the main API.
-   Return the ID in the `X-Request-ID` response header.
-   Propagate the same ID from the main API to the online-store and ERP
    services.
-   Generate IDs for direct requests to the mock services when no ID is
    supplied.
-   Include request IDs in service logs to help correlate activity
    across services.

### 8. Structured JSON logging

-   Added a shared JSON logging formatter.
-   Include timestamp, log level, service name, request ID, logger name
    and message.
-   Include relevant request fields such as HTTP method, path, status
    code and duration.
-   Include exception details when an exception is logged.
-   Configure separate service names for the main application and mock
    services.

### 9. Operational metrics

-   Added a thread-safe, in-memory metrics collector.
-   Added `GET /metrics` to expose main-application request metrics.
-   Track total requests, successful requests and error requests.
-   Calculate error rate and average request latency.
-   Track P50, P95 and P99 latency, slowest request and latency sample
    count.
-   Bound the latency sample history to avoid unbounded memory growth.
-   Added automated tests for counts, error rates, averages,
    percentiles, sample limits and empty metrics.

## API endpoints

  ----------------------------------------------------------------------------
  Method                  Endpoint                     Purpose
  ----------------------- ---------------------------- -----------------------
  GET                     `/health`                    Main application health
                                                       check

  GET                     `/health/integrations`       Health status of the
                                                       online-store and ERP
                                                       dependencies

  GET                     `/metrics`                   In-memory request and
                                                       latency metrics

  GET                     `/inventory/discrepancies`   Retrieve inventory
                                                       discrepancies

  GET                     `/inventory/summary`         Retrieve an inventory
                                                       summary

  POST                    `/inventory/compare`         Compare submitted
                                                       inventory data

  POST                    `/ai/ask`                    Ask the AI agent an
                                                       operational question
  ----------------------------------------------------------------------------

Interactive API documentation is available at
`http://127.0.0.1:8000/docs` when the main application is running.

## Sample inventory data

The mock services currently use this sample dataset:

  SKU         Online quantity   ERP quantity   Difference
  --------- ----------------- -------------- ------------
  SKU-101                  20             15           +5
  SKU-102                   8              8            0
  SKU-103                  12             10           +2

The difference is calculated as online quantity minus ERP quantity. In
this sample, SKU-101 and SKU-103 have discrepancies, while SKU-102 is
matched.

## Local setup

### Prerequisites

-   Windows 11
-   Python 3.14
-   Git (recommended)
-   Ollama installed locally
-   The `qwen3:4b` language model
-   The `nomic-embed-text` embedding model for semantic retrieval

Pull the Ollama models if they are not already installed:

``` powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### Create the virtual environment

From the project root in PowerShell:

``` powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Run the three services

Open three separate PowerShell terminals. Activate the virtual
environment in each terminal and run one command in each.

**Terminal 1 --- Main CommerceOps AI API**

``` powershell
uvicorn main:app --reload
```

**Terminal 2 --- Mock online-store API**

``` powershell
uvicorn mock_services.online_store_api:app --port 8001
```

**Terminal 3 --- Mock ERP API**

``` powershell
uvicorn mock_services.erp_api:app --port 8002
```

The main API runs at `http://127.0.0.1:8000`. The mock online-store and
ERP services run on ports `8001` and `8002`.

### Useful URLs

-   Main API documentation: `http://127.0.0.1:8000/docs`
-   Main health: `http://127.0.0.1:8000/health`
-   Integration health: `http://127.0.0.1:8000/health/integrations`
-   Metrics: `http://127.0.0.1:8000/metrics`
-   Inventory discrepancies:
    `http://127.0.0.1:8000/inventory/discrepancies`

## Testing and evaluation

Run the complete automated test suite from the project root:

``` powershell
python -m pytest -v
```

Run a focused test file when working on a particular component:

``` powershell
python -m pytest tests/test_metrics.py -v
```

The project also includes retrieval and answer evaluation scripts for
checking whether relevant runbook sections are retrieved and whether
agent responses follow expected evidence and safety behaviour. Run the
relevant evaluation script from the project root, for example:

``` powershell
python structured_retrieval_eval.py
```

Use the exact evaluation script names present in the current project if
they have changed.

## Current safety boundaries

-   Inventory comparison is performed by deterministic Python code, not
    by the language model.
-   The AI inventory tool is read-only.
-   AI answers about actual inventory must be grounded in tool results.
-   Operational guidance should be grounded in retrieved runbook
    content.
-   The prototype uses simulated services and sample data.
-   It does not make live inventory changes, process payments, issue
    refunds or execute operational actions.
-   Any future write operation must have explicit authorisation,
    validation, appropriate human approval and an audit trail.

## Current limitations

-   The online-store and ERP services are mock services, not live
    production integrations.
-   Metrics are held in memory. They reset when the process restarts and
    are not shared across multiple worker processes.
-   The metrics endpoint currently reports the main application's
    in-memory metrics; the mock services have their own request logs.
-   The current project is a local prototype and has not yet been
    deployed as a production service.
-   Retrieval and agent evaluation datasets are still being expanded.

## Next milestones

The following items are planned and should not be considered completed:

1.  Add audit logging and end-to-end traceability for agent questions,
    tool calls, retrieved evidence and generated responses.
2.  Add stronger deterministic validation of model-generated outputs and
    citation references.
3.  Expand evaluation datasets and improve retrieval and answer quality
    against realistic operational scenarios.
4.  Add human approval workflows for any future proposed write actions.
5.  Expand mock enterprise workflows, including orders and additional
    integration failure scenarios.
6.  Add a frontend or operator-facing demonstration interface.
7.  Containerise the services with Docker.
8.  Prepare deployment and monitoring for an AWS environment.
9.  Document end-to-end demonstrations and practical FDE interview
    scenarios.

## Learning and development approach

The project is built incrementally, with practical explanations and
tests at each milestone. The learning path is designed for an
experienced PHP/Laravel engineer transitioning into Python, AI agents,
RAG and enterprise FDE engineering.

The priority is to preserve working functionality, make each change
testable, and demonstrate engineering practices that matter in real
enterprise environments: reliable integrations, evidence-based AI, safe
failure handling, observability and clear operational documentation.
