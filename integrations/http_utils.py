
"""Shared HTTP helpers for resilient, request-correlated service calls."""

import time

import httpx

from integrations.request_context import request_id_var


def get_json_with_retries(
    url: str,
    service_name: str,
    attempts: int = 3,
) -> dict:
    """GET JSON, retrying transient failures and propagating request IDs."""

    request_id = request_id_var.get()

    headers = {}
    if request_id != "-":
        headers["X-Request-ID"] = request_id

    for attempt in range(1, attempts + 1):
        try:
            response = httpx.get(
                url,
                timeout=5.0,
                **({"headers": headers} if headers else {}),
            )
            response.raise_for_status()
            return response.json()

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt == attempts:
                raise RuntimeError(
                    f"{service_name} service request failed after {attempts} attempts"
                ) from exc

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            # Do not retry client-side errors (4xx).
            if status_code < 500:
                raise RuntimeError(
                    f"{service_name} service returned HTTP {status_code}"
                ) from exc

            # Retry server-side errors (5xx) until the final attempt.
            if attempt == attempts:
                raise RuntimeError(
                    f"{service_name} service request failed after "
                    f"{attempts} attempts (HTTP {status_code})"
                ) from exc

        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"{service_name} service request failed"
            ) from exc

        except ValueError as exc:
            # Invalid JSON is not treated as a transient network failure.
            raise RuntimeError(
                f"{service_name} returned invalid JSON"
            ) from exc

        time.sleep(0.2 * attempt)

    raise RuntimeError(f"{service_name} service request failed")
