"""Security.txt endpoint (RFC 9116).

SEC-017: Provides a standardized way for security researchers to report vulnerabilities.
See: https://securitytxt.org/
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["well-known"])

# Security contact information
# Update these values for your organization
SECURITY_CONTACT = "security@cybervpn.example"  # Email for security reports
SECURITY_POLICY_URL = "https://cybervpn.example/security-policy"  # Optional
ACKNOWLEDGEMENTS_URL = "https://cybervpn.example/security/acknowledgements"  # Optional
PREFERRED_LANGUAGES = "en, ru"


def generate_security_txt() -> str:
    """Generate security.txt content following RFC 9116.

    Returns:
        Formatted security.txt content
    """
    # Expires should be less than 1 year from now
    expires = datetime.now(UTC) + timedelta(days=365)
    expires_str = expires.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    lines = [
        "# CyberVPN Security Policy",
        "# See https://securitytxt.org/ for format specification",
        "",
        f"Contact: mailto:{SECURITY_CONTACT}",
        f"Expires: {expires_str}",
        f"Preferred-Languages: {PREFERRED_LANGUAGES}",
        "",
        "# We appreciate responsible disclosure of security vulnerabilities.",
        "# Please allow us reasonable time to address reported issues",
        "# before public disclosure.",
    ]

    # Add optional fields if configured
    if SECURITY_POLICY_URL and not SECURITY_POLICY_URL.endswith("example"):
        lines.insert(4, f"Policy: {SECURITY_POLICY_URL}")

    if ACKNOWLEDGEMENTS_URL and not ACKNOWLEDGEMENTS_URL.endswith("example"):
        lines.insert(5, f"Acknowledgements: {ACKNOWLEDGEMENTS_URL}")

    return "\n".join(lines) + "\n"


@router.get(
    "/.well-known/security.txt",
    response_class=PlainTextResponse,
    summary="Security.txt",
    description="Security contact information following RFC 9116",
)
async def security_txt() -> PlainTextResponse:
    """Return security.txt content.

    This endpoint follows RFC 9116 and provides:
    - Contact information for security researchers
    - Expiration date for the information
    - Preferred languages for communication

    See: https://www.rfc-editor.org/rfc/rfc9116
    """
    content = generate_security_txt()
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
    )


# Also serve at /security.txt for convenience (common alternative location)
@router.get(
    "/security.txt",
    response_class=PlainTextResponse,
    include_in_schema=False,  # Don't duplicate in API docs
)
async def security_txt_root() -> PlainTextResponse:
    """Convenience redirect for /security.txt."""
    content = generate_security_txt()
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
    )
