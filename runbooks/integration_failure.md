
# Inventory Integration Failure

## Purpose
Investigate unavailable or failing inventory APIs.

## Initial checks
1. Check the affected service health endpoint.
2. Record the HTTP status code and timestamp.
3. Inspect application logs for the failed request.
4. Check whether the failure is a timeout, HTTP error, or invalid response.
5. Verify that the configured service URL is correct.

## Recommended response
- Timeout: check service responsiveness and network connectivity.
- HTTP 5xx: investigate the upstream service and its logs.
- HTTP 4xx: check request configuration and API requirements.
- Invalid JSON or schema: treat the response as untrusted and investigate its format.

## Retry guidance
- Retry only when appropriate for the error and operation.
- Use bounded retries and backoff for transient failures.
- Avoid uncontrolled retry loops.
- Do not retry non-idempotent operations without assessing duplicate-action risk.

## Safety requirements
- Do not expose credentials or secrets in logs.
- Do not invent a successful response when the service fails.
- Do not claim inventory was retrieved if the API request failed.
- Escalate persistent failures to the service owner.
