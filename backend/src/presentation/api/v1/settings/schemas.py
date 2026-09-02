"""Typed Remnawave 3.4.3 system-settings contracts."""

from __future__ import annotations

from typing import Any

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, model_validator


class RemnawaveSettingsModel(BaseModel):
    """Strict camel-case model for the pinned Remnawave settings contract."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class PasskeySettings(RemnawaveSettingsModel):
    enabled: bool
    rp_id: str | None = Field(alias="rpId")
    origin: str | None


class OAuthClientSettings(RemnawaveSettingsModel):
    enabled: bool
    client_id: str | None = Field(alias="clientId")
    client_secret: str | None = Field(alias="clientSecret")
    allowed_emails: list[str] = Field(alias="allowedEmails")


class PocketIdSettings(OAuthClientSettings):
    frontend_domain: str | None = Field(alias="frontendDomain")
    plain_domain: str | None = Field(alias="plainDomain")


class KeycloakSettings(OAuthClientSettings):
    realm: str | None
    frontend_domain: str | None = Field(alias="frontendDomain")
    keycloak_domain: str | None = Field(alias="keycloakDomain")


def _default_keycloak_settings() -> KeycloakSettings:
    return KeycloakSettings.model_validate(
        {
            "enabled": False,
            "realm": None,
            "clientId": None,
            "clientSecret": None,
            "frontendDomain": None,
            "keycloakDomain": None,
            "allowedEmails": [],
        }
    )


class GenericOAuthSettings(OAuthClientSettings):
    with_pkce: bool = Field(alias="withPkce")
    authorization_url: str | None = Field(alias="authorizationUrl")
    token_url: str | None = Field(alias="tokenUrl")
    frontend_domain: str | None = Field(alias="frontendDomain")


def _default_generic_oauth_settings() -> GenericOAuthSettings:
    return GenericOAuthSettings.model_validate(
        {
            "enabled": False,
            "clientId": None,
            "clientSecret": None,
            "withPkce": False,
            "authorizationUrl": None,
            "tokenUrl": None,
            "frontendDomain": None,
            "allowedEmails": [],
        }
    )


class TelegramOAuthSettings(RemnawaveSettingsModel):
    enabled: bool
    client_id: str | None = Field(alias="clientId")
    client_secret: str | None = Field(alias="clientSecret")
    allowed_ids: list[str] = Field(alias="allowedIds")
    frontend_domain: str | None = Field(alias="frontendDomain")


def _default_telegram_oauth_settings() -> TelegramOAuthSettings:
    return TelegramOAuthSettings.model_validate(
        {
            "enabled": False,
            "clientId": None,
            "clientSecret": None,
            "allowedIds": [],
            "frontendDomain": None,
        }
    )


class OAuth2Settings(RemnawaveSettingsModel):
    github: OAuthClientSettings
    pocketid: PocketIdSettings
    yandex: OAuthClientSettings
    keycloak: KeycloakSettings = Field(default_factory=_default_keycloak_settings)
    generic: GenericOAuthSettings = Field(default_factory=_default_generic_oauth_settings)
    telegram: TelegramOAuthSettings = Field(default_factory=_default_telegram_oauth_settings)


class PasswordSettings(RemnawaveSettingsModel):
    enabled: bool


class BrandingSettings(RemnawaveSettingsModel):
    title: str | None
    logo_url: AnyUrl | None = Field(alias="logoUrl")


class RemnawaveSettingsResponse(RemnawaveSettingsModel):
    """Unwrapped ``response`` object returned by Remnawave 3.4.3."""

    passkey_settings: PasskeySettings | None = Field(alias="passkeySettings")
    oauth2_settings: OAuth2Settings | None = Field(alias="oauth2Settings")
    password_settings: PasswordSettings | None = Field(alias="passwordSettings")
    branding_settings: BrandingSettings | None = Field(alias="brandingSettings")


class UpdateRemnawaveSettingsRequest(RemnawaveSettingsModel):
    """PATCH body whose four target fields are optional but never nullable."""

    passkey_settings: PasskeySettings | None = Field(default=None, alias="passkeySettings")
    oauth2_settings: OAuth2Settings | None = Field(default=None, alias="oauth2Settings")
    password_settings: PasswordSettings | None = Field(default=None, alias="passwordSettings")
    branding_settings: BrandingSettings | None = Field(default=None, alias="brandingSettings")

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_sections(cls, value: Any) -> Any:
        if isinstance(value, dict):
            nullable_keys = {
                "passkeySettings",
                "passkey_settings",
                "oauth2Settings",
                "oauth2_settings",
                "passwordSettings",
                "password_settings",
                "brandingSettings",
                "branding_settings",
            }
            if any(key in value and value[key] is None for key in nullable_keys):
                raise ValueError("Remnawave settings PATCH sections cannot be null")
        return value


class CreateSettingRequest(BaseModel):
    """Legacy request retained only so the removed create route can return 503."""

    key: str = Field(min_length=1, max_length=100)
    value: Any
    description: str | None = Field(default=None, max_length=500)
    is_public: bool = False


class UpdateSettingRequest(BaseModel):
    """Legacy by-id request retained only so the removed route can return 503."""

    value: Any | None = None
    description: str | None = Field(default=None, max_length=500)
    is_public: bool | None = None
