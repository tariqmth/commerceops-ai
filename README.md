# CommerceOps AI

An AI-assisted retail operations platform prototype that connects simulated e-commerce and ERP systems, reconciles inventory using deterministic Python logic, and uses a local large language model to explain verified results.

The platform demonstrates enterprise AI engineering practices, including tool-calling agents, retrieval-augmented generation (RAG), integration resilience, request tracing, structured logging, operational metrics, audit logging, human approval workflows, controlled inventory execution, and safe recovery after partial failures.

This project is being developed as a practical portfolio project for AI Engineering and Forward Deployed Engineer (FDE) roles, building on an experienced PHP/Laravel, e-commerce, ERP and integration engineering background.

## Project goals

- Build practical Python, FastAPI and AI engineering skills.
- Simulate enterprise retail integrations between an online store and an ERP.
- Use deterministic business logic for critical inventory calculations.
- Ground AI explanations in verified tool results and operational documentation.
- Demonstrate safe AI agent behaviour and evidence-based responses.
- Implement reliable enterprise integration patterns.
- Demonstrate human approval and controlled execution of operational actions.
- Handle partial failures, retries, reconciliation and recovery safely.
- Apply automated testing, evaluation, validation and observability.
- Build a credible, demonstrable project relevant to enterprise AI and FDE work.

## Architecture

```text
                         Client
                           |
                           v
                  CommerceOps AI API
                       FastAPI
                       main.py
                           |
          +----------------+-------------------+
          |                |                   |
          v                v                   v
    Inventory APIs     AI question API    Operational APIs
    /inventory/...      POST /ai/ask       /health/*
          |                |
          v                v
    Inventory service   AI agent
          |                |
      +---+---+        +---+----------------+
      |       |        |                    |
      v       v        v                    v
   Online    ERP     Ollama             Runbook RAG
   Store     API    qwen3:4b          Semantic/hybrid
   API                 |               retrieval
      |                v
      |          Read-only AI tools
      |                |
      +----------------+
                       |
                       v
              Verified inventory data
                       |
                       v
              Evidence-based AI answer


       Human Approval and Controlled Execution
                       |
             Approval service
                       |
              Role permissions
                       |
             Approved proposal
                       |
              Execution service
                       |
             +---------+---------+
             |                   |
             v                   v
         Online Store           ERP
             |                   |
             +---------+---------+
                       |
               Final verification
                       |
                Safe recovery


Cross-cutting capabilities:
- Request ID generation and propagation
- Structured JSON logging
- Integration retry handling
- Integration health checks
- In-memory operational metrics
- Append-only audit event logging
- Automated tests and evaluation datasets
- Approval and execution state tracking
- Partial-failure reconciliation and recovery
```

## Technology stack

- Python 3.14
- FastAPI and Uvicorn
- Pydantic
- HTTPX for service-to-service HTTP requests
- Ollama with `qwen3:4b` for local language-model inference
- Ollama with `nomic-embed-text` for semantic embeddings
- pytest and FastAPI TestClient
- Thread-safe Python services and locking
- JSON and JSONL structured records
- VS Code on Windows 11

## Completed milestones

### 1. Core inventory domain and API

- Implemented deterministic comparison of online-store and ERP stock quantities.
- Calculate the difference as online quantity minus ERP quantity.
- Identify matched and discrepant SKUs.
- Validate inventory records and reject invalid quantities, including negative values and invalid boolean/string inputs.
- Added inventory endpoints and API-level tests.

### 2. Local AI agent and read-only tool calling

- Connected the application to a locally running Ollama model.
- Implemented a read-only inventory discrepancy tool.
- Require tool evidence for questions about actual inventory discrepancies.
- Ground AI explanations in returned inventory data rather than allowing the model to invent stock figures.
- Handle missing evidence, unsupported tool requests, unexpected multiple tool calls and tool execution failures.
- Avoid making a second model call after a tool failure.
- Added agent tests covering expected behaviour and failure cases.

### 3. Mock enterprise integrations

- Created separate FastAPI services to simulate an online store and an ERP.
- Added health and inventory endpoints to both mock services.
- Implemented HTTP clients for each service.
- Added an inventory integration service that fetches both datasets and compares them.
- Added controlled inventory update endpoints to the mock services.
- Connected the main application to these mock services.

