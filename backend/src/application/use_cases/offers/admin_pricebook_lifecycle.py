from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.commercial_context import (
    COUNTRY_CURRENCY_DEFAULTS,
    normalize_country_code,
    normalize_currency_code,
)
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.metrics import (
    commerce_pricebook_lifecycle_total,
    commerce_pricebook_validation_issues_current,
)

COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY = "commercial_context.options"
COMMERCIAL_CONTEXT_OPTIONS_DESCRIPTION = "Admin-managed country and currency options for commercial catalog context."

PRICEBOOK_AUDIT_RESOURCE_TYPE = "pricebook"
PRICEBOOK_UPDATED_ACTION = "commercial.pricebook.updated"
PRICEBOOK_PUBLISHED_ACTION = "commercial.pricebook.published"
PRICEBOOK_SCHEDULED_ACTION = "commercial.pricebook.scheduled"
PRICEBOOK_ROLLED_BACK_ACTION = "commercial.pricebook.rolled_back"
COMMERCIAL_CONTEXT_OPTIONS_UPDATED_ACTION = "commercial.context_options.updated"


@dataclass(frozen=True)
class PricebookValidationIssue:
    code: str
    severity: str
    message: str
    field: str | None = None
    entry_id: UUID | None = None
    offer_id: UUID | None = None
    remediation: str | None = None


@dataclass(frozen=True)
class PricebookLifecycleResult:
    pricebook: PricebookModel
    action: str
    previous: dict[str, Any]
    current: dict[str, Any]


class AdminPricebookLifecycleUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PricebookRepository(session)

    async def list_pricebooks(
        self,
        *,
        include_inactive: bool = True,
        storefront_id: UUID | None = None,
        storefront_key: str | None = None,
        currency_code: str | None = None,
        region_code: str | None = None,
    ) -> list[PricebookModel]:
        return await self._repo.list_active(
            include_inactive=include_inactive,
            storefront_id=storefront_id,
            storefront_key=storefront_key,
            currency_code=currency_code,
            region_code=region_code,
        )

    async def get_pricebook(self, pricebook_id: UUID) -> PricebookModel:
        pricebook = await self._repo.get_by_id(pricebook_id)
        if pricebook is None:
            raise ValueError("Pricebook not found")
        return pricebook

    async def update_pricebook(self, pricebook_id: UUID, payload: dict[str, Any]) -> PricebookLifecycleResult:
        try:
            pricebook = await self.get_pricebook(pricebook_id)
            previous = snapshot_pricebook(pricebook)
            entries = payload.pop("entries", None)

            for field_name, value in payload.items():
                if field_name == "currency_code" and value is not None:
                    value = normalize_currency_code(value)
                elif field_name == "region_code" and value is not None:
                    value = normalize_country_code(value)
                elif isinstance(value, str):
                    value = value.strip()
                setattr(pricebook, field_name, value)

            if entries is not None:
                await self._replace_entries(pricebook, entries)

            _validate_effective_window(pricebook.effective_from, pricebook.effective_to)
            updated = await self._repo.update(pricebook)
        except Exception:
            _record_pricebook_lifecycle(action="update", status="failure")
            raise

        _record_pricebook_lifecycle(action="update", status="success")
        return PricebookLifecycleResult(
            pricebook=updated,
            action=PRICEBOOK_UPDATED_ACTION,
            previous=previous,
            current=snapshot_pricebook(updated),
        )

    async def publish_pricebook(
        self,
        pricebook_id: UUID,
        *,
        effective_from: datetime | None = None,
    ) -> PricebookLifecycleResult:
        try:
            pricebook = await self.get_pricebook(pricebook_id)
            previous = snapshot_pricebook(pricebook)
            publish_at = effective_from or datetime.now(UTC)
            await self._close_overlapping_versions(pricebook, close_at=publish_at)
            pricebook.version_status = "active"
            pricebook.is_active = True
            pricebook.effective_from = publish_at
            pricebook.effective_to = None
            updated = await self._repo.update(pricebook)
        except Exception:
            _record_pricebook_lifecycle(action="publish", status="failure")
            raise

        _record_pricebook_lifecycle(action="publish", status="success")
        return PricebookLifecycleResult(
            pricebook=updated,
            action=PRICEBOOK_PUBLISHED_ACTION,
            previous=previous,
            current=snapshot_pricebook(updated),
        )

    async def schedule_pricebook(self, pricebook_id: UUID, *, scheduled_for: datetime) -> PricebookLifecycleResult:
        try:
            pricebook = await self.get_pricebook(pricebook_id)
            previous = snapshot_pricebook(pricebook)
            if scheduled_for <= datetime.now(UTC):
                raise ValueError("scheduled_for must be in the future")
            await self._close_overlapping_versions(pricebook, close_at=scheduled_for)
            pricebook.version_status = "active"
            pricebook.is_active = True
            pricebook.effective_from = scheduled_for
            pricebook.effective_to = None
            updated = await self._repo.update(pricebook)
        except Exception:
            _record_pricebook_lifecycle(action="schedule", status="failure")
            raise

        _record_pricebook_lifecycle(action="schedule", status="success")
        return PricebookLifecycleResult(
            pricebook=updated,
            action=PRICEBOOK_SCHEDULED_ACTION,
            previous=previous,
            current=snapshot_pricebook(updated),
        )

    async def rollback_pricebook(
        self,
        pricebook_id: UUID,
        *,
        target_pricebook_id: UUID | None = None,
    ) -> PricebookLifecycleResult:
        try:
            current = await self.get_pricebook(pricebook_id)
            target = await self.get_pricebook(target_pricebook_id) if target_pricebook_id is not None else None
            if target is None:
                target = await self._latest_previous_version(current)
            if target is None:
                raise ValueError("No previous pricebook version is available for rollback")

            previous = snapshot_pricebook(current)
            rollback_at = datetime.now(UTC)
            await self._close_overlapping_versions(current, close_at=rollback_at)
            clone = PricebookModel(
                pricebook_key=current.pricebook_key,
                display_name=f"Rollback to {target.display_name}",
                storefront_id=current.storefront_id,
                merchant_profile_id=target.merchant_profile_id,
                currency_code=target.currency_code,
                region_code=target.region_code,
                discount_rules=dict(target.discount_rules or {}),
                renewal_pricing_policy=dict(target.renewal_pricing_policy or {}),
                version_status="active",
                effective_from=rollback_at,
                effective_to=None,
                is_active=True,
                entries=[
                    PricebookEntryModel(
                        offer_id=entry.offer_id,
                        visible_price=entry.visible_price,
                        compare_at_price=entry.compare_at_price,
                        included_addon_codes=list(entry.included_addon_codes or []),
                        display_order=entry.display_order,
                    )
                    for entry in target.entries
                ],
            )
            created = await self._repo.create(clone)
        except Exception:
            _record_pricebook_lifecycle(action="rollback", status="failure")
            raise

        _record_pricebook_lifecycle(action="rollback", status="success")
        return PricebookLifecycleResult(
            pricebook=created,
            action=PRICEBOOK_ROLLED_BACK_ACTION,
            previous=previous,
            current={**snapshot_pricebook(created), "rollback_target_pricebook_id": str(target.id)},
        )

    async def list_history(self, pricebook_key: str) -> list[PricebookModel]:
        return await self._repo.list_versions_by_key(pricebook_key)

    async def validate_pricebook(self, pricebook_id: UUID) -> list[PricebookValidationIssue]:
        pricebook = await self.get_pricebook(pricebook_id)
        issues: list[PricebookValidationIssue] = []
        context_options = await AdminCommercialContextOptionsUseCase(self._session).get_options()
        supported_currencies = {
            option["currency_code"] for option in context_options["currencies"] if option.get("is_enabled", True)
        }

        if normalize_currency_code(pricebook.currency_code) not in supported_currencies:
            issues.append(
                PricebookValidationIssue(
                    code="unsupported_currency",
                    severity="error",
                    field="currency_code",
                    message=f"Currency {pricebook.currency_code} is not enabled in commercial context options.",
                    remediation="Add the currency to commercial context options or change the pricebook currency.",
                )
            )

        if not pricebook.entries:
            issues.append(
                PricebookValidationIssue(
                    code="missing_price",
                    severity="error",
                    field="entries",
                    message="Pricebook must contain at least one priced offer entry.",
                    remediation="Add at least one entry with a positive visible_price.",
                )
            )

        addon_codes = {code for entry in pricebook.entries for code in (entry.included_addon_codes or [])}
        addons = await self._addons_by_code(addon_codes)
        active_channels = await self._active_provisioning_channels()

        for entry in pricebook.entries:
            offer = entry.offer
            if not _positive_money(entry.visible_price):
                issues.append(
                    PricebookValidationIssue(
                        code="missing_price",
                        severity="error",
                        field="visible_price",
                        entry_id=entry.id,
                        offer_id=entry.offer_id,
                        message="Entry visible_price must be positive before publish.",
                        remediation="Set a non-zero visible_price for this offer entry.",
                    )
                )
            if offer is None:
                continue

            plan = await self._session.get(SubscriptionPlanModel, offer.subscription_plan_id)
            if plan is None:
                issues.append(
                    PricebookValidationIssue(
                        code="missing_provisioning_profile",
                        severity="error",
                        entry_id=entry.id,
                        offer_id=entry.offer_id,
                        message="Offer subscription plan could not be resolved for provisioning validation.",
                        remediation="Attach the offer to a valid subscription plan.",
                    )
                )
                continue

            plan_channels = set(plan.sale_channels or [])
            if not plan.server_pool or not plan.connection_modes or (
                active_channels and plan_channels.isdisjoint(active_channels)
            ):
                issues.append(
                    PricebookValidationIssue(
                        code="missing_provisioning_profile",
                        severity="warning",
                        entry_id=entry.id,
                        offer_id=entry.offer_id,
                        message="Plan has no active provisioning profile coverage for its sale channels.",
                        remediation=(
                            "Confirm service identity provisioning profiles cover the sale channels before publish."
                        ),
                    )
                )

            for addon_code in entry.included_addon_codes or []:
                addon = addons.get(addon_code)
                if addon is None or not addon.is_active:
                    issues.append(
                        PricebookValidationIssue(
                            code="incompatible_addon",
                            severity="error",
                            field="included_addon_codes",
                            entry_id=entry.id,
                            offer_id=entry.offer_id,
                            message=f"Add-on {addon_code} is not active or does not exist.",
                            remediation="Remove the add-on or activate a matching plan add-on.",
                        )
                    )
                    continue
                addon_channels = set(addon.sale_channels or [])
                offer_channels = set(offer.sale_channels or [])
                if addon_channels and offer_channels and addon_channels.isdisjoint(offer_channels):
                    issues.append(
                        PricebookValidationIssue(
                            code="incompatible_addon",
                            severity="error",
                            field="included_addon_codes",
                            entry_id=entry.id,
                            offer_id=entry.offer_id,
                            message=f"Add-on {addon_code} is not available on the offer sale channels.",
                            remediation="Align offer and add-on sale_channels or remove the add-on from the entry.",
                        )
                    )
                max_by_plan = dict(addon.max_quantity_by_plan or {})
                if plan.plan_code and max_by_plan and int(max_by_plan.get(plan.plan_code, 0)) <= 0:
                    issues.append(
                        PricebookValidationIssue(
                            code="incompatible_addon",
                            severity="error",
                            field="included_addon_codes",
                            entry_id=entry.id,
                            offer_id=entry.offer_id,
                            message=f"Add-on {addon_code} is not allowed for plan {plan.plan_code}.",
                            remediation="Update max_quantity_by_plan or remove the add-on from this pricebook entry.",
                        )
                    )

        _record_pricebook_validation_metrics(issues)
        _record_pricebook_lifecycle(action="validate", status="success")
        return issues

    async def _replace_entries(self, pricebook: PricebookModel, entries: list[dict[str, Any]]) -> None:
        offer_ids = [entry["offer_id"] for entry in entries]
        if len(set(offer_ids)) != len(offer_ids):
            raise ValueError("Pricebook cannot contain duplicate offer entries")
        result = await self._session.execute(select(OfferModel.id).where(OfferModel.id.in_(offer_ids)))
        existing_offer_ids = {row[0] for row in result.all()}
        missing_offer_ids = set(offer_ids) - existing_offer_ids
        if missing_offer_ids:
            raise ValueError("One or more pricebook offers do not exist")
        pricebook.entries = [
            PricebookEntryModel(
                offer_id=entry["offer_id"],
                visible_price=entry["visible_price"],
                compare_at_price=entry.get("compare_at_price"),
                included_addon_codes=list(entry.get("included_addon_codes", [])),
                display_order=entry.get("display_order", 0),
            )
            for entry in entries
        ]

    async def _close_overlapping_versions(self, pricebook: PricebookModel, *, close_at: datetime) -> None:
        peers = await self._repo.list_peer_versions(pricebook)
        for peer in peers:
            if peer.id == pricebook.id:
                continue
            if not peer.is_active or peer.version_status != "active":
                continue
            if peer.effective_from >= close_at:
                continue
            if peer.effective_to is None or peer.effective_to > close_at:
                peer.effective_to = close_at
        await self._session.flush()

    async def _latest_previous_version(self, current: PricebookModel) -> PricebookModel | None:
        for candidate in await self._repo.list_peer_versions(current):
            if candidate.id != current.id:
                return candidate
        return None

    async def _addons_by_code(self, addon_codes: set[str]) -> dict[str, PlanAddonModel]:
        if not addon_codes:
            return {}
        result = await self._session.execute(select(PlanAddonModel).where(PlanAddonModel.code.in_(addon_codes)))
        return {addon.code: addon for addon in result.scalars().all()}

    async def _active_provisioning_channels(self) -> set[str]:
        result = await self._session.execute(
            select(ProvisioningProfileModel.target_channel).where(ProvisioningProfileModel.profile_status == "active")
        )
        return {channel for channel in result.scalars().all() if channel}


class AdminCommercialContextOptionsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SystemConfigRepository(session)

    async def get_options(self) -> dict[str, Any]:
        configured = await self._repo.get_value(COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY)
        if configured:
            return _normalize_context_options(configured)
        currencies = sorted(set(COUNTRY_CURRENCY_DEFAULTS.values()) | {"USD"})
        return _normalize_context_options(
            {
                "countries": [
                    {
                        "country_code": country_code,
                        "default_currency_code": currency_code,
                        "supported_currency_codes": [currency_code, "USD"],
                        "payment_country_code": country_code,
                        "is_enabled": True,
                    }
                    for country_code, currency_code in sorted(COUNTRY_CURRENCY_DEFAULTS.items())
                ],
                "currencies": [
                    {
                        "currency_code": currency_code,
                        "minor_units": 0 if currency_code in {"JPY", "KRW", "VND"} else 2,
                        "is_enabled": True,
                    }
                    for currency_code in currencies
                ],
            }
        )

    async def update_options(
        self,
        payload: dict[str, Any],
        *,
        updated_by: UUID,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        previous = await self.get_options()
        normalized = _normalize_context_options(payload)
        await self._repo.set(
            COMMERCIAL_CONTEXT_OPTIONS_CONFIG_KEY,
            normalized,
            updated_by=updated_by,
            description=COMMERCIAL_CONTEXT_OPTIONS_DESCRIPTION,
        )
        return previous, normalized


def snapshot_pricebook(pricebook: PricebookModel) -> dict[str, Any]:
    return {
        "id": str(pricebook.id),
        "pricebook_key": pricebook.pricebook_key,
        "display_name": pricebook.display_name,
        "storefront_id": str(pricebook.storefront_id),
        "merchant_profile_id": str(pricebook.merchant_profile_id) if pricebook.merchant_profile_id else None,
        "currency_code": pricebook.currency_code,
        "region_code": pricebook.region_code,
        "version_status": pricebook.version_status,
        "effective_from": pricebook.effective_from.isoformat(),
        "effective_to": pricebook.effective_to.isoformat() if pricebook.effective_to else None,
        "is_active": pricebook.is_active,
        "entry_count": len(pricebook.entries or []),
    }


def pricebook_lifecycle_status(pricebook: PricebookModel, *, now: datetime | None = None) -> str:
    current_time = now or datetime.now(UTC)
    if pricebook.version_status == "active" and pricebook.is_active and pricebook.effective_from > current_time:
        return "scheduled"
    if (
        pricebook.version_status == "active"
        and pricebook.is_active
        and pricebook.effective_from <= current_time
        and (pricebook.effective_to is None or pricebook.effective_to > current_time)
    ):
        return "published"
    if pricebook.effective_to is not None and pricebook.effective_to <= current_time:
        return "superseded"
    return str(pricebook.version_status)


def _normalize_context_options(payload: dict[str, Any]) -> dict[str, Any]:
    countries: list[dict[str, Any]] = []
    currencies: list[dict[str, Any]] = []
    currency_codes: set[str] = set()

    for raw_currency in payload.get("currencies", []):
        currency_code = normalize_currency_code(raw_currency.get("currency_code"))
        currency_codes.add(currency_code)
        currencies.append(
            {
                "currency_code": currency_code,
                "minor_units": int(raw_currency.get("minor_units", 2)),
                "is_enabled": bool(raw_currency.get("is_enabled", True)),
            }
        )

    for raw_country in payload.get("countries", []):
        country_code = normalize_country_code(raw_country.get("country_code"))
        default_currency = normalize_currency_code(raw_country.get("default_currency_code"))
        raw_supported = raw_country.get("supported_currency_codes", [default_currency])
        supported = tuple(dict.fromkeys(normalize_currency_code(code) for code in raw_supported))
        if default_currency not in supported:
            raise ValueError("default_currency_code must be included in supported_currency_codes")
        currency_codes.update(supported)
        countries.append(
            {
                "country_code": country_code,
                "default_currency_code": default_currency,
                "supported_currency_codes": list(supported),
                "payment_country_code": normalize_country_code(raw_country.get("payment_country_code") or country_code),
                "is_enabled": bool(raw_country.get("is_enabled", True)),
            }
        )

    if not countries:
        raise ValueError("At least one country option is required")
    if not currencies:
        currencies = [
            {
                "currency_code": currency_code,
                "minor_units": 0 if currency_code in {"JPY", "KRW", "VND"} else 2,
                "is_enabled": True,
            }
            for currency_code in sorted(currency_codes or {"USD"})
        ]
    enabled_currency_codes = {currency["currency_code"] for currency in currencies if currency["is_enabled"]}
    missing_currency_codes = currency_codes - {currency["currency_code"] for currency in currencies}
    if missing_currency_codes:
        currencies.extend(
            {
                "currency_code": currency_code,
                "minor_units": 0 if currency_code in {"JPY", "KRW", "VND"} else 2,
                "is_enabled": True,
            }
            for currency_code in sorted(missing_currency_codes)
        )
        enabled_currency_codes.update(missing_currency_codes)
    if not enabled_currency_codes:
        raise ValueError("At least one currency option must be enabled")

    return {
        "countries": sorted(countries, key=lambda item: item["country_code"]),
        "currencies": sorted(currencies, key=lambda item: item["currency_code"]),
    }


def _validate_effective_window(effective_from: datetime, effective_to: datetime | None) -> None:
    if effective_to is not None and effective_to <= effective_from:
        raise ValueError("Pricebook effective_to must be greater than effective_from")


def _record_pricebook_lifecycle(*, action: str, status: str) -> None:
    commerce_pricebook_lifecycle_total.labels(action=action, status=status).inc()


def _record_pricebook_validation_metrics(issues: list[PricebookValidationIssue]) -> None:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = issue.severity if issue.severity in counts else "info"
        counts[severity] += 1
    for severity, count in counts.items():
        commerce_pricebook_validation_issues_current.labels(severity=severity).set(count)


def _positive_money(value: Any) -> bool:
    if value is None:
        return False
    try:
        return Decimal(str(value)) > 0
    except (InvalidOperation, ValueError):
        return False
