"""Create durable, idempotent renewal invoices for Remnawave numeric users."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from html import escape
from typing import Literal
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_mobile_user_ref,
)
from src.application.use_cases.payments.checkout import CheckoutUseCase
from src.application.use_cases.payments.commit_checkout import CommitCheckoutUseCase
from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.payments.cryptobot.client import CryptoBotClient
from src.infrastructure.remnawave.user_gateway import RemnawaveIdentityBindingError, RemnawaveUserGateway

_IDEMPOTENCY_KEY_RE = re.compile(r"^remnawave:auto-renew:(?P<user_id>[1-9][0-9]*):(?P<digest>[0-9a-f]{64})$")
_AUTO_RENEW_PAST_WINDOW = timedelta(hours=2)
_AUTO_RENEW_FUTURE_WINDOW = timedelta(hours=2)
_AUTO_RENEW_NOTIFICATION_PREFIX = "auto_renew:"


class RemnawaveAutoRenewError(RuntimeError):
    """Base class for safe transport mapping."""


class RemnawaveAutoRenewNotFoundError(RemnawaveAutoRenewError):
    pass


class RemnawaveAutoRenewConflictError(RemnawaveAutoRenewError):
    pass


class RemnawaveAutoRenewUpstreamUnavailableError(RemnawaveAutoRenewError):
    pass


@dataclass(frozen=True, slots=True)
class RemnawaveAutoRenewResult:
    payment_id: str
    reused: bool
    notification_status: Literal["queued", "already_queued"]


class CreateRemnawaveAutoRenewInvoiceUseCase:
    """Keep provider identity resolution and CyberVPN billing authority separate."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        crypto_client: CryptoBotClient,
        user_gateway: RemnawaveUserGateway,
    ) -> None:
        self._session = session
        self._crypto_client = crypto_client
        self._user_gateway = user_gateway

    async def execute(
        self,
        *,
        remnawave_user_id: int,
        expected_expire_at: datetime,
        idempotency_key: str,
    ) -> RemnawaveAutoRenewResult:
        expected_expire_at = _aware_utc(expected_expire_at)
        _validate_idempotency_key(
            idempotency_key,
            remnawave_user_id=remnawave_user_id,
            expected_expire_at=expected_expire_at,
        )
        customer = await self._resolve_customer(remnawave_user_id)
        user_ref = await self._require_reconciled(customer, remnawave_user_id)
        if (
            not settings.payment_autorenewal_enabled
            or not customer.subscription_auto_renew_enabled
            or not customer.is_active
        ):
            raise RemnawaveAutoRenewConflictError("Automatic renewal is not enabled for this customer")
        canonical_telegram_id = customer.telegram_id
        if (
            isinstance(canonical_telegram_id, bool)
            or not isinstance(canonical_telegram_id, int)
            or canonical_telegram_id <= 0
        ):
            raise RemnawaveAutoRenewConflictError("A canonical Telegram recipient is required for auto-renewal")
        await self._require_current_upstream_expiry(
            user_ref=user_ref,
            expected_expire_at=expected_expire_at,
        )
        previous_payment = await self._latest_completed_plan_payment(customer.id)
        if previous_payment is None or previous_payment.plan_id is None:
            raise RemnawaveAutoRenewNotFoundError("No completed CyberVPN plan payment is available for renewal")
        if previous_payment.subscription_days <= 0:
            raise RemnawaveAutoRenewConflictError("The current plan is not renewable")

        channel = str((previous_payment.metadata_ or {}).get("channel") or "web")
        quote = await CheckoutUseCase(self._session).execute(
            customer.id,
            previous_payment.plan_id,
            currency=previous_payment.currency,
            use_wallet=Decimal("0"),
            sale_channel=channel,
        )
        provider_payload = f"cybervpn:auto-renew:v1:{remnawave_user_id}:{_expiry_digest(expected_expire_at)}"
        committed = await CommitCheckoutUseCase(self._session, self._crypto_client).execute(
            user_id=customer.id,
            quote_result=quote,
            currency=previous_payment.currency,
            channel=channel,
            description=f"CyberVPN auto-renewal: {quote.plan_name or 'plan'}",
            payload=provider_payload,
            checkout_mode="auto_renew",
            payment_plan_id=previous_payment.plan_id,
            metadata_extra={
                "remnawave_user_id": remnawave_user_id,
                "expected_expire_at": _canonical_expiry(expected_expire_at),
                "auto_renew_source": "remnawave_worker",
            },
            idempotency_key=idempotency_key,
            reconcile_provider_by_payload=True,
        )
        if committed.invoice is None or not committed.invoice.payment_url:
            raise RemnawaveAutoRenewUpstreamUnavailableError("Renewal invoice has no payment URL")
        payment_url = _validate_payment_url(committed.invoice.payment_url)
        notification_status = await self._queue_notification_once(
            customer=customer,
            telegram_id=canonical_telegram_id,
            payment=committed.payment,
            expected_expire_at=expected_expire_at,
            amount=str(committed.invoice.amount),
            currency=committed.invoice.currency,
            payment_url=payment_url,
        )
        await self._session.commit()
        return RemnawaveAutoRenewResult(
            payment_id=str(committed.payment.id),
            reused=committed.reused,
            notification_status=notification_status,
        )

    async def _resolve_customer(self, remnawave_user_id: int) -> MobileUserModel:
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.remnawave_user_id == remnawave_user_id)
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise RemnawaveAutoRenewNotFoundError("Remnawave numeric user is not mapped to a customer")
        return customer

    async def _require_reconciled(
        self,
        customer: MobileUserModel,
        remnawave_user_id: int,
    ) -> RemnawaveUserRef:
        try:
            user_ref = await resolve_exact_mapped_mobile_user_ref(self._session, customer)
        except RemnawaveIdentityAccessConflict as exc:
            raise RemnawaveAutoRenewConflictError("Remnawave numeric identity reconciliation is incomplete") from exc
        if user_ref is None or user_ref.require_numeric_id() != remnawave_user_id:
            raise RemnawaveAutoRenewConflictError("Remnawave numeric identity reconciliation is incomplete")
        return user_ref

    async def _require_current_upstream_expiry(
        self,
        *,
        user_ref: RemnawaveUserRef,
        expected_expire_at: datetime,
    ) -> None:
        remnawave_user_id = user_ref.require_numeric_id()
        try:
            user = await self._user_gateway.get_by_ref(user_ref)
        except RemnawaveIdentityBindingError as exc:
            raise RemnawaveAutoRenewConflictError(
                "Remnawave upstream identity does not match the reconciled user"
            ) from exc
        if user is None:
            raise RemnawaveAutoRenewUpstreamUnavailableError("Remnawave user could not be verified")
        upstream_numeric_id = getattr(user, "remnawave_id", None)
        if (
            isinstance(upstream_numeric_id, bool)
            or not isinstance(upstream_numeric_id, int)
            or upstream_numeric_id <= 0
            or upstream_numeric_id != remnawave_user_id
        ):
            raise RemnawaveAutoRenewConflictError(
                "Remnawave upstream identity does not match the reconciled numeric user"
            )
        if user.expires_at is None:
            raise RemnawaveAutoRenewConflictError("Remnawave user has no renewable expiry")
        actual_expire_at = _aware_utc(user.expires_at)
        if abs((actual_expire_at - expected_expire_at).total_seconds()) > 1:
            raise RemnawaveAutoRenewConflictError("Remnawave expiry changed after the renewal scan")
        now = _utc_now()
        if actual_expire_at < now - _AUTO_RENEW_PAST_WINDOW or actual_expire_at > now + _AUTO_RENEW_FUTURE_WINDOW:
            raise RemnawaveAutoRenewConflictError("Remnawave user is not within the renewal window")

    async def _queue_notification_once(
        self,
        *,
        customer: MobileUserModel,
        telegram_id: int,
        payment: PaymentModel,
        expected_expire_at: datetime,
        amount: str,
        currency: str,
        payment_url: str,
    ) -> Literal["queued", "already_queued"]:
        """Persist one canonical-recipient delivery intent per payment/expiry.

        The checkout advisory lock serializes the shared idempotency key on
        PostgreSQL.  A deterministic queue id and a marker stored on the
        payment keep scheduler replays from recreating a notification even
        after the delivered queue row is later removed by retention.
        """

        queue_id = uuid5(
            NAMESPACE_URL,
            f"cybervpn:auto-renew-notification/v1:{payment.id}:{_canonical_expiry(expected_expire_at)}",
        )
        metadata = dict(payment.metadata_ or {})
        marker = metadata.get("auto_renew_notification")
        if marker is not None:
            if not isinstance(marker, dict):
                raise RemnawaveAutoRenewConflictError("Auto-renew notification receipt is invalid")
            try:
                marker_queue_id = UUID(str(marker.get("queue_id")))
            except (TypeError, ValueError, AttributeError) as exc:
                raise RemnawaveAutoRenewConflictError("Auto-renew notification receipt is invalid") from exc
            if marker_queue_id != queue_id or marker.get("expected_expire_at") != _canonical_expiry(expected_expire_at):
                raise RemnawaveAutoRenewConflictError("Auto-renew notification receipt conflicts with this expiry")
            return "already_queued"

        existing = await self._session.get(NotificationQueue, queue_id)
        notification_status: Literal["queued", "already_queued"] = "already_queued"
        if existing is None:
            display_name = customer.username or customer.telegram_username or "customer"
            self._session.add(
                NotificationQueue(
                    id=queue_id,
                    telegram_id=telegram_id,
                    message=_render_auto_renew_notification(
                        display_name=display_name,
                        amount=amount,
                        currency=currency,
                        payment_url=payment_url,
                    ),
                    # Bind delivery to the canonical backend customer. The worker
                    # revalidates this subject-to-Telegram binding immediately
                    # before sending so a reassigned chat cannot receive a stale
                    # payment link.
                    notification_type=f"{_AUTO_RENEW_NOTIFICATION_PREFIX}{customer.id}",
                    scheduled_at=_utc_now(),
                )
            )
            notification_status = "queued"

        metadata["auto_renew_notification"] = {
            "version": 1,
            "queue_id": str(queue_id),
            "expected_expire_at": _canonical_expiry(expected_expire_at),
        }
        payment.metadata_ = metadata
        await self._session.flush()
        return notification_status

    async def _latest_completed_plan_payment(self, customer_id) -> PaymentModel | None:
        result = await self._session.execute(
            select(PaymentModel)
            .where(
                PaymentModel.user_uuid == customer_id,
                PaymentModel.status == "completed",
                PaymentModel.plan_id.is_not(None),
            )
            .order_by(PaymentModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


def _canonical_expiry(value: datetime) -> str:
    return _aware_utc(value).isoformat().replace("+00:00", "Z")


def _expiry_digest(value: datetime) -> str:
    return hashlib.sha256(_canonical_expiry(value).encode()).hexdigest()


def _validate_idempotency_key(
    value: str,
    *,
    remnawave_user_id: int,
    expected_expire_at: datetime,
) -> None:
    match = _IDEMPOTENCY_KEY_RE.fullmatch(value.strip())
    if match is None or int(match.group("user_id")) != remnawave_user_id:
        raise ValueError("Invalid auto-renew Idempotency-Key")
    if not hmac.compare_digest(match.group("digest"), _expiry_digest(expected_expire_at)):
        raise ValueError("Auto-renew Idempotency-Key does not match expected_expire_at")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("expected_expire_at must include timezone")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_payment_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if (
        not normalized
        or len(normalized) > 2000
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise RemnawaveAutoRenewUpstreamUnavailableError("Renewal invoice has an unsafe payment URL")
    return normalized


def _render_auto_renew_notification(
    *,
    display_name: str,
    amount: str,
    currency: str,
    payment_url: str,
) -> str:
    return (
        "💳 <b>Auto-Renewal Invoice</b>\n\n"
        f"User: <code>{escape(display_name, quote=True)}</code>\n"
        f"Amount: <b>{escape(amount, quote=True)} {escape(currency, quote=True)}</b>\n\n"
        f'<a href="{escape(payment_url, quote=True)}">Pay now</a> to continue your subscription.'
    )