### 4. Operational runbooks and RAG

- Created Markdown runbooks for inventory discrepancies and integration failures.
- Implemented runbook section retrieval.
- Added keyword-based and semantic retrieval using local embeddings.
- Added hybrid retrieval to combine semantic relevance with keyword and heading matches.
- Integrated retrieved operational guidance into AI agent responses.
- Added structured retrieval evaluation cases, including expected runbook sections and unsupported questions.
- Instructed the agent to use retrieved evidence and not invent runbook citations or links.

### 5. Integration resilience

- Added a shared HTTP request helper for the online-store and ERP clients.
- Retry transient connection and timeout failures.
- Retry server-side HTTP 5xx responses.
- Do not retry client-side HTTP 4xx responses or invalid JSON responses.
- Use a bounded retry count and increasing delays between attempts.
- Added automated tests for retry success, exhausted retries and non-retryable failures.

### 6. Integration health checks

- Added health-check logic for the online-store and ERP services.
- Added `GET /health/integrations` to report each dependency as healthy or unhealthy.
- Return an overall healthy or degraded status.
- Tested healthy and unavailable dependency scenarios.

### 7. Request ID tracking and propagation

- Generate a request ID for incoming requests to the main API.
- Return the ID in the `X-Request-ID` response header.
- Propagate the same ID from the main API to the online-store and ERP services.
- Generate IDs for direct requests to mock services when no ID is supplied.
- Include request IDs in service logs to help correlate activity across services.

### 8. Structured JSON logging

- Added a shared JSON logging formatter.
- Include timestamp, log level, service name, request ID, logger name and message.
- Include relevant request fields such as HTTP method, path, status code and duration.
- Include exception details when an exception is logged.
- Configure separate service names for the main application and mock services.

### 9. Operational metrics

- Added a thread-safe, in-memory metrics collector.
- Added `GET /metrics` to expose main-application request metrics.
- Track total requests, successful requests and error requests.
- Calculate error rate and average request latency.
- Track P50, P95 and P99 latency, slowest request and latency sample count.
- Bound the latency sample history to avoid unbounded memory growth.
- Added automated tests for counts, error rates, averages, percentiles, sample limits and empty metrics.

### 10. Audit logging and traceability

- Implemented append-only JSONL audit event logging.
- Record UTC timestamps, request IDs, event types, service names and event details.
- Added thread-safe audit file writing.
- Create the audit log directory when required.
- Raise audit errors rather than silently ignoring failures during critical operations.
- Added audit events for AI requests, runbook retrieval, tool execution, successful responses and failures.
- Added audit logging for approval and inventory execution workflows.
- Tested audit event creation, appending, write failures and rollback behaviour.

### 11. Human approval and action safety

- Implemented an approval service for proposed operational actions.
- Added support for inventory adjustments, order cancellations and refunds as approval action types.
- Added approval creation, retrieval, approval and rejection.
- Enforced pending-only approval decisions.
- Implemented role-based approval permissions.
- Added warehouse manager, operations manager, finance manager and admin permission definitions.
- Prevented unauthorised roles from approving restricted action types.
- Added deep-copy protection for approval records.
- Added audit logging for approval decisions.
- Added API endpoints for creating, retrieving and deciding approvals.
- Tested approval validation, permissions, concurrency, duplicate decisions and audit failures.

### 12. Expanded enterprise workflows: controlled execution and safe recovery

**Approved inventory execution**

- Implemented a separate execution service for approved inventory adjustments.
- Require an approved inventory adjustment before execution.
- Validate the approved proposal, SKU, physical count, target quantity, count reference and reason.
- Use explicit physical-count-backed target quantities rather than assuming either system has the correct stock.
- Verify that both systems still contain their expected original quantities before execution.
- Update the online store and ERP independently.
- Verify final quantities by fetching both systems again.
- Prevent duplicate execution for the same approval.
- Record execution status, updated services, failures and observed quantities.
- Distinguish completed, failed, partial-failure, verification-failed, reconciled and audit-failure outcomes.

**Safe recovery after partial failure**

