from fastapi import APIRouter

from src.presentation.api.v1.access_delivery_channels.routes import router as access_delivery_channels_router
from src.presentation.api.v1.addons.routes import router as addons_router
from src.presentation.api.v1.admin.customer_operations import router as admin_customer_operations_router
from src.presentation.api.v1.admin.customer_support import router as admin_customer_support_router
from src.presentation.api.v1.admin.growth import router as admin_growth_router
from src.presentation.api.v1.admin.invites import router as invites_router
from src.presentation.api.v1.admin.mobile_users import router as admin_mobile_users_router
from src.presentation.api.v1.admin.routes import router as admin_router
from src.presentation.api.v1.attribution.routes import router as attribution_router
from src.presentation.api.v1.auth.registration import router as registration_router
from src.presentation.api.v1.auth.routes import router as auth_router
from src.presentation.api.v1.billing.routes import router as billing_router
from src.presentation.api.v1.billing_descriptors.routes import router as billing_descriptors_router
from src.presentation.api.v1.checkout_sessions.routes import router as checkout_sessions_router
from src.presentation.api.v1.commercial_bindings.routes import router as commercial_bindings_router
from src.presentation.api.v1.config_profiles.routes import router as config_profiles_router
from src.presentation.api.v1.creative_approvals.routes import router as creative_approvals_router
from src.presentation.api.v1.device_credentials.routes import router as device_credentials_router
from src.presentation.api.v1.dispute_cases.routes import router as dispute_cases_router
from src.presentation.api.v1.earning_events.routes import router as earning_events_router
from src.presentation.api.v1.earning_holds.routes import router as earning_holds_router
from src.presentation.api.v1.entitlements.routes import router as entitlements_router
from src.presentation.api.v1.fcm.routes import router as fcm_router
from src.presentation.api.v1.growth_rewards.routes import router as growth_rewards_router
from src.presentation.api.v1.helix.routes import router as helix_router
from src.presentation.api.v1.hosts.routes import router as hosts_router
from src.presentation.api.v1.inbounds.routes import router as inbounds_router
from src.presentation.api.v1.invites.routes import admin_router as invite_admin_router
from src.presentation.api.v1.invites.routes import router as invite_codes_router
from src.presentation.api.v1.invoice_profiles.routes import router as invoice_profiles_router
from src.presentation.api.v1.keygen.routes import router as keygen_router
from src.presentation.api.v1.legal_documents.routes import router as legal_documents_router
from src.presentation.api.v1.merchant_profiles.routes import router as merchant_profiles_router
from src.presentation.api.v1.mobile_auth.routes import router as mobile_auth_router
from src.presentation.api.v1.monitoring.routes import router as monitoring_router
from src.presentation.api.v1.node_plugins.routes import router as node_plugins_router
from src.presentation.api.v1.notifications.routes import router as notifications_router
from src.presentation.api.v1.oauth.routes import router as oauth_router
from src.presentation.api.v1.offers.routes import router as offers_router
from src.presentation.api.v1.orders.routes import router as orders_router
from src.presentation.api.v1.partner_payout_accounts.routes import router as partner_payout_accounts_router
from src.presentation.api.v1.partner_statements.routes import router as partner_statements_router
from src.presentation.api.v1.partners.routes import router as partners_router
from src.presentation.api.v1.payment_attempts.routes import router as payment_attempts_router
from src.presentation.api.v1.payment_disputes.routes import router as payment_disputes_router
from src.presentation.api.v1.payments.routes import router as payments_router
from src.presentation.api.v1.payouts.routes import router as payouts_router
from src.presentation.api.v1.pilot_cohorts.routes import router as pilot_cohorts_router
from src.presentation.api.v1.plans.routes import router as plans_router
from src.presentation.api.v1.policies.routes import router as policies_router
from src.presentation.api.v1.policy_acceptance.routes import router as policy_acceptance_router
from src.presentation.api.v1.policy_evaluation.routes import router as policy_evaluation_router
from src.presentation.api.v1.pricebooks.routes import router as pricebooks_router
from src.presentation.api.v1.profile.routes import router as profile_router
from src.presentation.api.v1.program_eligibility.routes import router as program_eligibility_router
from src.presentation.api.v1.promo_codes.routes import router as promo_codes_router
from src.presentation.api.v1.provisioning_profiles.routes import router as provisioning_profiles_router
from src.presentation.api.v1.quotes.routes import router as quotes_router
from src.presentation.api.v1.realms.routes import router as realms_router
from src.presentation.api.v1.referral.routes import router as referral_router
from src.presentation.api.v1.refunds.routes import router as refunds_router
from src.presentation.api.v1.renewal_orders.routes import router as renewal_orders_router
from src.presentation.api.v1.reporting.routes import router as reporting_router
from src.presentation.api.v1.reserves.routes import router as reserves_router
from src.presentation.api.v1.security.routes import router as security_router
from src.presentation.api.v1.servers.routes import router as servers_router
from src.presentation.api.v1.service_identities.routes import router as service_identities_router
from src.presentation.api.v1.settings.routes import router as settings_router
from src.presentation.api.v1.settlement_periods.routes import router as settlement_periods_router
from src.presentation.api.v1.snippets.routes import router as snippets_router
from src.presentation.api.v1.squads.routes import router as squads_router
from src.presentation.api.v1.status.routes import router as status_router
from src.presentation.api.v1.subscriptions.routes import router as subscriptions_router
from src.presentation.api.v1.telegram.routes import router as telegram_router
from src.presentation.api.v1.traffic_declarations.routes import router as traffic_declarations_router
from src.presentation.api.v1.trial.routes import router as trial_router
from src.presentation.api.v1.two_factor.routes import router as two_factor_router
from src.presentation.api.v1.usage.routes import router as usage_router
from src.presentation.api.v1.users.routes import router as users_router
from src.presentation.api.v1.wallet.routes import router as wallet_router
from src.presentation.api.v1.webhooks.routes import router as webhooks_router
from src.presentation.api.v1.ws.monitoring import router as ws_monitoring_router
from src.presentation.api.v1.ws.notifications import router as ws_notifications_router
from src.presentation.api.v1.ws.tickets import router as ws_tickets_router
from src.presentation.api.v1.xray.routes import router as xray_router

