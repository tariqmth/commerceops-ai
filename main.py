
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CommerceOps AI",
    description="Retail operations and integration assistant",
    version="0.3.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": "CommerceOps AI",
    }


@app.get(
    "/inventory/discrepancies",
    response_model=list[InventoryDiscrepancy],
)
def inventory_discrepancies():
    return compare_inventory()


@app.get("/inventory/summary")
def inventory_summary():
    results = compare_inventory()

    matched = sum(
        1 for item in results if item["status"] == "matched"
    )
    discrepancies = sum(
        1 for item in results if item["status"] == "discrepancy"
    )
    missing = sum(
        1 for item in results if item["status"] == "missing_from_system"
    )

    return {
        "total_skus": len(results),
        "matched": matched,
        "discrepancies": discrepancies,
        "missing_from_system": missing,
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
            detail="The AI service took too long to respond. Please try again.",
        ) from exc

