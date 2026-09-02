from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from src.application.services.auth_service import AuthService
from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.device_credential_model import DeviceCredentialModel
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.promo_code_model import PromoCodeModel
from src.infrastructure.database.models.provisioning_profile_model import ProvisioningProfileModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.models.wallet_model import WalletModel, WalletTransactionModel

SAFE_CLIENT_PASSWORD = "SafeClientFixture123!"
SAFE_MINIAPP_BOT_TOKEN = "safe-client-fixture-bot-token"
SAFE_CLIENT_SUBSCRIPTION_URL = "https://fixtures.cybervpn.test/sub/safe-client-active"


@dataclass(frozen=True)
class SafeClientAccount:
    user_id: uuid.UUID
    email: str
    state: str
    telegram_id: int | None = None
    referral_code: str | None = None
    subscription_key: str | None = None
    entitlement_grant_id: uuid.UUID | None = None
    service_identity_id: uuid.UUID | None = None
    device_subject_key: str | None = None
    remnawave_user_id: int | None = None
    remnawave_uuid: uuid.UUID | None = None


@dataclass(frozen=True)
class SafeClientFixturePack:
    auth_realm_id: uuid.UUID
    auth_realm_key: str
    auth_realm_audience: str
    active: SafeClientAccount
    trial: SafeClientAccount
    expired: SafeClientAccount
    no_subscription: SafeClientAccount
    referral_owner: SafeClientAccount
    partner_owner: SafeClientAccount
    promo_code: str
    partner_code: str
    subscription_url: str
    miniapp_init_data: str


def make_safe_customer_headers(
    auth_service: AuthService,
    pack: SafeClientFixturePack,
    account: SafeClientAccount,
) -> dict[str, str]:
    token, _, _ = auth_service.create_access_token(
        str(account.user_id),
        "customer",
        audience=pack.auth_realm_audience,
        principal_type="customer",
        realm_id=str(pack.auth_realm_id),
        realm_key=pack.auth_realm_key,
        scope_family="customer",
    )
    return {"Authorization": f"Bearer {token}", "X-Auth-Realm": pack.auth_realm_key}


