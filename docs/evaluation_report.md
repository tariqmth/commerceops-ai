# CommerceOps AI — Evaluation Report

**Project:** CommerceOps AI

**Evaluation stage:** Prototype / development
**Date:** 27 October 2026

## 1. Project overview

CommerceOps AI is a retail operations assistant that compares inventory between a mock online store and a mock ERP system. It uses a local Ollama language model and retrieves operational runbooks to support troubleshooting answers.

## 2. Evaluation results

| Evaluation area | Result | Scope |
|---|---|---|
| Keyword retrieval | 100% Recall@1 and Recall@3 | 10 hand-written questions |
| Semantic retrieval | 100% Recall@1 and Recall@3 | Same 10 questions |
| AI answer factual smoke test | 2/2 passed | Two inventory questions |
| SKU-to-quantity association checks | Passed | Two evaluation cases |
| Inventory integration failure tests | Passed | Online store and ERP failure paths |
| AI API safety tests | Passed | Successful answers, validation, errors and timeouts |
| Full automated test suite | Passed | Current project test suite |

## 3. Reliability and safety controls

The prototype includes:

- Input validation for inventory records and API requests.
- Deterministic inventory comparison logic.
- Read-only inventory tools for the AI agent.
- Semantic retrieval of operational runbooks.
- Error handling for upstream service failures and AI service errors.
- Safe API error responses that avoid exposing tested internal exception details.
- Automated tests for selected failure scenarios.

## 4. Known limitations

- Retrieval results are based on a small, manually written dataset.
- The answer evaluation checks only a small number of questions.
- SKU association checks use nearby text and do not prove that every quantity is correctly labelled.
- Retrieval scores are similarity measures, not confidence probabilities.
- Mock services do not demonstrate reliability against real enterprise systems.
- Production readiness, security, load handling and retrieval quality on unseen questions have not yet been established.

## 5. Reproducibility

Run the following commands from the project root with the virtual environment activated:

```powershell
python -m pytest -q
python retrieval_eval.py
python answer_eval.py
```

The mock online store and ERP services must be running before executing the AI answer evaluation.

## 6. Next evaluation priorities

1. Expand the retrieval benchmark with unseen and ambiguous questions.
2. Validate exact SKU, online quantity, ERP quantity and difference relationships.
3. Test unsupported questions and adversarial runbook content.
4. Measure response latency and failure rates.
5. Add structured, repeatable evaluation outputs for regression testing.

**Status:** Working prototype with passing automated tests and an initial retrieval and answer evaluation baseline.