- Implemented `recover_partial_inventory_execution()`.
- Allow recovery only for executions marked `partial_failure`.
- Re-check the original approved proposal before recovery.
- Fetch actual quantities from both systems before making changes.
- Permit only the approved original quantity or approved target quantity.
- Stop recovery if either system contains an unexpected quantity.
- Update only the system that still requires the approved adjustment.
- Avoid repeating updates already confirmed by remote state.
- Handle successful remote updates whose HTTP responses were lost.
- Fetch both systems again and verify the final target quantities.
- Record recovery start, completion and failure audit events.
- Track recovery attempts and observed quantities.
- Prevent concurrent recovery attempts for the same approval.

**Testing progress**

The latest reported full-suite result before the most recent concurrency test was 149 passed. The focused execution-service suite subsequently reported 150 passed, including the concurrency test. The full suite should be rerun to refresh its total.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Main application health check |
| GET | `/health/integrations` | Health status of online-store and ERP dependencies |
| GET | `/metrics` | In-memory request and latency metrics |
| GET | `/inventory/discrepancies` | Retrieve inventory discrepancies |
| GET | `/inventory/summary` | Retrieve an inventory summary |
| POST | `/inventory/compare` | Compare submitted inventory data |
| POST | `/ai/ask` | Ask the AI agent an operational question |
| POST | `/approvals` | Create an approval request |
| GET | `/approvals/{approval_id}` | Retrieve an approval |
| POST | `/approvals/{approval_id}/decision` | Approve or reject a proposal |

The project also contains execution and recovery service functionality. Recovery API exposure and its API-level tests remain planned work.

Interactive API documentation is available at:

`http://127.0.0.1:8000/docs`

## Sample inventory data

The mock services currently use this sample dataset:

| SKU | Product | Online quantity | ERP quantity | Difference |
|---|---|---:|---:|---:|
| SKU-101 | Wireless Mouse | 20 | 15 | +5 |
| SKU-102 | Mechanical Keyboard | 8 | 8 | 0 |
| SKU-103 | USB-C Hub | 12 | 10 | +2 |

The difference is calculated as online quantity minus ERP quantity.

In this sample, SKU-101 and SKU-103 have discrepancies, while SKU-102 is matched.

## Inventory execution safety example

The project uses an explicit physical count as the source of truth for an inventory adjustment.

Example approved proposal:

```python
{
    "sku": "SKU-101",
    "target_quantity": 18,
    "physical_count": 18,
    "count_reference": "COUNT-2026-001",
    "reason": "Physical stock reconciliation",
    "expected_online_quantity": 20,
    "expected_erp_quantity": 15,
}
```

The execution workflow:

1. Detect the inventory discrepancy.
2. Record the physical count and supporting reference.
3. Request human approval.
4. Verify approval status and action type.
5. Check that current quantities still match the approved original quantities.
6. Update both systems.
7. Fetch both systems again and verify the target quantity.
8. Record audit events.
9. Reconcile actual remote state after failures.
10. Recover only when actual quantities remain within the approved original/target values.

The system does not assume that the online store or ERP is automatically correct.

## Local setup

### Prerequisites

- Windows 11
- Python 3.14
- Git (recommended)
- Ollama installed locally
- The `qwen3:4b` language model
- The `nomic-embed-text` embedding model for semantic retrieval

Pull the Ollama models if they are not already installed:

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### Create the virtual environment

From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Run the three services

Open three separate PowerShell terminals. Activate the virtual environment in each terminal and run one command in each.

**Terminal 1 — Main CommerceOps AI API**

```powershell
uvicorn main:app --reload
```

**Terminal 2 — Mock online-store API**

```powershell
uvicorn mock_services.online_store_api:app --port 8001
```

**Terminal 3 — Mock ERP API**

```powershell
uvicorn mock_services.erp_api:app --port 8002
```

The main API runs at `http://127.0.0.1:8000`.

The mock online-store and ERP services run on ports `8001` and `8002`.

### Useful URLs

- Main API documentation: `http://127.0.0.1:8000/docs`
- Main health: `http://127.0.0.1:8000/health`
- Integration health: `http://127.0.0.1:8000/health/integrations`
- Metrics: `http://127.0.0.1:8000/metrics`
- Inventory discrepancies: `http://127.0.0.1:8000/inventory/discrepancies`

## Testing and evaluation

Run the complete automated test suite from the project root:

```powershell
python -m pytest -q
```

For detailed test output:

```powershell
python -m pytest -v
```

