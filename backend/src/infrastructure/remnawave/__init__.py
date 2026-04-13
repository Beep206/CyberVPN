"""Internal Remnawave integration package.

Contracts, client behaviour, gateways and adapters should be sourced from this
package so the upstream Remnawave API is represented in one place.
"""

from src.infrastructure.remnawave.client import RemnawaveClient, get_remnawave_client, remnawave_client

__all__ = [
    "RemnawaveClient",
    "get_remnawave_client",
    "remnawave_client",
]
