"""Public client capability response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class ClientAuthCapabilities(BaseModel):
    email_password: bool = True
    magic_link: bool = True
    telegram: bool = True


class ClientPaymentCapabilities(BaseModel):
    web_checkout: bool = False
    telegram_stars: bool = False
    cryptobot: bool = False
    manual_invoice: bool = False
    autorenewal: bool = False


class ClientGrowthCapabilities(BaseModel):
    invites: bool = False
    referral: bool = False
    promo_codes: bool = False
    gift_codes: bool = False
    checkout_code_discounts: bool = False
    growth_hub: bool = False


class ClientSubscriptionCapabilities(BaseModel):
    multi_subscription: bool = True
    selected_subscription_required: bool = True
    addons: bool = False
    upgrade: bool = True
    trial: bool = False
    paid_provisioning: bool = False


class ClientPartnerCapabilities(BaseModel):
    portal: bool = False
    applications: bool = False
    codes: bool = False
    attribution: bool = False
    storefronts: bool = False
    reporting: bool = False
    settlement_sandbox: bool = False
    webhooks: bool = False
    payouts: bool = False
    event_backbone: bool = False


class ClientSiteCapabilities(BaseModel):
    customer_site_mode: Literal["full_site", "cabinet_only", "maintenance"] = "full_site"
    cabinet_only: bool = False
    public_hosts: list[str] = Field(default_factory=list)
    cabinet_hosts: list[str] = Field(default_factory=list)
    cabinet_destination_path: str = "/dashboard"
    allowed_path_prefixes: list[str] = Field(default_factory=list)
    preserve_query_keys: list[str] = Field(default_factory=list)
    registration_policy_independent: bool = True


class ClientOnboardingCapabilities(BaseModel):
    post_registration_code_prompt: bool = False
    web_otp: bool = False
    telegram_miniapp: bool = False
    state_store: bool = False
    flow_key: str = "post_registration_growth_code_v1"
    version: int = 1
    allowed_code_types: list[Literal["promo", "invite", "gift"]] = Field(default_factory=list)
    allow_referral_input: bool = False
    allow_partner_input: bool = False
    available: bool = False


class ClientCapabilityResponse(BaseModel):
    auth: ClientAuthCapabilities = Field(default_factory=ClientAuthCapabilities)
    payments: ClientPaymentCapabilities
    growth: ClientGrowthCapabilities
    subscriptions: ClientSubscriptionCapabilities
    partner: ClientPartnerCapabilities
    site: ClientSiteCapabilities = Field(default_factory=ClientSiteCapabilities)
    onboarding: ClientOnboardingCapabilities = Field(default_factory=ClientOnboardingCapabilities)
