"""Health checks for the external inventory integrations."""

import httpx


ONLINE_STORE_URL = "http://127.0.0.1:8001"
ERP_URL = "http://127.0.0.1:8002"


def check_service_health(
    base_url: str,
    service_name: str,
) -> dict:
    """Check whether an external service health endpoint is responding."""

    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/health",
            timeout=2.0,
        )

        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, dict) or payload.get("status") != "ok":
            return {
                "service": service_name,
                "status": "unhealthy",
                "message": "Service returned an invalid health response",
            }

        return {
            "service": service_name,
            "status": "healthy",
        }

    except httpx.HTTPError:
        return {
            "service": service_name,
            "status": "unhealthy",
            "message": "Service is unavailable",
        }

    except ValueError:
        return {
            "service": service_name,
            "status": "unhealthy",
            "message": "Service returned invalid JSON",
        }


def get_integrations_health() -> dict:
    """Check the health of all external integrations."""

    services = [
        check_service_health(ONLINE_STORE_URL, "online-store"),
        check_service_health(ERP_URL, "erp"),
    ]

    all_healthy = all(
        service["status"] == "healthy"
        for service in services
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }