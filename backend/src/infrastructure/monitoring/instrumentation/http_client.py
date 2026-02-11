"""HTTP client instrumentation for external API metrics.

Tracks external API call duration and status using httpx event hooks.
"""

import httpx

from src.infrastructure.monitoring.metrics import external_api_duration_seconds


def create_instrumented_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx AsyncClient with Prometheus metrics instrumentation.

    Args:
        **kwargs: Arguments to pass to httpx.AsyncClient constructor

    Returns:
        Instrumented httpx.AsyncClient

    Usage:
        client = create_instrumented_client(
            base_url="http://api.example.com",
            timeout=30.0,
        )
    """

    async def log_request(request: httpx.Request) -> None:
        """Log request start (store start time in request state)."""
        import time

        request.extensions["start_time"] = time.perf_counter()

    async def log_response(response: httpx.Response) -> None:
        """Log response and record duration metric."""
        import time

        start_time = response.request.extensions.get("start_time")
        if start_time:
            duration = time.perf_counter() - start_time

            # Extract service name from base URL
            service = response.request.url.host or "unknown"

            # Extract endpoint path
            endpoint = response.request.url.path or "/"

            # Get HTTP method
            method = response.request.method

            external_api_duration_seconds.labels(
                service=service,
                endpoint=endpoint,
                method=method,
            ).observe(duration)

    # Create client with event hooks
    event_hooks = kwargs.get("event_hooks", {})
    event_hooks["request"] = event_hooks.get("request", []) + [log_request]
    event_hooks["response"] = event_hooks.get("response", []) + [log_response]
    kwargs["event_hooks"] = event_hooks

    return httpx.AsyncClient(**kwargs)


def instrument_existing_client(client: httpx.AsyncClient) -> None:
    """Instrument an existing httpx AsyncClient with metrics.

    Args:
        client: Existing httpx.AsyncClient to instrument

    This modifies the client in-place by adding event hooks.
    """

    async def log_request(request: httpx.Request) -> None:
        """Log request start (store start time in request state)."""
        import time

        request.extensions["start_time"] = time.perf_counter()

    async def log_response(response: httpx.Response) -> None:
        """Log response and record duration metric."""
        import time

        start_time = response.request.extensions.get("start_time")
        if start_time:
            duration = time.perf_counter() - start_time

            # Extract service name from base URL
            service = response.request.url.host or "unknown"

            # Extract endpoint path
            endpoint = response.request.url.path or "/"

            # Get HTTP method
            method = response.request.method

            external_api_duration_seconds.labels(
                service=service,
                endpoint=endpoint,
                method=method,
            ).observe(duration)

    # Add hooks to existing client
    if "request" not in client.event_hooks:
        client.event_hooks["request"] = []
    if "response" not in client.event_hooks:
        client.event_hooks["response"] = []

    client.event_hooks["request"].append(log_request)
    client.event_hooks["response"].append(log_response)
