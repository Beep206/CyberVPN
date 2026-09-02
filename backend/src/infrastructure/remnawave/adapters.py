"""Fail-closed compatibility shim for removed auth-time VPN provisioning."""


class RemnawaveUserAdapter:
    """Prevent legacy AdminUser authentication from creating orphan VPN users."""

    async def create_user(
        self,
        username: str,
        email: str,
        telegram_id: int | None = None,
    ) -> dict:
        _ = username, email, telegram_id
        raise RuntimeError(
            "Auth-time Remnawave provisioning is disabled; use a canonical MobileUser subscription or trial flow"
        )


def get_remnawave_adapter() -> RemnawaveUserAdapter:
    """Return the compatibility shim without loading any provider credential."""

    return RemnawaveUserAdapter()
