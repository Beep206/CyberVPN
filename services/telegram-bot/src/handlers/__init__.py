"""CyberVPN Telegram Bot — Handler routers registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Dispatcher, Router


def _create_admin_router() -> Router:
    """Create admin sub-router with IsAdmin filter applied to all handlers."""
    from aiogram import Router

    from src.filters.admin import IsAdmin
    from src.handlers.admin.access import router as access_router
    from src.handlers.admin.broadcast import router as broadcast_router
    from src.handlers.admin.gateways import router as gateways_router
    from src.handlers.admin.import_sync import router as import_router
    from src.handlers.admin.main import router as admin_main_router
    from src.handlers.admin.notifications import router as notifications_router
    from src.handlers.admin.plans import router as plans_router
    from src.handlers.admin.promos import router as promos_router
    from src.handlers.admin.referral import router as referral_admin_router
    from src.handlers.admin.stats import router as stats_router
    from src.handlers.admin.system import router as system_router
    from src.handlers.admin.users import router as users_router

    admin_router = Router(name="admin")
    admin_router.message.filter(IsAdmin())
    admin_router.callback_query.filter(IsAdmin())

    admin_router.include_routers(
        admin_main_router,
        stats_router,
        users_router,
        broadcast_router,
        plans_router,
        promos_router,
        access_router,
        gateways_router,
        notifications_router,
        referral_admin_router,
        import_router,
        system_router,
    )

    return admin_router


def register_routers(dp: Dispatcher) -> None:
    """Register all handler routers with the dispatcher.

    Routers are included in order of priority:
    1. Admin router (filtered by IsAdmin) — most restrictive first
    2. User-facing routers — start, menu, subscription, payment, etc.
    """
    from src.handlers.account import router as account_router
    from src.handlers.config import router as config_router
    from src.handlers.menu import router as menu_router
    from src.handlers.payment import router as payment_router
    from src.handlers.promocode import router as promocode_router
    from src.handlers.referral import router as referral_router
    from src.handlers.start import router as start_router
    from src.handlers.subscription import router as subscription_router
    from src.handlers.support import router as support_router
    from src.handlers.trial import router as trial_router

    # Admin router (with IsAdmin filter)
    admin_router = _create_admin_router()

    dp.include_routers(
        # Admin (filtered) — must come before user routers
        admin_router,
        # User-facing handlers
        start_router,
        menu_router,
        subscription_router,
        payment_router,
        config_router,
        trial_router,
        referral_router,
        promocode_router,
        account_router,
        support_router,
    )
