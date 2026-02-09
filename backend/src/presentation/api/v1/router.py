from fastapi import APIRouter

from src.presentation.api.v1.auth.routes import router as auth_router
from src.presentation.api.v1.auth.registration import router as registration_router
from src.presentation.api.v1.mobile_auth.routes import router as mobile_auth_router
from src.presentation.api.v1.oauth.routes import router as oauth_router
from src.presentation.api.v1.two_factor.routes import router as two_factor_router
from src.presentation.api.v1.users.routes import router as users_router
from src.presentation.api.v1.servers.routes import router as servers_router
from src.presentation.api.v1.monitoring.routes import router as monitoring_router
from src.presentation.api.v1.payments.routes import router as payments_router
from src.presentation.api.v1.webhooks.routes import router as webhooks_router
from src.presentation.api.v1.telegram.routes import router as telegram_router
from src.presentation.api.v1.admin.routes import router as admin_router
from src.presentation.api.v1.admin.invites import router as invites_router
from src.presentation.api.v1.subscriptions.routes import router as subscriptions_router
from src.presentation.api.v1.plans.routes import router as plans_router
from src.presentation.api.v1.billing.routes import router as billing_router
from src.presentation.api.v1.hosts.routes import router as hosts_router
from src.presentation.api.v1.config_profiles.routes import router as config_profiles_router
from src.presentation.api.v1.inbounds.routes import router as inbounds_router
from src.presentation.api.v1.squads.routes import router as squads_router
from src.presentation.api.v1.snippets.routes import router as snippets_router
from src.presentation.api.v1.keygen.routes import router as keygen_router
from src.presentation.api.v1.xray.routes import router as xray_router
from src.presentation.api.v1.settings.routes import router as settings_router
from src.presentation.api.v1.status.routes import router as status_router
from src.presentation.api.v1.ws.monitoring import router as ws_monitoring_router
from src.presentation.api.v1.ws.notifications import router as ws_notifications_router
from src.presentation.api.v1.ws.tickets import router as ws_tickets_router

api_router = APIRouter(prefix="/api/v1")

# Auth
api_router.include_router(auth_router)
api_router.include_router(registration_router)
api_router.include_router(mobile_auth_router)
api_router.include_router(oauth_router)
api_router.include_router(two_factor_router)

# Core resources
api_router.include_router(users_router)
api_router.include_router(servers_router)
api_router.include_router(subscriptions_router)
api_router.include_router(plans_router)

# Payments & billing
api_router.include_router(payments_router)
api_router.include_router(billing_router)

# Monitoring & admin
api_router.include_router(status_router)
api_router.include_router(monitoring_router)
api_router.include_router(admin_router)
api_router.include_router(invites_router)

# Webhooks & integrations
api_router.include_router(webhooks_router)
api_router.include_router(telegram_router)

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
