from .settings import Settings, settings

# Backward-compatible alias for older service modules that still import the
# settings object via ``BackendSettings``.
BackendSettings = Settings

__all__ = ["BackendSettings", "Settings", "settings"]
