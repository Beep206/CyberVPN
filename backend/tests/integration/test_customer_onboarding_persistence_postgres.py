from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.services.config_service import (
    CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
    CustomerOnboardingRuntimeConfig,
)
from src.application.use_cases.customer_onboarding import (
    ApplyCustomerOnboardingGrowthCodeUseCase,
    ConnectionPlatform,
    ConnectionSurface,
    CustomerOnboardingAppliedCode,
    CustomerOnboardingFlowTokenService,
    CustomerOnboardingUnavailableError,
    GetCurrentCustomerOnboardingUseCase,
    SkipCustomerOnboardingUseCase,
)
from src.infrastructure.database.models.access_delivery_channel_model import AccessDeliveryChannelModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_onboarding_model import (
    CustomerConnectionSessionModel,
    CustomerOnboardingCodeApplicationModel,
    CustomerOnboardingStateModel,
)
from src.infrastructure.database.models.entitlement_grant_model import EntitlementGrantModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel
from src.infrastructure.database.repositories.customer_onboarding_repo import (
    CustomerConnectionSessionSqlAlchemyRepository,
    CustomerOnboardingStateSqlAlchemyRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse, RemnawaveUserResponse
from src.presentation.api.v1.customer_onboarding import routes as onboarding_routes
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]


class RecordingOnboardingCodeApplier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, uuid.UUID, str]] = []

    async def apply_code(
        self,
        *,
        code: str,
        user_id: uuid.UUID,
        idempotency_key: str,
        normalized_code_hash: str,
        masked_code: str,
    ) -> CustomerOnboardingAppliedCode:
        _ = normalized_code_hash
        self.calls.append((code, user_id, idempotency_key))
        return CustomerOnboardingAppliedCode(
            result="accepted",
            code_type="invite",
            message_key="onboarding.code.accepted",
            masked_code=masked_code,
            next_destination="/dashboard",
            entitlement_snapshot={"status": "active", "duration_days": 7},
            safe_details={"applier_call_count": len(self.calls)},
        )


class _FakeOnboardingRemnawaveClient:
    def __init__(self, *, subscription_url: str) -> None:
        self.created_uuid = uuid.uuid4()
        self.username = "cvpn_s_onboarding"
        self.subscription_url = subscription_url
        self.get_paths: list[str] = []
        self.collection_paths: list[str] = []
        self.post_payloads: list[dict[str, object]] = []
        self.get_validated_paths: list[str] = []

    async def get(self, path: str):
        self.get_paths.append(path)
        assert path.startswith("/api/users/by-telegram-id/")
        return []

    async def get_collection_validated(self, path: str, collection_key: str, item_schema):
        self.collection_paths.append(path)
        assert path == "/internal-squads"
        assert collection_key == "internalSquads"
        _ = item_schema
        return [SimpleNamespace(uuid=str(uuid.uuid4()), name="Default-Squad")]

    async def post_validated(self, path: str, schema, *, json=None):
        assert path == "/api/users"
        assert schema is RemnawaveUserResponse
        payload = dict(json or {})
        self.post_payloads.append(payload)
        self.username = str(payload.get("username") or self.username)
        now = datetime.now(UTC)
        return RemnawaveUserResponse(
            uuid=str(self.created_uuid),
            username=self.username,
            status="ACTIVE",
            short_uuid=str(self.created_uuid)[:8],
            created_at=now,
            updated_at=now,
            expire_at=payload.get("expireAt"),
            subscription_url=self.subscription_url,
            traffic_limit_bytes=payload.get("trafficLimitBytes"),
            hwid_device_limit=payload.get("hwidDeviceLimit"),
        )

    async def get_validated(self, path: str, schema):
        self.get_validated_paths.append(path)
        assert path == f"/subscriptions/by-uuid/{self.created_uuid}"
        assert schema is RemnawaveSubscriptionDetailsResponse
        return RemnawaveSubscriptionDetailsResponse(
            is_found=True,
            user={
                "shortUuid": str(self.created_uuid)[:8],
                "username": self.username,
                "userStatus": "ACTIVE",
            },
            links=[f"vless://{self.created_uuid}@vpn.example.test:443"],
            subscription_url=self.subscription_url,
        )


