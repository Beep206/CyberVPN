from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import (
    ApplyCustomerOnboardingGrowthCodeUseCase,
    CustomerOnboardingAppliedCode,
    CustomerOnboardingFlowTokenService,
    CustomerOnboardingUnavailableError,
    GetCurrentCustomerOnboardingUseCase,
    SkipCustomerOnboardingUseCase,
)
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.customer_onboarding_model import (
    CustomerOnboardingCodeApplicationModel,
    CustomerOnboardingStateModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.customer_onboarding_repo import (
    CustomerOnboardingStateSqlAlchemyRepository,
)
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
            code_type="promo",
            message_key="onboarding.code.accepted",
            masked_code=masked_code,
            next_destination="/dashboard",
            safe_details={"applier_call_count": len(self.calls)},
        )


@pytest.mark.asyncio
async def test_postgres_customer_onboarding_state_restores_and_persists_idempotently() -> None:
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
            clock = {"now": 1_000_000}
            flow_tokens = CustomerOnboardingFlowTokenService(
                secret="2" * 32,
                clock=lambda: clock["now"],
            )
            user_id = await _seed_onboarding_user(maker, email="onboarding-primary@example.test")
            other_user_id = await _seed_onboarding_user(maker, email="onboarding-other@example.test")
            skip_user_id = await _seed_onboarding_user(maker, email="onboarding-skip@example.test")

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
            async with maker() as session:
                result = await ApplyCustomerOnboardingGrowthCodeUseCase(
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
                assert result.status == "completed"
                assert result.masked_code == "SAVE...20"
                await session.commit()
            assert len(applier.calls) == 1
            assert await _onboarding_application_count(maker, user_id=user_id) == 1
            assert await _onboarding_state_status(maker, user_id=user_id) == "completed"

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
) -> uuid.UUID:
    async with maker() as session:
        auth_realm_id = await session.scalar(select(AuthRealmModel.id).where(AuthRealmModel.realm_key == "customer"))
        assert auth_realm_id is not None
        user = MobileUserModel(
            id=uuid.uuid4(),
            auth_realm_id=auth_realm_id,
            email=email,
            password_hash="hash",
            notification_prefs={},
            totp_enabled=False,
            is_active=True,
            status="active",
        )
        session.add(user)
        await session.commit()
        return user.id


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