async def seed_safe_client_fixture_pack(sessionmaker, auth_service: AuthService) -> SafeClientFixturePack:
    now = datetime.now(UTC)
    realm_id = uuid.uuid4()
    active_user_id = uuid.uuid4()
    trial_user_id = uuid.uuid4()
    expired_user_id = uuid.uuid4()
    no_subscription_user_id = uuid.uuid4()
    referral_owner_id = uuid.uuid4()
    partner_owner_id = uuid.uuid4()
    partner_account_id = uuid.uuid4()
    active_service_identity_id = uuid.uuid4()
    active_grant_id = uuid.uuid4()
    active_subscription_key = f"grant:{active_grant_id}"
    provisioning_profile_id = uuid.uuid4()
    device_credential_id = uuid.uuid4()
    wallet_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    provider_subject_ref = uuid.uuid4()
    provider_numeric_subject_id = 990_001

    miniapp_init_data = build_safe_miniapp_init_data(
        telegram_user_id=990001,
        username="safe_client_active",
        auth_date=1_803_984_000,
    )

    customer_realm = AuthRealmModel(
        id=realm_id,
        realm_key="customer",
        realm_type="customer",
        display_name="Safe Client Fixture Realm",
        audience="cybervpn:safe-client-fixture",
        cookie_namespace="safe_client_fixture",
        status="active",
        is_default=True,
    )

    active_user = MobileUserModel(
        id=active_user_id,
        auth_realm_id=realm_id,
        email="safe-active@example.test",
        username="safe_client_active",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        telegram_id=990001,
        telegram_username="safe_client_active",
        remnawave_user_id=provider_numeric_subject_id,
        remnawave_uuid=str(provider_subject_ref),
        referral_code="SAFEACT",
        is_active=True,
        status="active",
    )
    trial_user = MobileUserModel(
        id=trial_user_id,
        auth_realm_id=realm_id,
        email="safe-trial@example.test",
        username="safe_client_trial",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        telegram_id=990002,
        telegram_username="safe_client_trial",
        trial_activated_at=now - timedelta(days=1),
        trial_expires_at=now + timedelta(days=6),
        is_active=True,
        status="active",
    )
    expired_user = MobileUserModel(
        id=expired_user_id,
        auth_realm_id=realm_id,
        email="safe-expired@example.test",
        username="safe_client_expired",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        telegram_id=990003,
        telegram_username="safe_client_expired",
        is_active=True,
        status="active",
    )
    no_subscription_user = MobileUserModel(
        id=no_subscription_user_id,
        auth_realm_id=realm_id,
        email="safe-no-subscription@example.test",
        username="safe_client_empty",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        telegram_id=990004,
        telegram_username="safe_client_empty",
        is_active=True,
        status="active",
    )
    referral_owner = MobileUserModel(
        id=referral_owner_id,
        auth_realm_id=realm_id,
        email="safe-referral-owner@example.test",
        username="safe_referral_owner",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        referral_code="SAFEREF",
        is_active=True,
        status="active",
    )
    partner_owner = MobileUserModel(
        id=partner_owner_id,
        auth_realm_id=realm_id,
        email="safe-partner-owner@example.test",
        username="safe_partner_owner",
        password_hash=await auth_service.hash_password(SAFE_CLIENT_PASSWORD),
        is_partner=True,
        is_active=True,
        status="active",
    )

    partner_account = PartnerAccountModel(
        id=partner_account_id,
        account_key="safe-client-partner",
        display_name="Safe Client Partner",
        status="active",
        legacy_owner_user_id=partner_owner_id,
    )
    partner_code = PartnerCodeModel(
        id=uuid.uuid4(),
        code="SAFEPARTNER",
        partner_account_id=partner_account_id,
        partner_user_id=partner_owner_id,
        markup_pct=Decimal("0.00"),
        is_active=True,
    )
    promo = PromoCodeModel(
        id=uuid.uuid4(),
        code="SAFEPROMO10",
        discount_type="percent",
        discount_value=Decimal("10.00"),
        currency="USD",
        max_uses=100,
        current_uses=0,
        is_single_use=False,
        min_amount=Decimal("10.00"),
        expires_at=None,
        is_active=True,
        description="Synthetic client fixture promo only.",
    )

    active_service_identity = ServiceIdentityModel(
        id=active_service_identity_id,
        service_key="safe-client-active-subscription",
        customer_account_id=active_user_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key=active_subscription_key,
        provider_subject_ref=str(provider_subject_ref),
        provider_numeric_subject_id=provider_numeric_subject_id,
        identity_status="active",
        service_context={
            "fixture": "safe_client_pack",
            "subscription_key": active_subscription_key,
            "subscription_url": SAFE_CLIENT_SUBSCRIPTION_URL,
        },
    )
    active_profile = ProvisioningProfileModel(
        id=provisioning_profile_id,
        service_identity_id=active_service_identity_id,
        profile_key="shared_client-default",
        target_channel="shared_client",
        delivery_method="subscription_url",
        profile_status="active",
        provider_name="remnawave",
        provider_profile_ref="safe-client-profile",
        provisioning_payload={"fixture": "safe_client_pack", "secret_material": False},
    )
    active_grant = EntitlementGrantModel(
        id=active_grant_id,
        grant_key="safe-client-active-grant",
        service_identity_id=active_service_identity_id,
        customer_account_id=active_user_id,
        auth_realm_id=realm_id,
        source_type="manual",
        manual_source_key="safe-client-active-manual-source",
        grant_status="active",
        grant_snapshot=_grant_snapshot(
            status="active",
            plan_code="pro",
            display_name="Safe Pro 30D",
            plan_uuid=uuid.uuid4(),
            expires_at=now + timedelta(days=30),
            is_trial=False,
            device_limit=5,
        ),
        source_snapshot={"fixture": "safe_client_pack"},
        effective_from=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
        activated_at=now - timedelta(days=1),
    )
    expired_service_identity = ServiceIdentityModel(
        id=uuid.uuid4(),
        service_key="safe-client-expired-subscription",
        customer_account_id=expired_user_id,
        auth_realm_id=realm_id,
        provider_name="remnawave",
        identity_scope="subscription",
        subscription_key=None,
        provider_subject_ref=str(uuid.uuid4()),
        identity_status="active",
        service_context={"fixture": "safe_client_pack"},
    )
    expired_grant = EntitlementGrantModel(
        id=uuid.uuid4(),
        grant_key="safe-client-expired-grant",
        service_identity_id=expired_service_identity.id,
        customer_account_id=expired_user_id,
        auth_realm_id=realm_id,
        source_type="manual",
        manual_source_key="safe-client-expired-manual-source",
        grant_status="active",
        grant_snapshot=_grant_snapshot(
            status="active",
            plan_code="basic",
            display_name="Safe Expired Basic",
            plan_uuid=uuid.uuid4(),
            expires_at=now - timedelta(days=1),
            is_trial=False,
            device_limit=1,
        ),
        source_snapshot={"fixture": "safe_client_pack"},
        effective_from=now - timedelta(days=40),
        expires_at=now - timedelta(days=1),
        activated_at=now - timedelta(days=40),
    )
    active_device_credential = DeviceCredentialModel(
        id=device_credential_id,
        credential_key="safe-client-desktop-credential",
        service_identity_id=active_service_identity_id,
        auth_realm_id=realm_id,
        provisioning_profile_id=provisioning_profile_id,
        credential_type="desktop_client",
        credential_status="active",
        subject_key="safe-desktop-primary",
        provider_name="remnawave",
        provider_credential_ref="safe-device-ref",
        credential_context={"fixture": "safe_client_pack", "contains_secret": False},
        issued_at=now - timedelta(hours=6),
    )
    active_channel = AccessDeliveryChannelModel(
        id=uuid.uuid4(),
        delivery_key="safe-client-shared-channel",
        service_identity_id=active_service_identity_id,
        auth_realm_id=realm_id,
        provisioning_profile_id=provisioning_profile_id,
        device_credential_id=device_credential_id,
        channel_type="shared_client",
        channel_status="active",
        channel_subject_ref="safe-desktop-primary",
        provider_name="remnawave",
        delivery_context={"fixture": "safe_client_pack"},
        delivery_payload={
            "entitlement_status": "active",
            "provider_name": "remnawave",
            "subscription_key": active_subscription_key,
            "subscription_url": SAFE_CLIENT_SUBSCRIPTION_URL,
        },
        last_delivered_at=now - timedelta(hours=1),
    )
    active_mobile_reconciliation = RemnawaveIdentityReconciliationModel(
        subject_type="mobile_user",
        subject_id=active_user_id,
        legacy_uuid=str(provider_subject_ref),
        numeric_user_id=provider_numeric_subject_id,
        reconciliation_state="mapped",
        evidence={"source": "safe_client_fixture_pack"},
        reconciled_at=now,
    )
    active_service_reconciliation = RemnawaveIdentityReconciliationModel(
        subject_type="service_identity",
        subject_id=active_service_identity_id,
        legacy_uuid=str(provider_subject_ref),
        numeric_user_id=provider_numeric_subject_id,
        reconciliation_state="mapped",
        evidence={"source": "safe_client_fixture_pack"},
        reconciled_at=now,
    )
    wallet = WalletModel(
        id=wallet_id,
        user_id=active_user_id,
        balance=Decimal("42.50"),
        currency="USD",
        frozen=Decimal("5.00"),
    )
    wallet_credit = WalletTransactionModel(
        id=uuid.uuid4(),
        wallet_id=wallet_id,
        user_id=active_user_id,
        type="credit",
        amount=Decimal("50.00"),
        currency="USD",
        balance_after=Decimal("50.00"),
        reason="admin_topup",
        reference_type="fixture",
        reference_id=None,
        description="Synthetic safe-client fixture credit.",
        created_at=now - timedelta(days=2),
    )
    wallet_debit = WalletTransactionModel(
        id=uuid.uuid4(),
        wallet_id=wallet_id,
        user_id=active_user_id,
        type="debit",
        amount=Decimal("7.50"),
        currency="USD",
        balance_after=Decimal("42.50"),
        reason="subscription_payment",
        reference_type="fixture",
        reference_id=None,
        description="Synthetic safe-client fixture debit.",
        created_at=now - timedelta(days=1),
    )
    payment = PaymentModel(
        id=payment_id,
        external_id="synthetic-payment-history-001",
        user_uuid=active_user_id,
        amount=Decimal("75.00"),
        currency="USD",
        status="completed",
        provider="cryptobot",
        subscription_days=30,
        promo_code_id=promo.id,
        discount_amount=Decimal("7.50"),
        wallet_amount_used=Decimal("7.50"),
        final_amount=Decimal("60.00"),
        entitlements_snapshot=active_grant.grant_snapshot,
        metadata_={
            "fixture": "safe_client_pack",
            "provider_mode": "synthetic_no_capture",
            "raw_provider_payload": None,
        },
        created_at=now - timedelta(days=1),
    )

    with sessionmaker() as db:
        db.add_all(
            [
                customer_realm,
                active_user,
                trial_user,
                expired_user,
                no_subscription_user,
                referral_owner,
                partner_owner,
                partner_account,
                partner_code,
                promo,
                active_service_identity,
                active_profile,
                active_grant,
                expired_service_identity,
                expired_grant,
                active_device_credential,
                active_channel,
                active_mobile_reconciliation,
                active_service_reconciliation,
                wallet,
                wallet_credit,
                wallet_debit,
                payment,
            ]
        )
        db.commit()

    pack = SafeClientFixturePack(
        auth_realm_id=realm_id,
        auth_realm_key="customer",
        auth_realm_audience="cybervpn:safe-client-fixture",
        active=SafeClientAccount(
            user_id=active_user_id,
            email=active_user.email,
            state="active",
            telegram_id=active_user.telegram_id,
            referral_code=active_user.referral_code,
            subscription_key=active_subscription_key,
            entitlement_grant_id=active_grant_id,
            service_identity_id=active_service_identity_id,
            device_subject_key=active_device_credential.subject_key,
            remnawave_user_id=provider_numeric_subject_id,
            remnawave_uuid=provider_subject_ref,
        ),
        trial=SafeClientAccount(
            user_id=trial_user_id,
            email=trial_user.email,
            state="trial",
            telegram_id=trial_user.telegram_id,
        ),
        expired=SafeClientAccount(
            user_id=expired_user_id,
            email=expired_user.email,
            state="expired",
            telegram_id=expired_user.telegram_id,
            subscription_key=f"grant:{expired_grant.id}",
            entitlement_grant_id=expired_grant.id,
            service_identity_id=expired_service_identity.id,
        ),
        no_subscription=SafeClientAccount(
            user_id=no_subscription_user_id,
            email=no_subscription_user.email,
            state="no_subscription",
            telegram_id=no_subscription_user.telegram_id,
        ),
        referral_owner=SafeClientAccount(
            user_id=referral_owner_id,
            email=referral_owner.email,
            state="referral_owner",
            referral_code=referral_owner.referral_code,
        ),
        partner_owner=SafeClientAccount(
            user_id=partner_owner_id,
            email=partner_owner.email,
            state="partner_owner",
        ),
        promo_code=promo.code,
        partner_code=partner_code.code,
        subscription_url=SAFE_CLIENT_SUBSCRIPTION_URL,
        miniapp_init_data=miniapp_init_data,
    )
    assert_safe_client_fixture_pack_is_synthetic(pack)
    return pack


