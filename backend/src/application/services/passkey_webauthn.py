"""WebAuthn ceremony helpers for CyberVPN passkeys."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json_dict
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from src.config.settings import settings
from src.infrastructure.cache.passkey_challenges import PasskeyChallengeRecord
from src.infrastructure.database.models.passkey_credential_model import PasskeyCredentialModel


class PasskeyVerificationError(Exception):
    """Raised when a WebAuthn response cannot be verified."""


@dataclass(frozen=True)
class PasskeyRegistrationVerification:
    credential_id_b64: str
    credential_id_hash: str
    credential_public_key: bytes
    sign_count: int
    aaguid: str | None
    attestation_format: str | None
    credential_type: str
    user_verified: bool
    device_type: str | None
    backed_up: bool
    transports: list[str]
    authenticator_attachment: str | None


@dataclass(frozen=True)
class PasskeyAuthenticationVerification:
    credential_id_b64: str
    credential_id_hash: str
    new_sign_count: int
    user_verified: bool
    device_type: str | None
    backed_up: bool


def passkey_credential_hash(credential_id: bytes) -> str:
    return sha256(credential_id).hexdigest()


def passkey_user_handle_bytes(
    *,
    auth_realm_id: UUID,
    principal_class: str,
    principal_subject: str,
) -> bytes:
    source = f"{auth_realm_id}:{principal_class}:{principal_subject}".encode()
    return sha256(source).digest()


def passkey_user_handle(
    *,
    auth_realm_id: UUID,
    principal_class: str,
    principal_subject: str,
) -> str:
    return bytes_to_base64url(
        passkey_user_handle_bytes(
            auth_realm_id=auth_realm_id,
            principal_class=principal_class,
            principal_subject=principal_subject,
        )
    )


def passkey_identifier_hash(identifier: str | None) -> str | None:
    if not identifier:
        return None
    normalized = identifier.strip().lower()
    if not normalized:
        return None
    return sha256(normalized.encode("utf-8")).hexdigest()


def credential_hash_from_browser_payload(payload: dict) -> str:
    raw_id = payload.get("rawId") or payload.get("raw_id") or payload.get("id")
    if not isinstance(raw_id, str) or not raw_id:
        raise PasskeyVerificationError("passkey_credential_id_missing")
    return passkey_credential_hash(base64url_to_bytes(raw_id))


def _transports_from_payload(payload: dict) -> list[str]:
    response = payload.get("response")
    if not isinstance(response, dict):
        return []
    transports = response.get("transports")
    if not isinstance(transports, list):
        return []
    return [str(item) for item in transports if isinstance(item, str) and item]


def _authenticator_attachment_from_payload(payload: dict) -> str | None:
    attachment = payload.get("authenticatorAttachment")
    return attachment if isinstance(attachment, str) and attachment else None


class PasskeyWebAuthnService:
    def registration_options(
        self,
        *,
        rp_id: str,
        rp_name: str,
        user_name: str,
        user_display_name: str,
        user_handle: bytes,
        exclude_credentials: list[PasskeyCredentialModel],
        timeout_ms: int | None = None,
    ) -> tuple[dict, bytes]:
        descriptors = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential.credential_id))
            for credential in exclude_credentials
        ]
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_name=user_name,
            user_display_name=user_display_name,
            user_id=user_handle,
            timeout=timeout_ms if timeout_ms is not None else settings.passkey_browser_timeout_ms,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=descriptors,
        )
        return options_to_json_dict(options), options.challenge

    def authentication_options(
        self,
        *,
        rp_id: str,
        allow_credentials: list[PasskeyCredentialModel],
        timeout_ms: int | None = None,
    ) -> tuple[dict, bytes]:
        descriptors = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential.credential_id))
            for credential in allow_credentials
        ]
        options = generate_authentication_options(
            rp_id=rp_id,
            timeout=timeout_ms if timeout_ms is not None else settings.passkey_browser_timeout_ms,
            allow_credentials=descriptors,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return options_to_json_dict(options), options.challenge

    def verify_registration(
        self,
        *,
        payload: dict,
        challenge: PasskeyChallengeRecord,
    ) -> PasskeyRegistrationVerification:
        try:
            verified = verify_registration_response(
                credential=payload,
                expected_challenge=base64url_to_bytes(challenge.challenge_b64),
                expected_rp_id=challenge.rp_id,
                expected_origin=challenge.expected_origin,
                require_user_verification=challenge.require_user_verification,
            )
        except InvalidRegistrationResponse as exc:
            raise PasskeyVerificationError("passkey_registration_invalid") from exc

        credential_id_b64 = bytes_to_base64url(verified.credential_id)
        return PasskeyRegistrationVerification(
            credential_id_b64=credential_id_b64,
            credential_id_hash=passkey_credential_hash(verified.credential_id),
            credential_public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            aaguid=verified.aaguid,
            attestation_format=str(verified.fmt.value if hasattr(verified.fmt, "value") else verified.fmt),
            credential_type=str(
                verified.credential_type.value
                if hasattr(verified.credential_type, "value")
                else verified.credential_type
            ),
            user_verified=verified.user_verified,
            device_type=str(
                verified.credential_device_type.value
                if hasattr(verified.credential_device_type, "value")
                else verified.credential_device_type
            ),
            backed_up=verified.credential_backed_up,
            transports=_transports_from_payload(payload),
            authenticator_attachment=_authenticator_attachment_from_payload(payload),
        )

    def verify_authentication(
        self,
        *,
        payload: dict,
        challenge: PasskeyChallengeRecord,
        credential: PasskeyCredentialModel,
    ) -> PasskeyAuthenticationVerification:
        try:
            verified = verify_authentication_response(
                credential=payload,
                expected_challenge=base64url_to_bytes(challenge.challenge_b64),
                expected_rp_id=challenge.rp_id,
                expected_origin=challenge.expected_origin,
                credential_public_key=credential.credential_public_key,
                # py_webauthn rejects non-increasing counters before returning
                # new_sign_count. CyberVPN compares the stored counter after
                # ceremony verification so clone markers and audit rows can be
                # durably committed before the endpoint fails closed.
                credential_current_sign_count=0,
                require_user_verification=challenge.require_user_verification,
            )
        except InvalidAuthenticationResponse as exc:
            raise PasskeyVerificationError("passkey_authentication_invalid") from exc

        credential_id_b64 = bytes_to_base64url(verified.credential_id)
        return PasskeyAuthenticationVerification(
            credential_id_b64=credential_id_b64,
            credential_id_hash=passkey_credential_hash(verified.credential_id),
            new_sign_count=verified.new_sign_count,
            user_verified=verified.user_verified,
            device_type=str(
                verified.credential_device_type.value
                if hasattr(verified.credential_device_type, "value")
                else verified.credential_device_type
            ),
            backed_up=verified.credential_backed_up,
        )


def clone_options_payload(options: dict) -> dict:
    """Return a JSON-compatible options payload detached from dataclass internals."""

    return json.loads(json.dumps(options))
