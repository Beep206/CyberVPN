"""Seed a local admin operator for AC-18 live BFF/browser smoke evidence.

The script is intentionally local-only. It refuses non-loopback database URLs
and writes generated credentials only under .private so evidence can remain
sanitized.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import socket
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.infrastructure.database.models.messaging_conversation_model import (
    MessagingConversationModel,
    MessagingConversationParticipantModel,
    MessagingMessageModel,
    MessagingMessageReadStateModel,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.privacy_request_model import (
    PrivacyRequestEventModel,
    PrivacyRequestModel,
)
from src.infrastructure.database.models.support_ticket_model import (
    SupportTicketEventModel,
    SupportTicketMessageModel,
    SupportTicketModel,
)
from src.infrastructure.database.session import AsyncSessionLocal, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_OUTPUT = REPO_ROOT / ".private" / "latest-admin-smoke.json"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
FORBIDDEN_HOSTS = {
    "45.87.41.146",
    "prod-app-1",
    "my.cyber-vpn.net",
    "api.cyber-vpn.net",
}


def _database_host(url: str) -> str:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    return (parsed.hostname or "").lower()


def _is_loopback(host: str) -> bool:
    if host in LOCAL_HOSTS:
        return True
    try:
        return all(
            socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0][4][0].startswith(
                "127."
            )
            for _ in [host]
        )
    except socket.gaierror:
        return False


def _assert_local_database() -> None:
    host = _database_host(settings.database_url)
    if host in FORBIDDEN_HOSTS or not _is_loopback(host):
        raise RuntimeError(
            "Refusing to seed admin smoke data into a non-local database. "
            f"Resolved host: {host or '<missing>'}."
        )


def _new_password() -> str:
    return f"Ac18AdminSmoke-{secrets.token_urlsafe(18)}_1!"


async def _get_or_create_realm(
    session, *, realm_key: str, realm_type: str, display_name: str
) -> AuthRealmModel:
    result = await session.execute(
        select(AuthRealmModel).where(AuthRealmModel.realm_key == realm_key)
    )
    realm = result.scalar_one_or_none()
    if realm is not None:
        realm.realm_type = realm_type
        realm.display_name = display_name
        realm.audience = f"cybervpn:{realm_key}"
        realm.cookie_namespace = realm_key
        realm.status = "active"
        realm.is_default = True
        return realm

    realm = AuthRealmModel(
        realm_key=realm_key,
        realm_type=realm_type,
        display_name=display_name,
        audience=f"cybervpn:{realm_key}",
        cookie_namespace=realm_key,
        status="active",
        is_default=True,
    )
    session.add(realm)
    await session.flush()
    return realm


async def _get_or_create_mobile_customer(
    session, auth_service: AuthService, *, customer_realm: AuthRealmModel
) -> MobileUserModel:
    result = await session.execute(
        select(MobileUserModel).where(
            MobileUserModel.email == "ac18-route-customer@example.invalid"
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = MobileUserModel(
            email="ac18-route-customer@example.invalid",
            username="ac18_route_customer",
            auth_realm_id=customer_realm.id,
            password_hash=await auth_service.hash_password(_new_password()),
            notification_prefs={},
            referral_code=f"A18{secrets.token_hex(4).upper()}",
            is_active=True,
            status="active",
        )
        session.add(customer)
        await session.flush()
        return customer

    customer.auth_realm_id = customer_realm.id
    customer.username = customer.username or "ac18_route_customer"
    customer.notification_prefs = customer.notification_prefs or {}
    customer.is_active = True
    customer.status = "active"
    await session.flush()
    return customer


async def _get_or_create_support_ticket(
    session,
    *,
    customer: MobileUserModel,
    admin: AdminUserModel,
) -> SupportTicketModel:
    now = datetime.now(UTC)
    result = await session.execute(
        select(SupportTicketModel).where(SupportTicketModel.public_id == "SUP-2026-001")
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        ticket = SupportTicketModel(
            public_id="SUP-2026-001",
            owner_type="customer",
            customer_account_id=customer.id,
            partner_workspace_id=None,
            created_by_actor_type="customer",
            created_by_actor_id=customer.id,
            source="customer_web",
            status="pending_support",
            category="privacy",
            priority="normal",
            subject="AC-18 route smoke support ticket",
            last_message_preview="Local AC-18 route smoke support ticket.",
            assigned_admin_id=admin.id,
            metadata_json={"source": "ac18_admin_local_seed"},
            created_at=now,
            updated_at=now,
            last_customer_message_at=now,
        )
        session.add(ticket)
        await session.flush()
    else:
        ticket.customer_account_id = customer.id
        ticket.owner_type = "customer"
        ticket.source = "customer_web"
        ticket.status = "pending_support"
        ticket.category = "privacy"
        ticket.priority = "normal"
        ticket.subject = "AC-18 route smoke support ticket"
        ticket.assigned_admin_id = admin.id
        ticket.metadata_json = {"source": "ac18_admin_local_seed"}
        ticket.updated_at = now

    message_exists = (
        await session.execute(
            select(SupportTicketMessageModel.id)
            .where(SupportTicketMessageModel.ticket_id == ticket.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if message_exists is None:
        session.add(
            SupportTicketMessageModel(
                ticket_id=ticket.id,
                author_type="customer",
                author_id=customer.id,
                visibility="public",
                body="Local AC-18 route smoke support ticket.",
                created_at=now,
            )
        )
    event_exists = (
        await session.execute(
            select(SupportTicketEventModel.id)
            .where(SupportTicketEventModel.ticket_id == ticket.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if event_exists is None:
        session.add(
            SupportTicketEventModel(
                ticket_id=ticket.id,
                actor_type="customer",
                actor_id=customer.id,
                event_type="ticket_created",
                from_value=None,
                to_value="pending_support",
                audit_summary="AC-18 local route smoke support ticket seeded.",
                created_at=now,
            )
        )
    await session.flush()
    return ticket


async def _get_or_create_privacy_request(
    session,
    *,
    customer: MobileUserModel,
    customer_realm: AuthRealmModel,
    ticket: SupportTicketModel,
) -> PrivacyRequestModel:
    now = datetime.now(UTC)
    result = await session.execute(
        select(PrivacyRequestModel).where(
            PrivacyRequestModel.public_id == "PRIV-2026-001"
        )
    )
    privacy_request = result.scalar_one_or_none()
    if privacy_request is None:
        result = await session.execute(
            select(PrivacyRequestModel).where(
                PrivacyRequestModel.auth_realm_id == customer_realm.id,
                PrivacyRequestModel.principal_type == "customer",
                PrivacyRequestModel.principal_subject == customer.id,
                PrivacyRequestModel.request_type == "data_export",
                PrivacyRequestModel.status.in_(
                    [
                        "submitted",
                        "identity_verification",
                        "pending_decision",
                        "approved",
                        "scheduled",
                        "failed",
                    ]
                ),
            )
        )
        privacy_request = result.scalar_one_or_none()

    if privacy_request is None:
        privacy_request = PrivacyRequestModel(
            public_id="PRIV-2026-001",
            auth_realm_id=customer_realm.id,
            principal_type="customer",
            principal_subject=customer.id,
            customer_account_id=customer.id,
            support_ticket_id=ticket.id,
            request_type="data_export",
            status="submitted",
            reason_code="route_smoke",
            notes_redacted="Local AC-18 route smoke privacy request.",
            locale="ru-RU",
            policy_snapshot={"source": "ac18_admin_local_seed"},
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(privacy_request)
        await session.flush()
    else:
        privacy_request.public_id = "PRIV-2026-001"
        privacy_request.auth_realm_id = customer_realm.id
        privacy_request.principal_type = "customer"
        privacy_request.principal_subject = customer.id
        privacy_request.customer_account_id = customer.id
        privacy_request.support_ticket_id = ticket.id
        privacy_request.request_type = "data_export"
        privacy_request.status = "submitted"
        privacy_request.reason_code = "route_smoke"
        privacy_request.notes_redacted = "Local AC-18 route smoke privacy request."
        privacy_request.locale = "ru-RU"
        privacy_request.policy_snapshot = {"source": "ac18_admin_local_seed"}
        privacy_request.updated_at = now

    event_exists = (
        await session.execute(
            select(PrivacyRequestEventModel.id)
            .where(PrivacyRequestEventModel.privacy_request_id == privacy_request.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if event_exists is None:
        session.add(
            PrivacyRequestEventModel(
                privacy_request_id=privacy_request.id,
                event_type="request_submitted",
                actor_type="customer",
                actor_id=customer.id,
                from_status=None,
                to_status="submitted",
                safe_summary="AC-18 local route smoke privacy request seeded.",
                metadata_json={"source": "ac18_admin_local_seed"},
                created_at=now,
            )
        )
    await session.flush()
    return privacy_request


async def _get_or_create_messaging_conversation(
    session,
    *,
    customer: MobileUserModel,
    admin: AdminUserModel,
    support_ticket: SupportTicketModel,
) -> MessagingConversationModel:
    now = datetime.now(UTC)
    result = await session.execute(
        select(MessagingConversationModel).where(
            MessagingConversationModel.public_id == "smoke-conversation-001"
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        conversation = MessagingConversationModel(
            public_id="smoke-conversation-001",
            customer_account_id=customer.id,
            status="open",
            response_state="waiting_admin",
            category="support",
            priority="normal",
            subject="AC-18 route smoke conversation",
            created_by_admin_id=admin.id,
            assigned_admin_id=admin.id,
            related_support_ticket_id=support_ticket.id,
            metadata_json={"source": "ac18_admin_local_seed"},
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(conversation)
        await session.flush()
    else:
        conversation.customer_account_id = customer.id
        conversation.status = "open"
        conversation.response_state = "waiting_admin"
        conversation.category = "support"
        conversation.priority = "normal"
        conversation.subject = "AC-18 route smoke conversation"
        conversation.assigned_admin_id = admin.id
        conversation.related_support_ticket_id = support_ticket.id
        conversation.metadata_json = {"source": "ac18_admin_local_seed"}
        conversation.last_message_at = now
        conversation.updated_at = now

    participant_exists = (
        await session.execute(
            select(MessagingConversationParticipantModel.id)
            .where(
                MessagingConversationParticipantModel.conversation_id
                == conversation.id,
                MessagingConversationParticipantModel.participant_type == "customer",
                MessagingConversationParticipantModel.participant_id == customer.id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if participant_exists is None:
        session.add(
            MessagingConversationParticipantModel(
                conversation_id=conversation.id,
                participant_type="customer",
                participant_id=customer.id,
                role="customer",
                can_read=True,
                can_write=True,
                joined_at=now,
                metadata_json={"source": "ac18_admin_local_seed"},
            )
        )

    message_result = await session.execute(
        select(MessagingMessageModel).where(
            MessagingMessageModel.public_id == "MSG-2026-001"
        )
    )
    message = message_result.scalar_one_or_none()
    if message is None:
        message = MessagingMessageModel(
            public_id="MSG-2026-001",
            conversation_id=conversation.id,
            sender_type="customer",
            sender_id=customer.id,
            visibility="public",
            body="Local AC-18 route smoke conversation message.",
            body_format="plain_text",
            idempotency_key="ac18-admin-route-smoke-message",
            created_at=now,
            updated_at=now,
            metadata_json={"source": "ac18_admin_local_seed"},
        )
        session.add(message)
        await session.flush()
    else:
        message.conversation_id = conversation.id
        message.sender_type = "customer"
        message.sender_id = customer.id
        message.visibility = "public"
        message.body = "Local AC-18 route smoke conversation message."
        message.updated_at = now

    conversation.last_message_id = message.id
    read_state_exists = (
        await session.execute(
            select(MessagingMessageReadStateModel.id)
            .where(
                MessagingMessageReadStateModel.conversation_id == conversation.id,
                MessagingMessageReadStateModel.participant_type == "admin",
                MessagingMessageReadStateModel.participant_id == admin.id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if read_state_exists is None:
        session.add(
            MessagingMessageReadStateModel(
                conversation_id=conversation.id,
                participant_type="admin",
                participant_id=admin.id,
                last_read_message_id=None,
                last_read_at=now,
                updated_at=now,
            )
        )
    await session.flush()
    return conversation


async def main() -> None:
    _assert_local_database()
    suffix = secrets.token_hex(5)
    password = _new_password()
    auth_service = AuthService()

    async with AsyncSessionLocal() as session:
        admin_realm = await _get_or_create_realm(
            session,
            realm_key="admin",
            realm_type="admin",
            display_name="Admin",
        )
        customer_realm = await _get_or_create_realm(
            session,
            realm_key="customer",
            realm_type="customer",
            display_name="Customer",
        )
        admin = AdminUserModel(
            login=f"ac18_admin_{suffix}",
            email=f"ac18-admin-{suffix}@example.invalid",
            auth_realm_id=admin_realm.id,
            password_hash=await auth_service.hash_password(password),
            role="owner/super_admin",
            is_active=True,
            is_email_verified=True,
            status="active",
            language="en",
            timezone="UTC",
            display_name="AC-18 Live Admin Operator",
            totp_enabled=False,
            notification_prefs={},
        )
        session.add(admin)
        await session.flush()
        customer = await _get_or_create_mobile_customer(
            session, auth_service, customer_realm=customer_realm
        )
        support_ticket = await _get_or_create_support_ticket(
            session, customer=customer, admin=admin
        )
        privacy_request = await _get_or_create_privacy_request(
            session,
            customer=customer,
            customer_realm=customer_realm,
            ticket=support_ticket,
        )
        conversation = await _get_or_create_messaging_conversation(
            session,
            customer=customer,
            admin=admin,
            support_ticket=support_ticket,
        )
        await session.commit()
        await session.refresh(admin)
        await session.refresh(customer)
        await session.refresh(support_ticket)
        await session.refresh(privacy_request)
        await session.refresh(conversation)

    output = {
        "created_at": datetime.now(UTC).isoformat(),
        "identifier": admin.email,
        "password": password,
        "admin_id": str(admin.id),
        "admin_realm_id": str(admin_realm.id),
        "route_samples": {
            "customers": [str(customer.id)],
            "messaging": [conversation.public_id],
            "privacy-requests": [privacy_request.public_id],
            "support": [support_ticket.public_id],
        },
        "base_url": "http://admin.localhost:3001",
        "connect_base_url": "http://127.0.0.1:3001",
        "backend_url": "http://127.0.0.1:8002",
    }
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    safe_summary = {
        "status": "seeded",
        "credentials_path": str(PRIVATE_OUTPUT.relative_to(REPO_ROOT)),
        "identifier": "<redacted>",
        "admin_id": output["admin_id"],
        "admin_realm_id": output["admin_realm_id"],
        "route_samples": output["route_samples"],
    }
    print(json.dumps(safe_summary, indent=2, sort_keys=True))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
