from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from aiogram import F, Router

from src.keyboards.subscription import (
    addons_keyboard,
    duration_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
)
from src.states.subscription import SubscriptionState

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message
    from aiogram_i18n import I18nContext

    from src.config import BotSettings
    from src.services.api_client import CyberVPNAPIClient

logger = structlog.get_logger(__name__)

router = Router(name="subscription")


def _format_price(price_rub: Any = None, price_usd: Any = None) -> str:
    if price_rub is not None:
        return f"{float(price_rub):.0f} RUB"
    if price_usd is not None:
        return f"${float(price_usd):.2f}"
    return ""


def _is_telegram_sellable(plan: dict[str, Any]) -> bool:
    sale_channels = plan.get("sale_channels") or []
    if not sale_channels:
        return True
    return "telegram_bot" in {str(channel) for channel in sale_channels}


def _group_plan_catalog(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for plan in plans:
        plan_code = str(plan.get("plan_code") or "").strip()
        if not plan_code:
            continue

        group = grouped.setdefault(
            plan_code,
            {
                "plan_code": plan_code,
                "display_name": plan.get("display_name") or plan.get("name") or plan_code.title(),
                "sort_order": int(plan.get("sort_order", 0) or 0),
                "devices_included": int(plan.get("devices_included") or 0),
                "catalog_visibility": str(plan.get("catalog_visibility") or "public"),
                "sale_channels": list(plan.get("sale_channels") or []),
                "durations": [],
            },
        )
        group["durations"].append(
            {
                "plan_id": plan.get("uuid") or plan.get("id"),
                "duration_days": int(plan.get("duration_days") or 0),
                "price_usd": plan.get("price_usd"),
                "price_rub": plan.get("price_rub"),
            }
        )

    for group in grouped.values():
        group["durations"].sort(key=lambda item: int(item.get("duration_days", 0)))

    return sorted(grouped.values(), key=lambda item: (int(item.get("sort_order", 0)), item.get("display_name", "")))


def _group_public_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible alias kept for older tests/imports."""

    return _group_plan_catalog(plans)


def _find_plan_group(plan_catalog: list[dict[str, Any]], plan_code: str) -> dict[str, Any] | None:
    for plan in plan_catalog:
        if str(plan.get("plan_code")) == str(plan_code):
            return plan
    return None


def _find_duration_option(plan_group: dict[str, Any], duration_days: int) -> dict[str, Any] | None:
    for duration in plan_group.get("durations") or []:
        if int(duration.get("duration_days") or 0) == duration_days:
            return duration
    return None


def _resolve_supported_addons(addons_catalog: list[dict[str, Any]], plan_code: str) -> dict[str, Any]:
    supported: dict[str, Any] = {}
    for addon in addons_catalog:
        code = str(addon.get("code") or "")
        if code != "extra_device":
            continue
        if addon.get("requires_location"):
            continue
        max_quantity = int((addon.get("max_quantity_by_plan") or {}).get(plan_code, 0) or 0)
        if max_quantity <= 0:
            continue
        supported[code] = {"definition": addon, "max_quantity": max_quantity}
    return supported


def _build_checkout_payload(plan_id: str, addon_qty: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "plan_id": plan_id,
        "addons": [],
        "currency": "USD",
        "payment_method": "cryptobot",
    }
    if addon_qty > 0:
        payload["addons"] = [{"code": "extra_device", "qty": addon_qty}]
    return payload


def _addons_summary_text(*, plan_name: str, duration_days: int, extra_device_qty: int, extra_device_limit: int) -> str:
    summary = (
        "🧩 Add-ons\n\n"
        f"Plan: {plan_name}\n"
        f"Period: {duration_days} days\n"
        f"Extra device: {extra_device_qty}/{extra_device_limit}\n"
    )
    if extra_device_limit <= 0:
        summary += "\nNo bot-supported add-ons are available for this plan."
    return summary


async def _render_payment_step(
    *,
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
    settings: BotSettings,
) -> None:
    data = await state.get_data()
    plan_id = str(data.get("plan_id") or "")
    duration_days = int(data.get("duration_days") or 0)
    plan_name = str(data.get("plan_name") or "Plan")
    extra_device_qty = int(data.get("extra_device_qty") or 0)
    user_id = callback.from_user.id

    if not plan_id or duration_days <= 0:
        raise ValueError("Missing checkout context")

    payload = _build_checkout_payload(plan_id, extra_device_qty)
    quote = await api_client.quote_checkout(user_id, payload)
    amount = quote.get("gateway_amount", quote.get("displayed_price", 0))

    text = i18n.get(
        "subscription-select-payment",
        plan=plan_name,
        duration=duration_days,
        price=_format_price(price_usd=amount),
    )
    if extra_device_qty > 0:
        text += f"\n\nAdd-ons:\n+1 device x {extra_device_qty}"

    await state.update_data(checkout_payload=payload, checkout_quote=quote)
    await callback.message.edit_text(
        text=text,
        reply_markup=payment_methods_keyboard(i18n, settings),
    )
    await state.set_state(SubscriptionState.selecting_payment)


async def present_explicit_plan_offer(
    *,
    state: FSMContext,
    i18n: I18nContext,
    plan: dict[str, Any],
    target_message: Message,
    use_edit_text: bool = False,
    requested_duration_days: int | None = None,
) -> bool:
    """Open a direct purchase flow for a single explicit plan offer."""

    if not plan or not bool(plan.get("is_active", True)) or not _is_telegram_sellable(plan):
        return False

    plan_catalog = _group_plan_catalog([plan])
    if not plan_catalog:
        return False

    plan_group = plan_catalog[0]
    display_name = str(plan_group.get("display_name") or plan_group.get("plan_code") or "Plan")
    text = i18n.get("subscription-direct-offer", plan=display_name)
    if requested_duration_days and _find_duration_option(plan_group, requested_duration_days) is not None:
        text += "\n\n" + i18n.get("subscription-direct-offer-duration", duration_days=requested_duration_days)

    await state.clear()
    await state.update_data(
        plan_catalog=plan_catalog,
        selected_plan_code=plan_group.get("plan_code"),
        plan_name=display_name,
        plan_group=plan_group,
        flow_origin="direct_offer",
        requested_duration_days=requested_duration_days,
    )

    reply_markup = duration_keyboard(i18n, plan=plan_group, durations=plan_group.get("durations"))
    if use_edit_text:
        await target_message.edit_text(text=text, reply_markup=reply_markup)
    else:
        await target_message.answer(text=text, reply_markup=reply_markup)
    await state.set_state(SubscriptionState.selecting_duration)
    return True


@router.callback_query(F.data == "subscription:buy")
async def buy_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    try:
        plans = await api_client.get_plans()
        plan_catalog = _group_plan_catalog(
            [
                plan
                for plan in plans
                if isinstance(plan, dict)
                and str(plan.get("catalog_visibility") or "public") == "public"
                and _is_telegram_sellable(plan)
                and bool(plan.get("is_active", True))
            ]
        )

        if not plan_catalog:
            await callback.answer(i18n.get("error-no-plans"), show_alert=True)
            return

        await state.clear()
        await state.update_data(plan_catalog=plan_catalog)
        await callback.message.edit_text(
            text=i18n.get("subscription-select-plan"),
            reply_markup=plans_keyboard(i18n, plan_catalog),
        )
        await state.set_state(SubscriptionState.selecting_plan)
        logger.info("subscription_flow_started", user_id=callback.from_user.id)
    except Exception as exc:
        logger.error("buy_subscription_error", user_id=callback.from_user.id, error=str(exc))
        await callback.answer(i18n.get("error-generic"), show_alert=True)

    await callback.answer()


@router.callback_query(SubscriptionState.selecting_plan, F.data.startswith("plan:select:"))
async def plan_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    if callback.data is None:
        await state.clear()
        return

    plan_code = callback.data.split(":")[-1]
    data = await state.get_data()
    plan_catalog = data.get("plan_catalog") or []
    plan_group = _find_plan_group(plan_catalog, plan_code)

    if plan_group is None:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    await state.update_data(
        selected_plan_code=plan_code,
        plan_name=plan_group.get("display_name"),
        plan_group=plan_group,
    )
    await callback.message.edit_text(
        text=i18n.get("subscription-select-duration"),
        reply_markup=duration_keyboard(i18n, plan=plan_group, durations=plan_group.get("durations")),
    )
    await state.set_state(SubscriptionState.selecting_duration)
    logger.info("plan_selected", user_id=callback.from_user.id, plan_code=plan_code)
    await callback.answer()


@router.callback_query(SubscriptionState.selecting_duration, F.data.startswith("duration:select:"))
async def duration_selected_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
    settings: BotSettings,
) -> None:
    if callback.data is None:
        await state.clear()
        return

    parts = callback.data.split(":")
    if len(parts) < 4:
        await state.clear()
        return

    plan_code = parts[2]
    duration_days = int(parts[3])
    data = await state.get_data()
    plan_group = data.get("plan_group") or _find_plan_group(data.get("plan_catalog") or [], plan_code)
    if plan_group is None:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    duration = _find_duration_option(plan_group, duration_days)
    if duration is None:
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        await state.clear()
        return

    addons_catalog = await api_client.get_addons_catalog()
    supported_addons = _resolve_supported_addons(addons_catalog, plan_code)
    extra_device_limit = int((supported_addons.get("extra_device") or {}).get("max_quantity", 0))

    await state.update_data(
        plan_id=duration.get("plan_id"),
        duration_days=duration_days,
        plan_name=plan_group.get("display_name"),
        supported_addons=supported_addons,
        extra_device_qty=0,
    )

    if extra_device_limit > 0:
        await callback.message.edit_text(
            text=_addons_summary_text(
                plan_name=str(plan_group.get("display_name") or "Plan"),
                duration_days=duration_days,
                extra_device_qty=0,
                extra_device_limit=extra_device_limit,
            ),
            reply_markup=addons_keyboard(
                i18n,
                extra_device_qty=0,
                extra_device_limit=extra_device_limit,
            ),
        )
        await state.set_state(SubscriptionState.selecting_addons)
    else:
        await _render_payment_step(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            state=state,
            settings=settings,
        )

    logger.info(
        "duration_selected",
        user_id=callback.from_user.id,
        plan_code=plan_code,
        duration_days=duration_days,
        extra_device_limit=extra_device_limit,
    )
    await callback.answer()


@router.callback_query(SubscriptionState.selecting_addons, F.data.startswith("addon:"))
async def addon_selection_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
    settings: BotSettings,
) -> None:
    if callback.data is None:
        await state.clear()
        return

    data = await state.get_data()
    supported_addons = data.get("supported_addons") or {}
    extra_device_limit = int((supported_addons.get("extra_device") or {}).get("max_quantity", 0))
    extra_device_qty = int(data.get("extra_device_qty") or 0)
    plan_name = str(data.get("plan_name") or "Plan")
    duration_days = int(data.get("duration_days") or 0)

    if callback.data == "addon:continue":
        await _render_payment_step(
            callback=callback,
            i18n=i18n,
            api_client=api_client,
            state=state,
            settings=settings,
        )
        await callback.answer()
        return

    if callback.data == "addon:inc:extra_device" and extra_device_qty < extra_device_limit:
        extra_device_qty += 1
    if callback.data == "addon:dec:extra_device" and extra_device_qty > 0:
        extra_device_qty -= 1

    await state.update_data(extra_device_qty=extra_device_qty)
    await callback.message.edit_text(
        text=_addons_summary_text(
            plan_name=plan_name,
            duration_days=duration_days,
            extra_device_qty=extra_device_qty,
            extra_device_limit=extra_device_limit,
        ),
        reply_markup=addons_keyboard(
            i18n,
            extra_device_qty=extra_device_qty,
            extra_device_limit=extra_device_limit,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:back")
async def subscription_back_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    api_client: CyberVPNAPIClient,
    state: FSMContext,
) -> None:
    current_state = await state.get_state()

    try:
        if current_state == SubscriptionState.selecting_payment.state:
            data = await state.get_data()
            supported_addons = data.get("supported_addons") or {}
            extra_device_limit = int((supported_addons.get("extra_device") or {}).get("max_quantity", 0))
            if extra_device_limit > 0:
                await callback.message.edit_text(
                    text=_addons_summary_text(
                        plan_name=str(data.get("plan_name") or "Plan"),
                        duration_days=int(data.get("duration_days") or 0),
                        extra_device_qty=int(data.get("extra_device_qty") or 0),
                        extra_device_limit=extra_device_limit,
                    ),
                    reply_markup=addons_keyboard(
                        i18n,
                        extra_device_qty=int(data.get("extra_device_qty") or 0),
                        extra_device_limit=extra_device_limit,
                    ),
                )
                await state.set_state(SubscriptionState.selecting_addons)
                await callback.answer()
                return

            plan_group = data.get("plan_group")
            await callback.message.edit_text(
                text=i18n.get("subscription-select-duration"),
                reply_markup=duration_keyboard(i18n, plan=plan_group, durations=(plan_group or {}).get("durations")),
            )
            await state.set_state(SubscriptionState.selecting_duration)
            await callback.answer()
            return

        if current_state == SubscriptionState.selecting_addons.state:
            data = await state.get_data()
            plan_group = data.get("plan_group")
            await callback.message.edit_text(
                text=i18n.get("subscription-select-duration"),
                reply_markup=duration_keyboard(i18n, plan=plan_group, durations=(plan_group or {}).get("durations")),
            )
            await state.set_state(SubscriptionState.selecting_duration)
            await callback.answer()
            return

        if current_state == SubscriptionState.selecting_duration.state:
            data = await state.get_data()
            plan_catalog = data.get("plan_catalog")
            if not plan_catalog:
                plan_catalog = _group_plan_catalog(
                    [
                        plan
                        for plan in await api_client.get_plans()
                        if isinstance(plan, dict)
                        and str(plan.get("catalog_visibility") or "public") == "public"
                        and _is_telegram_sellable(plan)
                        and bool(plan.get("is_active", True))
                    ]
                )
                await state.update_data(plan_catalog=plan_catalog)

            await callback.message.edit_text(
                text=i18n.get("subscription-select-plan"),
                reply_markup=plans_keyboard(i18n, plan_catalog),
            )
            await state.set_state(SubscriptionState.selecting_plan)
            await callback.answer()
            return

    except Exception as exc:
        logger.error("subscription_back_error", user_id=callback.from_user.id, error=str(exc))
        await callback.answer(i18n.get("error-generic"), show_alert=True)
        return

    await state.clear()
    from src.keyboards.menu import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("menu-main-title"),
        reply_markup=main_menu_keyboard(i18n),
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:cancel")
async def cancel_subscription_handler(
    callback: CallbackQuery,
    i18n: I18nContext,
    state: FSMContext,
) -> None:
    await state.clear()

    from src.keyboards.menu import main_menu_keyboard

    await callback.message.edit_text(
        text=i18n.get("subscription-cancelled"),
        reply_markup=main_menu_keyboard(i18n),
    )

    logger.info("subscription_flow_cancelled", user_id=callback.from_user.id)
    await callback.answer()
