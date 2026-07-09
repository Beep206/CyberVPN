"""Pydantic schemas for Passkey/WebAuthn API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class PasskeyPolicyResponse(BaseModel):
    enabled: bool
    configured_enabled: bool = Field(serialization_alias="configuredEnabled")
    global_enabled: bool = Field(serialization_alias="globalEnabled")
    surface_enabled: bool = Field(serialization_alias="surfaceEnabled")
    surface: str
    realm_key: str
    rp_id: str
    rp_name: str
    allowed_origins: list[str] = Field(serialization_alias="allowedOrigins")
    user_verification: str = Field(default="required", serialization_alias="userVerification")
    conditional_ui_enabled: bool = Field(serialization_alias="conditionalUiEnabled")
    registration_enabled: bool = Field(serialization_alias="registrationEnabled")
    authentication_enabled: bool = Field(serialization_alias="authenticationEnabled")
    reauthentication_enabled: bool = Field(serialization_alias="reauthenticationEnabled")
    security_dashboard_enabled: bool | None = Field(default=None, serialization_alias="securityDashboardEnabled")
    workspace_policy_enabled: bool | None = Field(default=None, serialization_alias="workspacePolicyEnabled")
    admin_counts_as_mfa: bool = Field(serialization_alias="adminCountsAsMfa")
    challenge_ttl_seconds: int = Field(serialization_alias="challengeTtlSeconds")
    browser_timeout_ms: int = Field(serialization_alias="browserTimeoutMs")
    fresh_auth_ttl_seconds: int | None = Field(default=None, serialization_alias="freshAuthTtlSeconds")
    policy_source: str = Field(default="settings", serialization_alias="policySource")
    updated_at: datetime | None = Field(default=None, serialization_alias="updatedAt")
    updated_by: UUID | None = Field(default=None, serialization_alias="updatedBy")


class UpdateAdminPasskeyPolicyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_by_name=True, validate_by_alias=True)

    enabled: bool | None = None
    registration_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("registrationEnabled", "registration_enabled"),
    )
    authentication_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("authenticationEnabled", "authentication_enabled"),
    )
    reauthentication_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("reauthenticationEnabled", "reauthentication_enabled"),
    )
    conditional_ui_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("conditionalUiEnabled", "conditional_ui_enabled"),
    )
    security_dashboard_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("securityDashboardEnabled", "security_dashboard_enabled"),
    )
    admin_counts_as_mfa: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("adminCountsAsMfa", "admin_counts_as_mfa"),
    )
    challenge_ttl_seconds: int | None = Field(
        default=None,
        ge=30,
        le=300,
        validation_alias=AliasChoices("challengeTtlSeconds", "challenge_ttl_seconds"),
    )
    browser_timeout_ms: int | None = Field(
        default=None,
        ge=15000,
        le=120000,
        validation_alias=AliasChoices("browserTimeoutMs", "browser_timeout_ms"),
    )
    fresh_auth_ttl_seconds: int | None = Field(
        default=None,
        ge=60,
        le=900,
        validation_alias=AliasChoices("freshAuthTtlSeconds", "fresh_auth_ttl_seconds"),
    )
    change_reason: str | None = Field(
        default=None,
        max_length=500,
        validation_alias=AliasChoices("changeReason", "change_reason"),
    )

    @model_validator(mode="after")
    def require_policy_update(self) -> UpdateAdminPasskeyPolicyRequest:
        if any(
            value is not None
            for value in (
                self.enabled,
                self.registration_enabled,
                self.authentication_enabled,
                self.reauthentication_enabled,
                self.conditional_ui_enabled,
                self.security_dashboard_enabled,
                self.admin_counts_as_mfa,
                self.challenge_ttl_seconds,
                self.browser_timeout_ms,
                self.fresh_auth_ttl_seconds,
            )
        ):
            return self
        raise ValueError("At least one passkey policy field is required.")


class PasskeyComplianceCredentialResponse(BaseModel):
    id: UUID
    label: str
    status: str
    realm_key: str = Field(serialization_alias="realmKey")
    principal_class: str = Field(serialization_alias="principalClass")
    principal_subject: str = Field(serialization_alias="principalSubject")
    surface: str
    rp_id: str = Field(serialization_alias="rpId")
    credential_id_hash_prefix: str = Field(serialization_alias="credentialIdHashPrefix")
    credential_type: str = Field(serialization_alias="credentialType")
    device_type: str | None = Field(serialization_alias="deviceType")
    transports: list[str]
    backed_up: bool = Field(serialization_alias="backedUp")
    user_verified: bool = Field(serialization_alias="userVerified")
    clone_suspected_at: datetime | None = Field(serialization_alias="cloneSuspectedAt")
    created_at: datetime = Field(serialization_alias="createdAt")
    last_used_at: datetime | None = Field(serialization_alias="lastUsedAt")
    revoked_at: datetime | None = Field(serialization_alias="revokedAt")


class PasskeyComplianceSummaryResponse(BaseModel):
    active_credentials: int = Field(serialization_alias="activeCredentials")
    revoked_credentials: int = Field(serialization_alias="revokedCredentials")
    clone_suspected_credentials: int = Field(serialization_alias="cloneSuspectedCredentials")
    principals_with_active_passkeys: int = Field(serialization_alias="principalsWithActivePasskeys")
    stale_credentials: int = Field(serialization_alias="staleCredentials")
    generated_at: datetime = Field(serialization_alias="generatedAt")


class PasskeyComplianceResponse(BaseModel):
    policy: PasskeyPolicyResponse
    summary: PasskeyComplianceSummaryResponse
    credentials: list[PasskeyComplianceCredentialResponse]


class PartnerWorkspacePasskeyOperatorComplianceResponse(BaseModel):
    workspace_id: UUID = Field(serialization_alias="workspaceId")
    active_members: int = Field(serialization_alias="activeMembers")
    operators_with_active_passkeys: int = Field(serialization_alias="operatorsWithActivePasskeys")
    operators_missing_active_passkeys: int = Field(serialization_alias="operatorsMissingActivePasskeys")


class PartnerWorkspacePasskeyPolicyResponse(BaseModel):
    workspace_id: UUID = Field(serialization_alias="workspaceId")
    workspace_key: str = Field(serialization_alias="workspaceKey")
    workspace_status: str = Field(serialization_alias="workspaceStatus")
    workspace_passkeys_preferred: bool = Field(serialization_alias="workspacePasskeysPreferred")
    workspace_mfa_required: bool = Field(serialization_alias="workspaceMfaRequired")
    workspace_policy_updated_at: datetime | None = Field(
        default=None,
        serialization_alias="workspacePolicyUpdatedAt",
    )
    policy: PasskeyPolicyResponse
    operator_compliance: PartnerWorkspacePasskeyOperatorComplianceResponse = Field(
        serialization_alias="operatorCompliance"
    )


class PartnerWorkspacePasskeyComplianceResponse(PartnerWorkspacePasskeyPolicyResponse):
    summary: PasskeyComplianceSummaryResponse
    credentials: list[PasskeyComplianceCredentialResponse]


class UpdatePartnerWorkspacePasskeyPolicyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_by_name=True, validate_by_alias=True)

    prefer_passkeys: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("preferPasskeys", "prefer_passkeys"),
    )
    require_mfa_for_workspace: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("requireMfaForWorkspace", "require_mfa_for_workspace"),
    )
    change_reason: str | None = Field(
        default=None,
        max_length=500,
        validation_alias=AliasChoices("changeReason", "change_reason"),
    )

    @model_validator(mode="after")
    def require_policy_update(self) -> UpdatePartnerWorkspacePasskeyPolicyRequest:
        if self.prefer_passkeys is not None or self.require_mfa_for_workspace is not None:
            return self
        raise ValueError("At least one partner workspace passkey policy field is required.")


class PasskeyOptionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_by_name=True, validate_by_alias=True)

    challenge_id: str = Field(serialization_alias="challengeId")
    public_key: dict[str, Any] = Field(serialization_alias="publicKey")
    expires_at: datetime = Field(serialization_alias="expiresAt")


class PasskeyRegistrationOptionsRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)


class PasskeyRegistrationVerifyRequest(BaseModel):
    challenge_id: str = Field(
        ...,
        min_length=1,
        max_length=80,
        validation_alias=AliasChoices("challengeId", "challenge_id"),
    )
    credential: dict[str, Any]
    label: str | None = Field(default=None, min_length=1, max_length=120)


class PasskeyAuthenticationOptionsRequest(BaseModel):
    identifier: str | None = Field(default=None, min_length=1, max_length=255)
    conditional: bool = False


class PasskeyAuthenticationVerifyRequest(BaseModel):
    challenge_id: str = Field(
        ...,
        min_length=1,
        max_length=80,
        validation_alias=AliasChoices("challengeId", "challenge_id"),
    )
    credential: dict[str, Any]


class PasskeyAuthenticationVerifyResponse(BaseModel):
    auth_realm_id: UUID | None = None
    auth_realm_key: str | None = None
    audience: str | None = None
    principal_type: str | None = None
    scope_family: str | None = None
    requires_2fa: bool = False
    tfa_token: str | None = None


class PasskeyReauthenticationOptionsRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=120)


class PasskeyReauthenticationVerifyRequest(BaseModel):
    challenge_id: str = Field(
        ...,
        min_length=1,
        max_length=80,
        validation_alias=AliasChoices("challengeId", "challenge_id"),
    )
    credential: dict[str, Any]
    action: str = Field(..., min_length=1, max_length=120)


class PasskeyReauthenticationVerifyResponse(BaseModel):
    fresh_auth_grant_id: str = Field(serialization_alias="freshAuthGrantId")
    expires_at: datetime = Field(serialization_alias="expiresAt")


class PasskeyCredentialResponse(BaseModel):
    id: UUID
    label: str
    status: str
    credential_type: str = Field(serialization_alias="credentialType")
    device_type: str | None = Field(serialization_alias="deviceType")
    transports: list[str]
    backed_up: bool = Field(serialization_alias="backedUp")
    user_verified: bool = Field(serialization_alias="userVerified")
    created_at: datetime = Field(serialization_alias="createdAt")
    last_used_at: datetime | None = Field(serialization_alias="lastUsedAt")
    revoked_at: datetime | None = Field(serialization_alias="revokedAt")


class PasskeyCredentialListResponse(BaseModel):
    credentials: list[PasskeyCredentialResponse]


class PasskeyRenameRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)


class PasskeyDeleteResponse(BaseModel):
    id: UUID
    status: str