API_V1_PREFIX = "/api/v1"

# Reserved canonical resource groups for the partner platform contract baseline.
# Not every family is implemented yet, but the names are frozen so later phases
# do not introduce incompatible endpoint vocabulary.
PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS = (
    "brands",
    "storefronts",
    "storefront-profiles",
    "surface-policies",
    "policies",
    "legal-documents",
    "realms",
    "principals",
    "partner-workspaces",
    "roles",
    "tokens",
    "offers",
    "pricebooks",
    "program-eligibility",
    "catalog",
    "policy-acceptance",
    "merchant-profiles",
    "invoice-profiles",
    "billing-descriptors",
    "attribution",
    "commercial-bindings",
    "quotes",
    "checkout-sessions",
    "orders",
    "order-items",
    "order-attribution-results",
    "growth-rewards",
    "renewal-orders",
    "policy-evaluation",
    "payment-attempts",
    "refunds",
    "payment-disputes",
    "earning-events",
    "earning-holds",
    "partner-statements",
    "partner-payout-accounts",
    "payouts",
    "settlement-periods",
    "reserves",
    "service-identities",
    "entitlements",
    "provisioning-profiles",
    "device-credentials",
    "access-delivery-channels",
    "risk-subjects",
    "risk-reviews",
    "governance-actions",
    "eligibility-checks",
    "traffic-declarations",
    "creative-approvals",
    "dispute-cases",
    "pilot-cohorts",
    "reporting",
    "exports",
    "postbacks",
)

api_router = APIRouter(prefix=API_V1_PREFIX)

# Auth
api_router.include_router(auth_router)
api_router.include_router(registration_router)
api_router.include_router(mobile_auth_router)
api_router.include_router(oauth_router)
api_router.include_router(two_factor_router)
api_router.include_router(security_router)
api_router.include_router(realms_router)
api_router.include_router(policies_router)
api_router.include_router(legal_documents_router)
api_router.include_router(policy_acceptance_router)

# Core resources
api_router.include_router(users_router)
api_router.include_router(profile_router)
api_router.include_router(notifications_router)
api_router.include_router(servers_router)
api_router.include_router(subscriptions_router)
api_router.include_router(plans_router)
api_router.include_router(addons_router)
api_router.include_router(offers_router)
api_router.include_router(pricebooks_router)
api_router.include_router(program_eligibility_router)
api_router.include_router(merchant_profiles_router)
api_router.include_router(invoice_profiles_router)
api_router.include_router(billing_descriptors_router)
api_router.include_router(attribution_router)
api_router.include_router(commercial_bindings_router)
api_router.include_router(growth_rewards_router)
api_router.include_router(renewal_orders_router)
api_router.include_router(policy_evaluation_router)
api_router.include_router(reporting_router)
api_router.include_router(quotes_router)
api_router.include_router(checkout_sessions_router)
api_router.include_router(orders_router)
api_router.include_router(payment_attempts_router)
api_router.include_router(refunds_router)
api_router.include_router(payment_disputes_router)
api_router.include_router(traffic_declarations_router)
api_router.include_router(creative_approvals_router)
api_router.include_router(dispute_cases_router)
api_router.include_router(pilot_cohorts_router)
api_router.include_router(earning_events_router)
api_router.include_router(earning_holds_router)
api_router.include_router(partner_statements_router)
api_router.include_router(partner_payout_accounts_router)
api_router.include_router(payouts_router)
api_router.include_router(settlement_periods_router)
api_router.include_router(reserves_router)
api_router.include_router(service_identities_router)
api_router.include_router(entitlements_router)
api_router.include_router(provisioning_profiles_router)
api_router.include_router(device_credentials_router)
api_router.include_router(access_delivery_channels_router)
api_router.include_router(helix_router)
api_router.include_router(usage_router)
api_router.include_router(trial_router)

# Payments & billing
api_router.include_router(payments_router)
api_router.include_router(billing_router)

# Codes & wallet
api_router.include_router(invite_codes_router)
api_router.include_router(invite_admin_router)
api_router.include_router(promo_codes_router)
api_router.include_router(referral_router)
api_router.include_router(partners_router)
api_router.include_router(wallet_router)

# Monitoring & admin
api_router.include_router(status_router)
api_router.include_router(monitoring_router)
api_router.include_router(admin_router)
api_router.include_router(invites_router)
api_router.include_router(admin_growth_router)
api_router.include_router(admin_mobile_users_router)
api_router.include_router(admin_customer_support_router)
api_router.include_router(admin_customer_operations_router)

# Webhooks & integrations
api_router.include_router(webhooks_router)
api_router.include_router(telegram_router)

# Push notifications
api_router.include_router(fcm_router)

# VPN management
api_router.include_router(hosts_router)
api_router.include_router(config_profiles_router)
api_router.include_router(inbounds_router)
api_router.include_router(node_plugins_router)
api_router.include_router(squads_router)
api_router.include_router(snippets_router)
api_router.include_router(keygen_router)
api_router.include_router(xray_router)
api_router.include_router(settings_router)

# WebSocket
api_router.include_router(ws_monitoring_router)
api_router.include_router(ws_notifications_router)
api_router.include_router(ws_tickets_router)