Run a focused test file when working on a particular component:

```powershell
python -m pytest tests/test_execution_service.py -q
```

The project also includes retrieval and answer evaluation scripts for checking whether relevant runbook sections are retrieved and whether agent responses follow expected evidence and safety behaviour.

For example:

```powershell
python structured_retrieval_eval.py
```

Use the exact evaluation script names present in the current project if they have changed.

## Current safety boundaries and limitations

- Inventory comparison is performed by deterministic Python code, not by the language model.
- The AI inventory tool is read-only.
- AI answers about actual inventory must be grounded in tool results.
- Operational guidance should be grounded in retrieved runbook content.
- Inventory write operations are restricted to the separate approved execution workflow.
- A physical count and supporting reference are required in the approved inventory adjustment proposal.
- Approval and execution are separate states.
- Recovery does not automatically overwrite unexpected stock quantities.
- The prototype uses simulated services and sample data, not live enterprise systems.
- Approval and execution records are currently stored in memory and reset when the application restarts.
- Audit events are stored locally in JSONL files; production deployments need durable storage, retention policies and access controls.
- Role and actor information is currently supplied by the caller. Production use requires authenticated identities and server-side authorisation.
- The current implementation does not provide a distributed transaction across the online store and ERP.
- Metrics are held in memory and are not shared across multiple worker processes.
- The project has not yet been containerised or deployed as a production service.
- Evaluation datasets and retrieval quality are still being expanded.

## Remaining milestones and roadmap

The following items are planned and should not be considered completed.

### 13. Recovery API integration and operational visibility

- Add a FastAPI endpoint for initiating recovery.
- Add an endpoint for retrieving execution and recovery status.
- Define appropriate HTTP response codes for blocked, failed, recovered and invalid requests.
- Add API-level tests for recovery.
- Expose useful execution and recovery information to operators.
- Improve operational visibility into partial failures and reconciliation.

### 14. Frontend demonstration

- Build an operator-facing dashboard.
- Display inventory discrepancies and integration health.
- Display AI-generated explanations with supporting evidence.
- Show approval requests and decisions.
- Show execution history, partial failures and recovery status.
- Provide a clear demonstration of the end-to-end retail operations workflow.

### 15. Docker and deployment preparation

- Create Dockerfiles for the main API and mock services.
- Add Docker Compose for local multi-service development.
- Configure environment variables and service configuration.
- Add production-oriented logging and health checks.
- Prepare deployment architecture for AWS.

### 16. AWS deployment and production architecture

- Deploy the application and supporting services in an AWS environment.
- Evaluate managed storage for approvals, executions and audit records.
- Introduce durable state and appropriate database transactions.
- Implement authenticated users and server-side role-based access control.
- Add monitoring, alerting, secrets management and deployment automation.
- Evaluate distributed workflow and reconciliation patterns.

### 17. AI quality, security and evaluation improvements

- Expand retrieval and answer evaluation datasets.
- Improve retrieval quality against realistic operational scenarios.
- Add deterministic validation of model-generated outputs and citation references.
- Test prompt injection and untrusted document handling.
- Add broader integration failure and recovery scenarios.
- Measure response quality, latency and reliability.

### 18. Portfolio and FDE interview preparation

- Document the architecture and key engineering decisions.
- Create end-to-end demonstration scenarios.
- Record short project demonstrations.
- Document failure-handling and recovery examples.
- Prepare technical explanations of RAG, tool calling, enterprise integrations, approval workflows and observability.
- Prepare practical FDE case studies and interview discussions.

## Learning and development approach

The project is built incrementally, with practical explanations and automated tests at each milestone.

The learning path is designed for an experienced PHP/Laravel engineer transitioning into Python, AI agents, RAG and enterprise FDE engineering.

The priority is to preserve working functionality, make each change testable, and demonstrate engineering practices that matter in real enterprise environments:

- Reliable integrations.
- Deterministic business logic.
- Evidence-based AI.
- Human oversight of operational actions.
- Safe failure handling and recovery.
- Auditability and traceability.
- Operational observability.
- Clear technical documentation.

The long-term goal is to turn CommerceOps AI into a demonstrable enterprise-style AI operations platform and a strong practical portfolio project for Forward Deployed Engineer and AI Engineer opportunities.