"""Client fingerprint generation for token binding (MED-002).

Generates a fingerprint from client request headers to bind tokens
to the original client, preventing token theft and replay attacks.
"""

import hashlib

from starlette.requests import Request


def generate_client_fingerprint(request: Request, *, include_ip: bool = True) -> str:
    """Generate a fingerprint from client request characteristics.

    Combines stable client identifiers:
    - User-Agent header
    - Accept-Language header
    - Client IP (optional, disabled for mobile)

    SEC-005: IP excluded by default for mobile to handle network changes.

    Args:
        request: The incoming HTTP request.
        include_ip: Whether to include client IP in fingerprint.
                   Set to False for mobile clients.

    Returns:
        SHA-256 hash of combined client characteristics.
    """
    components = []

    # User-Agent is relatively stable for a client
    user_agent = request.headers.get("user-agent", "")
    components.append(f"ua:{user_agent}")

    # Accept-Language provides additional entropy
    accept_lang = request.headers.get("accept-language", "")
    components.append(f"lang:{accept_lang}")

    # SEC-005: Only include IP for web clients, not mobile
    if include_ip:
        client_ip = ""
        if request.client:
            client_ip = request.client.host
        components.append(f"ip:{client_ip}")

    # Device ID for mobile clients (if provided in headers)
    device_id = request.headers.get("x-device-id", "")
    if device_id:
        components.append(f"device:{device_id}")

    # Combine and hash
    combined = "|".join(components)
    fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:32]

    return fingerprint


def generate_mobile_fingerprint(request: Request) -> str:
    """Generate a fingerprint for mobile clients.

    SEC-005: Excludes IP address for stability across network changes.
    Uses X-Device-ID header if available.

    Args:
        request: The incoming HTTP request.

    Returns:
        SHA-256 hash of mobile client characteristics.
    """
    return generate_client_fingerprint(request, include_ip=False)


def validate_fingerprint(
    request: Request,
    expected_fingerprint: str | None,
    *,
    strict: bool = False,
) -> bool:
    """Validate that request fingerprint matches expected fingerprint.

    Args:
        request: The incoming HTTP request.
        expected_fingerprint: The fingerprint stored with the token.
        strict: If True, require fingerprint match; if False, allow mismatch.

    Returns:
        True if fingerprint matches or validation is non-strict.
    """
    if not expected_fingerprint:
        return True  # No fingerprint stored, allow

    if not strict:
        return True  # Non-strict mode, always allow

    current = generate_client_fingerprint(request)
    return current == expected_fingerprint
