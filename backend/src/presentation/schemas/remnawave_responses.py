"""Compatibility shim for legacy Remnawave response imports.

The canonical upstream Remnawave contract now lives in
``src.infrastructure.remnawave.contracts``.
"""

from src.infrastructure.remnawave.contracts import *  # noqa: F401,F403
