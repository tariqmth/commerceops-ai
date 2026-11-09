
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

from fastapi import Request
from integrations.request_context import (
    request_id_var,
    RequestIdFilter,
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)s "
        "[request_id=%(request_id)s] "
        "%(name)s: %(message)s"
    ),
)

for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

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

    try:
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP request completed method=%s path=%s status_code=%s",
            request.method,
            request.url.path,
            response.status_code,
        )

        return response

    except Exception:
        logger.exception(
            "HTTP request failed method=%s path=%s",
            request.method,
            request.url.path,
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