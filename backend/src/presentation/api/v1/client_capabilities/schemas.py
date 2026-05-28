"""Public client capability response schemas."""

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
    invites: bool = True
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


class ClientCapabilityResponse(BaseModel):
    auth: ClientAuthCapabilities = Field(default_factory=ClientAuthCapabilities)
    payments: ClientPaymentCapabilities
    growth: ClientGrowthCapabilities
    subscriptions: ClientSubscriptionCapabilities
    partner: ClientPartnerCapabilities