@dataclass(frozen=True)
class _ServiceAccessSnapshot:
    identity_scope: str
    subscription_key: str | None
    provider_subject_ref: str | None
    service_context: dict[str, object]
    channel_type: str
    delivery_payload: dict[str, object]


@pytest.mark.asyncio
async def test_postgres_customer_onboarding_state_restores_and_persists_idempotently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_name = f"cvpn_onboarding_{uuid.uuid4().hex[:16]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    try:
        await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            runtime = CustomerOnboardingRuntimeConfig(
                post_registration_code_prompt_enabled=True,
                web_otp_enabled=True,
                telegram_miniapp_enabled=True,
                state_store_ready=True,
            )
            await _seed_onboarding_runtime_config(maker, runtime)
            clock = {"now": 1_000_000}
            flow_tokens = CustomerOnboardingFlowTokenService(
                secret="2" * 32,
                clock=lambda: clock["now"],
            )
            telegram_id = 777_123_456
            legacy_subscription_url = "https://sub.example/legacy-web-bot-mini-token"
            subscription_url = "https://sub.example/provider-web-bot-mini-token"
            remnawave_client = _FakeOnboardingRemnawaveClient(subscription_url=subscription_url)
            user_id = await _seed_onboarding_user(
                maker,
                email="onboarding-primary@example.test",
                telegram_id=telegram_id,
                subscription_url=legacy_subscription_url,
            )
            other_user_id = await _seed_onboarding_user(maker, email="onboarding-other@example.test")
            skip_user_id = await _seed_onboarding_user(maker, email="onboarding-skip@example.test")
            customer_realm_id = await _customer_realm_id(maker)

            async with maker() as session:
                state = await CustomerOnboardingStateSqlAlchemyRepository(session).ensure_pending(
                    user_id=user_id,
                    runtime_config=runtime,
                    source_channel="web",
                    auth_channel="otp",
                    referral_terminal_state="claimed",
                )
                assert state.required is True
                assert state.server_state_available is True
                await session.commit()
            assert await _onboarding_state_count(maker, user_id=user_id) == 1

            async with maker() as session:
                current = await GetCurrentCustomerOnboardingUseCase(
                    runtime_config=runtime,
                    state_repo=CustomerOnboardingStateSqlAlchemyRepository(session),
                    flow_tokens=flow_tokens,
                ).execute(user_id=user_id)
            assert current.required is True
            assert current.status == "pending"
            assert current.server_state_available is True
            assert current.referral_already_attributed is True
            assert current.flow_token is not None

            clock["now"] += 1
            async with maker() as session:
                restored = await GetCurrentCustomerOnboardingUseCase(
                    runtime_config=runtime,
                    state_repo=CustomerOnboardingStateSqlAlchemyRepository(session),
                    flow_tokens=flow_tokens,
                ).execute(user_id=user_id)
            assert restored.flow_token is not None
            assert restored.flow_token != current.flow_token

            applier = RecordingOnboardingCodeApplier()
            monkeypatch.setattr(onboarding_routes, "CustomerOnboardingFlowTokenService", lambda: flow_tokens)
            monkeypatch.setattr(
                onboarding_routes,
                "CustomerOnboardingGrowthCodeApplier",
                lambda *_args, **_kwargs: applier,
            )
            async with maker() as session:
                result = await onboarding_routes.apply_customer_onboarding_growth_code(
                    payload=onboarding_routes.CustomerOnboardingApplyRequest(
                        code="SAVE20",
                        flow_token=restored.flow_token,
                        idempotency_key="apply-1",
                        source_surface="web",
                    ),
                    user_id=user_id,
                    telegram_bot_secret=None,
                    current_realm=SimpleNamespace(
                        auth_realm=SimpleNamespace(id=customer_realm_id),
                        source="web",
                    ),
                    db=session,
                )
                assert result.status == "completed"
                assert result.masked_code == "SAVE...20"
                assert result.connection_required is True
            assert len(applier.calls) == 1
            assert await _onboarding_application_count(maker, user_id=user_id) == 1
            assert await _onboarding_state_status(maker, user_id=user_id) == "completed"

            async with maker() as session:
                current_after_bot_apply = await onboarding_routes.get_current_customer_onboarding(
                    user_id=user_id,
                    db=session,
                )
            assert current_after_bot_apply.required is False
            assert current_after_bot_apply.status == "completed"
            assert current_after_bot_apply.connection_required is True

            await _seed_active_entitlement(
                maker,
                user_id=user_id,
                auth_realm_id=customer_realm_id,
                suffix=uuid.uuid4().hex,
            )

            def require_telegram_secret(secret: str | None) -> None:
                assert secret == "telegram-internal-secret"

            monkeypatch.setattr(onboarding_routes, "_require_telegram_bot_secret", require_telegram_secret)

            async def fetch_bootstrap(surface: str, platform_hint: str):
                async with maker() as session:
                    return await onboarding_routes.get_customer_onboarding_connection_bootstrap(
                        response=Response(),
                        surface=cast(ConnectionSurface, surface),
                        platform_hint=cast(ConnectionPlatform, platform_hint),
                        telegram_id=telegram_id if surface == "telegram_bot" else None,
                        user_id=None if surface == "telegram_bot" else user_id,
                        telegram_bot_secret="telegram-internal-secret" if surface == "telegram_bot" else None,
                        current_realm=SimpleNamespace(
                            auth_realm=SimpleNamespace(id=customer_realm_id),
                            source=surface,
                        ),
                        db=session,
                        remnawave_client=remnawave_client,
                    )

            web_bootstrap = await fetch_bootstrap("web", "ios")
            telegram_bootstrap = await fetch_bootstrap("telegram_bot", "android")
            miniapp_bootstrap = await fetch_bootstrap("miniapp", "ios")

            assert web_bootstrap.available is True
            assert telegram_bootstrap.available is True
            assert miniapp_bootstrap.available is True
            assert web_bootstrap.subscription_url == subscription_url
            assert telegram_bootstrap.subscription_url == subscription_url
            assert miniapp_bootstrap.subscription_url == subscription_url
            assert legacy_subscription_url not in {
                web_bootstrap.subscription_url,
                telegram_bootstrap.subscription_url,
                miniapp_bootstrap.subscription_url,
            }
            assert len(remnawave_client.post_payloads) == 1
            assert remnawave_client.post_payloads[0]["email"] == "onboarding-primary@example.test"
            assert remnawave_client.collection_paths == ["/internal-squads"]
            assert len(remnawave_client.get_validated_paths) == 3
            service_access = await _selected_subscription_service_access_snapshot(
                maker,
                user_id=user_id,
                provider_subject_ref=str(remnawave_client.created_uuid),
            )
            assert service_access.identity_scope == "subscription"
            assert service_access.subscription_key is not None
            assert service_access.subscription_key.startswith("grant:")
            assert service_access.provider_subject_ref == str(remnawave_client.created_uuid)
            assert service_access.service_context["subscription_url"] == subscription_url
            assert service_access.channel_type == "shared_client"
            assert service_access.delivery_payload["subscription_url"] == subscription_url
            assert service_access.delivery_payload["subscription_key"] == service_access.subscription_key
            assert web_bootstrap.flow_key == runtime.flow_key
            assert telegram_bootstrap.flow_key == runtime.flow_key
            assert miniapp_bootstrap.flow_key == runtime.flow_key
            assert web_bootstrap.version == runtime.version
            assert telegram_bootstrap.version == runtime.version
            assert miniapp_bootstrap.version == runtime.version
            assert web_bootstrap.connection_session_id is not None
            assert telegram_bootstrap.connection_session_id == web_bootstrap.connection_session_id
            assert miniapp_bootstrap.connection_session_id == web_bootstrap.connection_session_id
            assert telegram_bootstrap.telegram_payload is not None
            assert telegram_bootstrap.telegram_payload.bot_connection_session_id is not None
            assert (
                telegram_bootstrap.telegram_payload.bot_connection_session_id
                == telegram_bootstrap.connection_session_id
            )
            assert len(applier.calls) == 1
            assert await _connection_session_count(maker, user_id=user_id) == 1

            old_connection_session_id = telegram_bootstrap.connection_session_id
            updated_legacy_subscription_url = "https://sub.example/legacy-web-bot-mini-token-v2"
            updated_subscription_url = "https://sub.example/provider-web-bot-mini-token-v2"
            await _update_subscription_url(
                maker,
                user_id=user_id,
                subscription_url=updated_legacy_subscription_url,
            )
            remnawave_client.subscription_url = updated_subscription_url
            fresh_bootstrap = await fetch_bootstrap("miniapp", "android")
            assert fresh_bootstrap.connection_session_id is not None
            assert fresh_bootstrap.connection_session_id != old_connection_session_id
            assert fresh_bootstrap.subscription_url == updated_subscription_url
            assert fresh_bootstrap.subscription_url != updated_legacy_subscription_url
            assert len(remnawave_client.post_payloads) == 1
            assert len(remnawave_client.get_validated_paths) == 4
            refreshed_service_access = await _selected_subscription_service_access_snapshot(
                maker,
                user_id=user_id,
                provider_subject_ref=str(remnawave_client.created_uuid),
            )
            assert refreshed_service_access.service_context["subscription_url"] == updated_subscription_url
            assert refreshed_service_access.delivery_payload["subscription_url"] == updated_subscription_url
            assert await _connection_session_count(maker, user_id=user_id) == 2
            assert (
                await _connection_session_status_by_id(
                    maker,
                    session_id=uuid.UUID(old_connection_session_id),
                )
                == "cancelled"
            )

            async with maker() as session:
                unbound_mark_result = await CustomerConnectionSessionSqlAlchemyRepository(
                    session,
                ).mark_connected(
                    user_id=user_id,
                    connection_session_id=cast(uuid.UUID, None),
                    source_surface="telegram_bot",
                    selected_platform="android",
                    flow_key=telegram_bootstrap.flow_key,
                    version=telegram_bootstrap.version,
                    connected_at=datetime.now(UTC),
                )
                await session.commit()

            assert unbound_mark_result.status == "not_required"
            assert (
                await _connection_session_status_by_id(
                    maker,
                    session_id=uuid.UUID(fresh_bootstrap.connection_session_id),
                )
                == "available"
            )

            async with maker() as session:
                stale_mark_result = await onboarding_routes.mark_customer_onboarding_connection_connected(
                    payload=onboarding_routes.MarkOnboardingConnectionConnectedRequest(
                        connection_session_id=old_connection_session_id,
                        source_surface="telegram_bot",
                        telegram_id=telegram_id,
                        platform="android",
                        flow_key=telegram_bootstrap.flow_key,
                        version=telegram_bootstrap.version,
                    ),
                    user_id=None,
                    telegram_bot_secret="telegram-internal-secret",
                    current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=customer_realm_id)),
                    db=session,
                )

            assert stale_mark_result.status == "not_required"
            assert (
                await _connection_session_status_by_id(
                    maker,
                    session_id=uuid.UUID(old_connection_session_id),
                )
                == "cancelled"
            )

            async with maker() as session:
                mark_result = await onboarding_routes.mark_customer_onboarding_connection_connected(
                    payload=onboarding_routes.MarkOnboardingConnectionConnectedRequest(
                        connection_session_id=fresh_bootstrap.connection_session_id,
                        source_surface="telegram_bot",
                        telegram_id=telegram_id,
                        platform="android",
                        flow_key=fresh_bootstrap.flow_key,
                        version=fresh_bootstrap.version,
                    ),
                    user_id=None,
                    telegram_bot_secret="telegram-internal-secret",
                    current_realm=SimpleNamespace(auth_realm=SimpleNamespace(id=customer_realm_id)),
                    db=session,
                )

            assert mark_result.status == "recorded"
            assert mark_result.flow_key == runtime.flow_key
            assert mark_result.version == runtime.version
            assert (
                await _connection_session_status_by_id(
                    maker,
                    session_id=uuid.UUID(fresh_bootstrap.connection_session_id),
                )
                == "acknowledged"
            )

            async with maker() as session:
                duplicate = await ApplyCustomerOnboardingGrowthCodeUseCase(
                    runtime_config=runtime,
                    state_repo=CustomerOnboardingStateSqlAlchemyRepository(session),
                    flow_tokens=flow_tokens,
                ).execute(
                    user_id=user_id,
                    code="SAVE20",
                    flow_token=restored.flow_token,
                    idempotency_key="apply-1",
                    code_applier=applier,
                )
                assert duplicate.status == "completed"
                await session.commit()
            assert len(applier.calls) == 1
            assert await _onboarding_application_count(maker, user_id=user_id) == 1

            async with maker() as session:
                await CustomerOnboardingStateSqlAlchemyRepository(session).ensure_pending(
                    user_id=other_user_id,
                    runtime_config=runtime,
                    source_channel="web",
                    auth_channel="otp",
                )
                await session.commit()
            async with maker() as session:
                with pytest.raises(CustomerOnboardingUnavailableError) as exc_info:
                    await ApplyCustomerOnboardingGrowthCodeUseCase(
                        runtime_config=runtime,
                        state_repo=CustomerOnboardingStateSqlAlchemyRepository(session),
                        flow_tokens=flow_tokens,
                    ).execute(
                        user_id=other_user_id,
                        code="SAVE20",
                        flow_token=restored.flow_token,
                        idempotency_key="cross-user",
                        code_applier=applier,
                    )
                await session.rollback()
            assert exc_info.value.code == "CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID"
            assert await _onboarding_state_status(maker, user_id=other_user_id) == "pending"
            assert await _onboarding_application_count(maker, user_id=other_user_id) == 0

            async with maker() as session:
                await CustomerOnboardingStateSqlAlchemyRepository(session).ensure_pending(
                    user_id=skip_user_id,
                    runtime_config=runtime,
                    source_channel="miniapp",
                    auth_channel="telegram_miniapp",
                )
                await session.commit()
            clock["now"] += 1
            skip_token = flow_tokens.issue(
                user_id=skip_user_id,
                flow_key=runtime.flow_key,
                version=runtime.version,
            )
            async with maker() as session:
                skip_result = await SkipCustomerOnboardingUseCase(
                    runtime_config=runtime,
                    state_repo=CustomerOnboardingStateSqlAlchemyRepository(session),
                    flow_tokens=flow_tokens,
                ).execute(
                    user_id=skip_user_id,
                    flow_token=skip_token,
                    idempotency_key="skip-1",
                )
                assert skip_result.status == "skipped"
                await session.commit()
            assert await _onboarding_state_status(maker, user_id=skip_user_id) == "skipped"
        finally:
            await engine.dispose()
    finally:
        await _drop_database(database_name)


