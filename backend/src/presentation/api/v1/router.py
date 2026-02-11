from fastapi import APIRouter

from src.presentation.api.v1.admin.invites import router as invites_router
from src.presentation.api.v1.admin.routes import router as admin_router
from src.presentation.api.v1.auth.registration import router as registration_router
from src.presentation.api.v1.auth.routes import router as auth_router
from src.presentation.api.v1.billing.routes import router as billing_router
from src.presentation.api.v1.config_profiles.routes import router as config_profiles_router
from src.presentation.api.v1.fcm.routes import router as fcm_router
from src.presentation.api.v1.hosts.routes import router as hosts_router
from src.presentation.api.v1.inbounds.routes import router as inbounds_router
from src.presentation.api.v1.invites.routes import admin_router as invite_admin_router
from src.presentation.api.v1.invites.routes import router as invite_codes_router
from src.presentation.api.v1.keygen.routes import router as keygen_router
from src.presentation.api.v1.mobile_auth.routes import router as mobile_auth_router
from src.presentation.api.v1.monitoring.routes import router as monitoring_router
from src.presentation.api.v1.notifications.routes import router as notifications_router
from src.presentation.api.v1.oauth.routes import router as oauth_router
from src.presentation.api.v1.partners.routes import router as partners_router
from src.presentation.api.v1.payments.routes import router as payments_router
from src.presentation.api.v1.plans.routes import router as plans_router
from src.presentation.api.v1.profile.routes import router as profile_router
from src.presentation.api.v1.promo_codes.routes import router as promo_codes_router
from src.presentation.api.v1.referral.routes import router as referral_router
from src.presentation.api.v1.security.routes import router as security_router
from src.presentation.api.v1.servers.routes import router as servers_router
from src.presentation.api.v1.settings.routes import router as settings_router
from src.presentation.api.v1.snippets.routes import router as snippets_router
from src.presentation.api.v1.squads.routes import router as squads_router
from src.presentation.api.v1.status.routes import router as status_router
from src.presentation.api.v1.subscriptions.routes import router as subscriptions_router
from src.presentation.api.v1.telegram.routes import router as telegram_router
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

api_router = APIRouter(prefix="/api/v1")

# Auth
api_router.include_router(auth_router)
api_router.include_router(registration_router)
api_router.include_router(mobile_auth_router)
api_router.include_router(oauth_router)
api_router.include_router(two_factor_router)
api_router.include_router(security_router)

# Core resources
api_router.include_router(users_router)
api_router.include_router(profile_router)
api_router.include_router(notifications_router)
api_router.include_router(servers_router)
api_router.include_router(subscriptions_router)
api_router.include_router(plans_router)
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

# Webhooks & integrations
api_router.include_router(webhooks_router)
api_router.include_router(telegram_router)

# Push notifications
api_router.include_router(fcm_router)

# VPN management
api_router.include_router(hosts_router)
api_router.include_router(config_profiles_router)
api_router.include_router(inbounds_router)
api_router.include_router(squads_router)
api_router.include_router(snippets_router)
api_router.include_router(keygen_router)
api_router.include_router(xray_router)
api_router.include_router(settings_router)

# WebSocket
api_router.include_router(ws_monitoring_router)
api_router.include_router(ws_notifications_router)
api_router.include_router(ws_tickets_router)
