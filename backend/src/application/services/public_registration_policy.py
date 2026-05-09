"""Public account creation guard for S1 registration kill switch."""

from dataclasses import dataclass

from src.config.settings import settings

REGISTRATION_DISABLED_CODE = "REGISTRATION_DISABLED"
REGISTRATION_DISABLED_MESSAGE = "Public registration is currently paused."


@dataclass(frozen=True)
class PublicRegistrationState:
    """Runtime state for public account creation gates."""

    enabled: bool
    invite_required: bool

    @property
    def paused(self) -> bool:
        return not self.enabled


class PublicRegistrationDisabledError(ValueError):
    """Raised when a public flow attempts to create a new account while paused."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        super().__init__(REGISTRATION_DISABLED_MESSAGE)

    def public_detail(self) -> dict[str, str]:
        return {
            "code": REGISTRATION_DISABLED_CODE,
            "message": REGISTRATION_DISABLED_MESSAGE,
            "channel": self.channel,
        }


def get_public_registration_state(
    *,
    registration_enabled: bool | None = None,
    invite_required: bool | None = None,
) -> PublicRegistrationState:
    """Return the effective public registration state."""

    return PublicRegistrationState(
        enabled=settings.registration_enabled if registration_enabled is None else registration_enabled,
        invite_required=settings.registration_invite_required if invite_required is None else invite_required,
    )


def ensure_public_registration_enabled(
    *,
    channel: str,
    registration_enabled: bool | None = None,
) -> None:
    """Fail closed when a public flow tries to create a new account while paused."""

    enabled = settings.registration_enabled if registration_enabled is None else registration_enabled
    if not enabled:
        raise PublicRegistrationDisabledError(channel=channel)