async def _seed_onboarding_user(
    maker: async_sessionmaker[AsyncSession],
    *,
    email: str,
    telegram_id: int | None = None,
    subscription_url: str | None = None,
) -> uuid.UUID:
    async with maker() as session:
        auth_realm_id = await session.scalar(select(AuthRealmModel.id).where(AuthRealmModel.realm_key == "customer"))
        assert auth_realm_id is not None
        user = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=auth_realm_id,
            email=email,
            telegram_id=telegram_id,
            subscription_url=subscription_url,
            password_hash="hash",
            notification_prefs={},
            totp_enabled=False,
            is_active=True,
            status="active",
        )
        session.add(user)
        await session.commit()
        return user.id


async def _customer_realm_id(maker: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with maker() as session:
        auth_realm_id = await session.scalar(select(AuthRealmModel.id).where(AuthRealmModel.realm_key == "customer"))
        assert auth_realm_id is not None
        return auth_realm_id


async def _seed_onboarding_runtime_config(
    maker: async_sessionmaker[AsyncSession],
    runtime: CustomerOnboardingRuntimeConfig,
) -> None:
    async with maker() as session:
        await SystemConfigRepository(session).set(
            CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
            {
                "post_registration_code_prompt_enabled": runtime.post_registration_code_prompt_enabled,
                "web_otp_enabled": runtime.web_otp_enabled,
                "telegram_miniapp_enabled": runtime.telegram_miniapp_enabled,
                "state_store_ready": runtime.state_store_ready,
                "flow_key": runtime.flow_key,
                "version": runtime.version,
                "allowed_code_types": list(runtime.allowed_code_types),
                "allow_referral_input": runtime.allow_referral_input,
                "allow_partner_input": runtime.allow_partner_input,
            },
        )
        await session.commit()


async def _seed_active_entitlement(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
    auth_realm_id: uuid.UUID,
    suffix: str,
) -> None:
    async with maker() as session:
        service_identity_id = uuid.uuid4()
        session.add(
            ServiceIdentityModel(
                id=service_identity_id,
                service_key=f"onboarding-shared-state-{suffix}",
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                provider_name="remnawave",
                provider_subject_ref=f"rw-onboarding-{suffix}",
                identity_status="active",
                service_context={},
            )
        )
        await session.flush()
        session.add(
            EntitlementGrantModel(
                id=uuid.uuid4(),
                grant_key=f"onboarding-shared-grant-{suffix}",
                service_identity_id=service_identity_id,
                customer_account_id=user_id,
                auth_realm_id=auth_realm_id,
                source_type="manual",
                manual_source_key=f"onboarding-shared-manual-{suffix}",
                grant_status="active",
                grant_snapshot={
                    "status": "active",
                    "plan_code": "shared-onboarding",
                    "display_name": "Shared onboarding entitlement",
                    "effective_entitlements": {
                        "device_limit": 3,
                        "traffic_limit_bytes": 1_073_741_824,
                    },
                },
                effective_from=datetime.now(UTC) - timedelta(days=1),
                expires_at=datetime.now(UTC) + timedelta(days=30),
                activated_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()


async def _onboarding_state_count(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
) -> int:
    async with maker() as session:
        value = await session.scalar(
            select(func.count())
            .select_from(CustomerOnboardingStateModel)
            .where(CustomerOnboardingStateModel.mobile_user_id == user_id)
        )
        return int(value or 0)


async def _onboarding_application_count(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
) -> int:
    async with maker() as session:
        value = await session.scalar(
            select(func.count())
            .select_from(CustomerOnboardingCodeApplicationModel)
            .where(CustomerOnboardingCodeApplicationModel.mobile_user_id == user_id)
        )
        return int(value or 0)


async def _onboarding_state_status(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
) -> str | None:
    async with maker() as session:
        return await session.scalar(
            select(CustomerOnboardingStateModel.status).where(CustomerOnboardingStateModel.mobile_user_id == user_id)
        )


async def _update_subscription_url(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
    subscription_url: str,
) -> None:
    async with maker() as session:
        user = await session.get(MobileUserModel, user_id)
        assert user is not None
        user.subscription_url = subscription_url
        await session.commit()


async def _connection_session_count(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
) -> int:
    async with maker() as session:
        value = await session.scalar(
            select(func.count())
            .select_from(CustomerConnectionSessionModel)
            .where(CustomerConnectionSessionModel.mobile_user_id == user_id)
        )
        return int(value or 0)


async def _selected_subscription_service_access_snapshot(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
    provider_subject_ref: str,
) -> _ServiceAccessSnapshot:
    async with maker() as session:
        service_identity = await session.scalar(
            select(ServiceIdentityModel).where(
                ServiceIdentityModel.customer_account_id == user_id,
                ServiceIdentityModel.identity_scope == "subscription",
                ServiceIdentityModel.provider_subject_ref == provider_subject_ref,
            )
        )
        assert service_identity is not None
        channel = await session.scalar(
            select(AccessDeliveryChannelModel).where(
                AccessDeliveryChannelModel.service_identity_id == service_identity.id,
                AccessDeliveryChannelModel.channel_type == "shared_client",
            )
        )
        assert channel is not None
        return _ServiceAccessSnapshot(
            identity_scope=service_identity.identity_scope,
            subscription_key=service_identity.subscription_key,
            provider_subject_ref=service_identity.provider_subject_ref,
            service_context=dict(service_identity.service_context or {}),
            channel_type=channel.channel_type,
            delivery_payload=dict(channel.delivery_payload or {}),
        )


async def _connection_session_status(
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: uuid.UUID,
) -> str | None:
    async with maker() as session:
        return await session.scalar(
            select(CustomerConnectionSessionModel.status).where(
                CustomerConnectionSessionModel.mobile_user_id == user_id
            )
        )


async def _connection_session_status_by_id(
    maker: async_sessionmaker[AsyncSession],
    *,
    session_id: uuid.UUID,
) -> str | None:
    async with maker() as session:
        return await session.scalar(
            select(CustomerConnectionSessionModel.status).where(CustomerConnectionSessionModel.id == session_id)
        )