def build_safe_miniapp_init_data(
    *,
    telegram_user_id: int,
    username: str,
    auth_date: int,
) -> str:
    user = json.dumps(
        {
            "id": telegram_user_id,
            "first_name": "Safe",
            "username": username,
            "language_code": "en",
        },
        separators=(",", ":"),
    )
    fields = {
        "auth_date": str(auth_date),
        "query_id": f"safe-client-query-{telegram_user_id}",
        "user": user,
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(
        b"WebAppData",
        SAFE_MINIAPP_BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def assert_safe_client_fixture_pack_is_synthetic(pack: SafeClientFixturePack) -> None:
    assert_safe_payload_is_synthetic(asdict(pack))


def assert_safe_payload_is_synthetic(payload: Any) -> None:
    flattened = _flatten_payload(payload).lower()
    forbidden_patterns = {
        "production domain": r"cyber-vpn\.(net|org)",
        "raw vpn uri": r"\b(vless|vmess|trojan|ss|wireguard)://",
        "private key material": r"private[-_ ]?key|begin .* key",
        "live payment key": r"\b(sk|pk)_live_[a-z0-9]",
        "bearer/api token": r"\b(bearer|api[_-]?key|x-api-key)\b",
        "provider checkout url": r"pay\.crypt\.bot|yookassa|nowpayments|payram|digiseller",
        "real telegram bot token shape": r"\b\d{6,}:[a-z0-9_-]{20,}\b",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, flattened):
            msg = f"Unsafe {label} found in safe client fixture payload"
            raise AssertionError(msg)


def _flatten_payload(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{key}={_flatten_payload(item)}" for key, item in sorted(value.items()))
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten_payload(item) for item in value)
    if isinstance(value, (uuid.UUID, datetime, Decimal)):
        return str(value)
    return "" if value is None else str(value)


def _grant_snapshot(
    *,
    status: str,
    plan_code: str,
    display_name: str,
    plan_uuid: uuid.UUID,
    expires_at: datetime,
    is_trial: bool,
    device_limit: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "plan_uuid": str(plan_uuid),
        "plan_code": plan_code,
        "display_name": display_name,
        "period_days": 30,
        "expires_at": expires_at.isoformat(),
        "effective_entitlements": {
            "device_limit": device_limit,
            "traffic_policy": "quota",
            "display_traffic_label": "30 GB",
            "connection_modes": ["wireguard"],
            "server_pool": ["safe-fixture-eu"],
            "support_sla": "standard",
            "dedicated_ip_count": 0,
        },
        "invite_bundle": {"count": 1, "friend_days": 7, "expiry_days": 30},
        "is_trial": is_trial,
        "addons": [],
    }
