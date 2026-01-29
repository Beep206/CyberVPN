from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from aiogram import F, Router
from aiogram.types import CallbackQuery

from middleware.admin import admin_required

if TYPE_CHECKING:
    from aiogram_i18n import I18nContext

    from clients.api_client import APIClient

logger = structlog.get_logger(__name__)

router = Router(name="admin_import_sync")
router.callback_query.middleware(admin_required)


@router.callback_query(F.data == "admin:import")
async def import_menu_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
) -> None:
    """Show data import/sync menu."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-import-users"),
            callback_data="admin:import:users",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-import-subscriptions"),
            callback_data="admin:import:subscriptions",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=i18n.get("admin-import-sync-remnawave"),
            callback_data="admin:import:sync:remnawave",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 " + i18n.get("button-back"),
            callback_data="admin:menu",
        )
    )

    await callback.message.edit_text(
        text=i18n.get("admin-import-title"),
        reply_markup=builder.as_markup(),
    )

    logger.info("admin_import_menu_opened", admin_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "admin:import:users")
async def import_users_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Import users from Remnawave."""
    try:
        await callback.answer(i18n.get("admin-import-users-starting"), show_alert=True)

        # Trigger import via API
        result = await api_client.import_users_from_remnawave()

        imported_count = result.get("imported_count", 0)
        skipped_count = result.get("skipped_count", 0)
        errors_count = result.get("errors_count", 0)

        await callback.message.edit_text(
            text=i18n.get(
                "admin-import-users-completed",
                imported=imported_count,
                skipped=skipped_count,
                errors=errors_count,
            ),
        )

        logger.info(
            "admin_users_imported",
            admin_id=callback.from_user.id,
            imported=imported_count,
            skipped=skipped_count,
            errors=errors_count,
        )

    except Exception as e:
        logger.error("admin_import_users_error", admin_id=callback.from_user.id, error=str(e))
        await callback.message.edit_text(
            text=i18n.get("admin-import-users-failed", error=str(e)),
        )


@router.callback_query(F.data == "admin:import:subscriptions")
async def import_subscriptions_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Import subscriptions from Remnawave."""
    try:
        await callback.answer(i18n.get("admin-import-subscriptions-starting"), show_alert=True)

        # Trigger import via API
        result = await api_client.import_subscriptions_from_remnawave()

        imported_count = result.get("imported_count", 0)
        updated_count = result.get("updated_count", 0)
        errors_count = result.get("errors_count", 0)

        await callback.message.edit_text(
            text=i18n.get(
                "admin-import-subscriptions-completed",
                imported=imported_count,
                updated=updated_count,
                errors=errors_count,
            ),
        )

        logger.info(
            "admin_subscriptions_imported",
            admin_id=callback.from_user.id,
            imported=imported_count,
            updated=updated_count,
            errors=errors_count,
        )

    except Exception as e:
        logger.error("admin_import_subscriptions_error", admin_id=callback.from_user.id, error=str(e))
        await callback.message.edit_text(
            text=i18n.get("admin-import-subscriptions-failed", error=str(e)),
        )


@router.callback_query(F.data == "admin:import:sync:remnawave")
async def sync_remnawave_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Sync all data with Remnawave."""
    try:
        await callback.answer(i18n.get("admin-import-sync-starting"), show_alert=True)

        # Trigger full sync via API
        result = await api_client.sync_with_remnawave()

        users_synced = result.get("users_synced", 0)
        subscriptions_synced = result.get("subscriptions_synced", 0)
        configs_synced = result.get("configs_synced", 0)
        errors = result.get("errors", [])

        sync_text = i18n.get(
            "admin-import-sync-completed",
            users=users_synced,
            subscriptions=subscriptions_synced,
            configs=configs_synced,
        )

        if errors:
            sync_text += "\n\n" + i18n.get("admin-import-sync-errors") + ":\n"
            for error in errors[:5]:  # Show first 5 errors
                sync_text += f"- {error}\n"

        await callback.message.edit_text(text=sync_text)

        logger.info(
            "admin_remnawave_synced",
            admin_id=callback.from_user.id,
            users=users_synced,
            subscriptions=subscriptions_synced,
            configs=configs_synced,
            errors_count=len(errors),
        )

    except Exception as e:
        logger.error("admin_sync_remnawave_error", admin_id=callback.from_user.id, error=str(e))
        await callback.message.edit_text(
            text=i18n.get("admin-import-sync-failed", error=str(e)),
        )


@router.callback_query(F.data == "admin:import:status")
async def import_status_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: APIClient,
) -> None:
    """Show import/sync status."""
    try:
        # Get last sync status
        status = await api_client.get_sync_status()

        last_sync = status.get("last_sync_at", "Never")
        is_syncing = status.get("is_syncing", False)
        last_error = status.get("last_error")

        status_text = i18n.get("admin-import-status-title") + "\n\n"
        status_text += f"{i18n.get('admin-import-last-sync')}: {last_sync}\n"
        status_text += f"{i18n.get('admin-import-status')}: "
        status_text += i18n.get("admin-import-syncing") if is_syncing else i18n.get("admin-import-idle")
        status_text += "\n"

        if last_error:
            status_text += f"\n{i18n.get('admin-import-last-error')}:\n{last_error}"

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔄 " + i18n.get("admin-import-refresh"),
                callback_data="admin:import:status",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 " + i18n.get("button-back"),
                callback_data="admin:import",
            )
        )

        await callback.message.edit_text(
            text=status_text,
            reply_markup=builder.as_markup(),
        )

        logger.info("admin_import_status_viewed", admin_id=callback.from_user.id)

    except Exception as e:
        logger.error("admin_import_status_error", admin_id=callback.from_user.id, error=str(e))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()
