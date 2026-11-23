
"""FastAPI application exposing inventory, AI, and health endpoints."""

import logging
from fastapi import FastAPI
from fastapi import HTTPException
from schemas import InventoryComparisonRequest
from inventory import compare_inventory
from schemas import InventoryDiscrepancy
from ai_agent import ask_commerceops
from schemas import AIQuestionRequest
import ollama
import httpx
from integrations.inventory_service import get_inventory_comparison
from integrations.health_service import get_integrations_health
import uuid
import time

from fastapi import Request
from integrations.request_context import (
    request_id_var,
)

from integrations.logging_config import configure_logging
from integrations.metrics import metrics
from integrations import approval_service
from integrations import execution_service

from schemas import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
)

configure_logging("commerceops-ai")

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CommerceOps AI",
    description="Retail operations and integration assistant",
    version="0.3.0",
)


@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )
        metrics.record_request(
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    except Exception:
        duration_ms = round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                )
        logger.exception(
            "HTTP request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise

    finally:
        request_id_var.reset(token)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": "CommerceOps AI",
    }


@app.get("/inventory/discrepancies")
def inventory_discrepancies():
    try:
        results = get_inventory_comparison()
    except RuntimeError as exc:
        logger.warning("Inventory integration failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Inventory systems are temporarily unavailable.",
        ) from exc
    except ValueError as exc:
        logger.warning("Inventory integration returned invalid data: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Inventory systems returned invalid data.",
        ) from exc

    return [
        item for item in results
        if item["status"] != "matched"
    ]


@app.get("/inventory/summary")
def inventory_summary():
    try:
        results = get_inventory_comparison()
    except RuntimeError as exc:
        logger.warning("Inventory integration failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Inventory systems are temporarily unavailable.",
        ) from exc
    except ValueError as exc:
        logger.warning("Inventory integration returned invalid data: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Inventory systems returned invalid data.",
        ) from exc

    return {
        "total_skus": len(results),
        "discrepancy_count": sum(
            item["status"] != "matched" for item in results
        ),
        "matched_count": sum(
            item["status"] == "matched" for item in results
        ),
    }

@app.post("/inventory/compare")
def compare_inventory_request(request: InventoryComparisonRequest):
    try:
        return compare_inventory(
            online_store={
                sku: record.model_dump()
                for sku, record in request.online_store.items()
            },
            erp_system={
                sku: record.model_dump()
                for sku, record in request.erp_system.items()
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    
    except httpx.TimeoutException as exc:
        logger.warning("AI service request timed out")
        raise HTTPException(
            status_code=504,
            detail="The AI service took too long to respond. Please try again.",
        ) from exc

    except ollama.RequestError as exc:
        logger.warning("AI service request failed")
        raise HTTPException(
            status_code=503,
            detail="The AI service is unavailable. Please try again.",
        ) from exc

    except ollama.ResponseError as exc:
        logger.exception("AI service returned an error")
        raise HTTPException(
            status_code=502,
            detail="The AI service returned an error.",
        ) from exc

    except ValueError as exc:
        logger.exception("Inventory data could not be retrieved safely")
        raise HTTPException(
            status_code=502,
            detail="Inventory data could not be retrieved safely.",
        ) from exc

    except RuntimeError as exc:
        logger.exception("AI agent could not produce a verified answer")
        raise HTTPException(
            status_code=502,
            detail="AI agent could not produce a verified answer.",
        ) from exc



@app.post("/ai/ask")
def ask_ai(request: AIQuestionRequest):
    try:
        answer = ask_commerceops(request.question)
        return {"answer": answer}

    except ollama.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI service is unavailable. Please try again.",
        ) from exc

    except ollama.ResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI service returned an error.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Inventory data could not be retrieved safely.",
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI agent could not produce a verified answer.",
        ) from exc

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The AI request timed out. Please try again.",
        ) from exc

@app.get("/health/integrations")
def integrations_health():
    return get_integrations_health()

@app.get("/metrics")
def get_application_metrics():
    return metrics.get_metrics("commerceops-ai")


@app.post("/approvals", status_code=201)
def create_approval(request: ApprovalCreateRequest):
    try:
        approval = approval_service.create_approval(
            action_type=request.action_type,
            description=request.description,
            proposed_changes=request.proposed_changes,
        )

        return approval

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        logger.exception("Failed to create approval")
        raise HTTPException(
            status_code=503,
            detail="Approval could not be recorded because audit storage is unavailable.",
        ) from exc


@app.get("/approvals/{approval_id}")
def get_approval(approval_id: str):
    approval = approval_service.get_approval(approval_id)

    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Approval not found.",
        )

    return approval


@app.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
):
    try:
        return approval_service.decide_approval(
            approval_id=approval_id,
            decision=request.decision,
            decided_by=request.decided_by,
            role=request.role,
            comment=request.comment,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        status_code = (
            404 if str(exc) == "Approval not found" else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        logger.exception("Failed to record approval decision")
        raise HTTPException(
            status_code=503,
            detail="Approval decision could not be recorded because audit storage is unavailable.",
        ) from exc


@app.post("/approvals/{approval_id}/execute")
def execute_approved_adjustment(approval_id: str):
    """Execute an approved inventory adjustment."""

    try:
        return execution_service.execute_approved_inventory_adjustment(
            approval_id
        )

    except ValueError as exc:
        status_code = (
            404 if str(exc) == "Approval not found" else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        execution = execution_service.get_execution(approval_id)

        logger.exception(
            "Inventory adjustment execution failed",
            extra={"approval_id": approval_id},
        )

        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Inventory adjustment execution did not complete. "
                    "Inspect the execution record and reconcile both systems."
                ),
                "execution": execution,
            },
        ) from exc

    except OSError as exc:
        logger.exception(
            "Inventory execution audit storage failed",
            extra={"approval_id": approval_id},
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Execution could not be safely recorded because "
                "audit storage is unavailable."
            ),
        ) from exc


@app.get("/approvals/{approval_id}/execution")
def get_approval_execution(approval_id: str):
    """Retrieve the execution record for an approval."""

    execution = execution_service.get_execution(approval_id)

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail="Execution record not found.",
        )

    return execution
