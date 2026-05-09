#!/usr/bin/env python3
"""Local mock API for S1-TG-004 Mini App cabinet evidence.

The mock serves only local, non-secret fixtures needed by the frontend Mini App
routes. It is intentionally small and deterministic so screenshots can be
reproduced without production Telegram/payment/Remnawave credentials.
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


GENERATED_AT = "2026-05-04T00:00:00Z"
USER_ID = "user-s1-tg-004"


def json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type, authorization, x-idempotency-key")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def empty_response(handler: BaseHTTPRequestHandler, status: HTTPStatus = HTTPStatus.NO_CONTENT) -> None:
    handler.send_response(status.value)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type, authorization, x-idempotency-key")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.end_headers()


def plan(
    *,
    code: str,
    duration_days: int,
    price_usd: float,
    devices: int,
    sort_order: int,
    modes: list[str],
    pool: list[str],
    stars: int,
) -> dict[str, Any]:
    display_name = code.title()
    return {
        "uuid": f"plan-{code}-{duration_days}",
        "name": f"{code}_{duration_days}",
        "plan_code": code,
        "display_name": display_name,
        "catalog_visibility": "public",
        "features": {
            "telegram_stars_amount": stars,
            "prices": {"USD": price_usd, "XTR": stars},
        },
        "devices_included": devices,
        "connection_modes": modes,
        "server_pool": pool,
        "support_sla": "standard",
        "dedicated_ip": {"included": 0, "eligible": code in {"plus", "pro", "max"}},
        "duration_days": duration_days,
        "traffic_limit_bytes": None,
        "traffic_policy": {"mode": "fair_use", "display_label": "Unlimited"},
        "sale_channels": ["miniapp"],
        "trial_eligible": code in {"basic", "plus"},
        "price_usd": price_usd,
        "price_rub": None,
        "sort_order": sort_order,
        "is_active": True,
        "invite_bundle": {
            "count": 2 if duration_days >= 180 else 0,
            "friend_days": 14 if duration_days >= 180 else 0,
            "expiry_days": 60 if duration_days >= 180 else 0,
        },
    }


def bootstrap_payload() -> dict[str, Any]:
    return {
        "session": {
            "authenticated": True,
            "userId": USER_ID,
            "telegramUserId": "123456789",
            "authRealm": "customer",
        },
        "runtime": {
            "surface": "telegram_miniapp",
            "tenant": {"kind": "platform"},
            "brand": {
                "name": "CyberVPN",
                "primaryColor": "#00ffff",
                "supportUrl": "https://t.me/cybervpn_bot?start=support",
                "legalName": "CyberVPN S1 Local Evidence",
            },
            "commercialPolicy": {
                "pricingPolicyId": "cybervpn-s1-miniapp",
                "currencyPolicy": "usd_xtr",
                "trialPolicyId": "cybervpn-s1-trial",
            },
            "attribution": {
                "source": "telegram",
                "surface": "miniapp",
                "startParam": "s1-tg-004",
            },
        },
        "user": {
            "firstName": "Sasha",
            "username": "s1_tg_004",
            "photoUrl": None,
            "locale": "en-EN",
            "rtl": False,
        },
        "subscription": {
            "status": "active",
            "planId": "plan-plus-30",
            "planName": "Plus Beta",
            "expiresAt": "2026-06-03T00:00:00Z",
            "autoRenew": False,
        },
        "trial": {
            "eligible": False,
            "reason": "active_subscription",
            "durationDays": 3,
            "trialStart": None,
            "trialEnd": None,
            "daysRemaining": 0,
        },
        "wallet": {"balance": 27.5, "currency": "USD", "bonusesAvailable": 0},
        "devices": {"activeCount": 2, "limit": 5, "hasConfig": True},
        "usage": {
            "bandwidthUsedBytes": 8589934592,
            "bandwidthLimitBytes": 214748364800,
            "connectionsActive": 1,
            "connectionsLimit": 5,
            "periodStart": "2026-05-01T00:00:00Z",
            "periodEnd": "2026-06-01T00:00:00Z",
            "lastConnectionAt": "2026-05-04T10:00:00Z",
        },
        "serviceState": {"providerName": "remnawave-local", "channelType": "telegram_miniapp"},
        "recommendedServer": {
            "id": "s1-local-node",
            "countryCode": "NL",
            "city": "Amsterdam",
            "publicName": "S1 Local Node",
            "latencyMs": 42,
            "speedMbps": 250,
            "uptimePct30d": 99.9,
            "dpiScore": 91,
            "status": "online",
            "recommendedReason": "Local S1-TG-004 smoke fixture",
        },
        "primaryCta": {"kind": "get_config", "label": "Get VPN config"},
        "referral": {"code": None, "inviteUrl": None, "shareText": None},
        "payment": {"unresolvedPaymentId": None, "lastStatus": "paid"},
        "support": {
            "url": "https://t.me/cybervpn_bot?start=support",
            "paysupportCommandAvailable": True,
        },
        "rollout": {
            "enabled": True,
            "mode": "live",
            "trialEnabled": True,
            "checkoutEnabled": True,
            "configEnabled": True,
            "accessGranted": True,
            "isCanaryUser": False,
            "gateReasonCode": None,
            "maintenanceMessage": None,
        },
        "featureFlags": {
            "miniapp_bootstrap_v1": True,
            "stage1_referral_public_ui": False,
            "stage1_checkout_codes_public_ui": False,
        },
        "freshness": {"generatedAt": GENERATED_AT},
    }


def offers_payload() -> dict[str, Any]:
    return {
        "plans": [
            plan(
                code="basic",
                duration_days=30,
                price_usd=9.99,
                devices=2,
                sort_order=1,
                modes=["standard"],
                pool=["shared_basic"],
                stars=499,
            ),
            plan(
                code="plus",
                duration_days=30,
                price_usd=14.99,
                devices=5,
                sort_order=2,
                modes=["standard", "stealth"],
                pool=["shared_plus"],
                stars=749,
            ),
            plan(
                code="plus",
                duration_days=180,
                price_usd=69.99,
                devices=5,
                sort_order=3,
                modes=["standard", "stealth"],
                pool=["shared_plus"],
                stars=3499,
            ),
            plan(
                code="pro",
                duration_days=365,
                price_usd=119.99,
                devices=10,
                sort_order=4,
                modes=["standard", "stealth", "premium"],
                pool=["shared_pro", "premium"],
                stars=5999,
            ),
            plan(
                code="max",
                duration_days=365,
                price_usd=179.99,
                devices=20,
                sort_order=5,
                modes=["standard", "stealth", "premium"],
                pool=["shared_max", "premium"],
                stars=8999,
            ),
        ],
        "addons": [],
        "trial": {
            "is_trial_active": False,
            "is_eligible": False,
            "trial_start": None,
            "trial_end": None,
            "days_remaining": 0,
        },
        "currentEntitlements": {
            "status": "active",
            "plan_uuid": "plan-plus-30",
            "plan_code": "plus",
            "display_name": "Plus Beta",
            "period_days": 30,
            "expires_at": "2026-06-03T00:00:00Z",
            "effective_entitlements": {
                "device_limit": 5,
                "display_traffic_label": "Unlimited",
                "connection_modes": ["standard", "stealth"],
                "server_pool": ["shared_plus"],
                "support_sla": "standard",
                "dedicated_ip_count": 0,
            },
            "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
            "is_trial": False,
            "addons": [],
        },
        "freshness": {"generatedAt": GENERATED_AT},
    }


def orders_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": "order-s1-tg-004-paid",
            "displayed_price": 14.99,
            "currency_code": "USD",
            "order_status": "committed",
            "settlement_status": "paid",
            "created_at": "2026-05-04T09:30:00Z",
            "items": [{"display_name": "Plus Beta 30 days"}],
        },
        {
            "id": "order-s1-tg-004-trial",
            "displayed_price": 0,
            "currency_code": "USD",
            "order_status": "committed",
            "settlement_status": "completed",
            "created_at": "2026-05-03T09:30:00Z",
            "items": [{"display_name": "3-Day Trial"}],
        },
    ]


def wallet_transactions_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": "txn-s1-tg-004-deposit",
            "amount": 27.5,
            "type": "deposit",
            "status": "completed",
            "description": "S1 local wallet deposit",
            "created_at": "2026-05-04T09:00:00Z",
        },
        {
            "id": "txn-s1-tg-004-plan",
            "amount": -14.99,
            "type": "purchase",
            "status": "completed",
            "description": "Plus Beta renewal",
            "created_at": "2026-05-04T09:30:00Z",
        },
    ]


class MiniAppMockHandler(BaseHTTPRequestHandler):
    server_version = "CyberVPNS1TG004Mock/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - http.server API
        return

    def do_OPTIONS(self) -> None:
        empty_response(self)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        payloads: dict[str, Any] = {
            "/api/v1/auth/session": auth_user_payload(),
            "/api/v1/auth/me": auth_user_payload(),
            "/api/v1/miniapp/bootstrap": bootstrap_payload(),
            "/api/v1/miniapp/offers": offers_payload(),
            "/api/v1/miniapp/config": {
                "config": "vless://s1-tg-004-local@example.invalid:443?security=reality#CyberVPN-S1",
                "configString": "vless://s1-tg-004-local@example.invalid:443?security=reality#CyberVPN-S1",
                "clientType": "vless",
                "source": "remnawave_generated",
                "isFound": True,
                "links": ["vless://s1-tg-004-local@example.invalid:443?security=reality#CyberVPN-S1"],
                "ssConfLinks": {},
                "subscriptionUrl": "https://cyber-vpn.net/sub/s1-tg-004-local",
                "generatedAt": GENERATED_AT,
            },
            "/api/v1/orders": orders_payload(),
            "/api/v1/auth/devices": {
                "devices": [
                    {
                        "device_id": "device-current",
                        "ip_address": "203.0.113.10",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
                        "last_used_at": "2026-05-04T10:00:00Z",
                        "is_current": True,
                    },
                    {
                        "device_id": "device-mobile",
                        "ip_address": "203.0.113.11",
                        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1",
                        "last_used_at": "2026-05-04T09:40:00Z",
                        "is_current": False,
                    },
                ],
            },
            "/api/v1/wallet": {"balance": 27.5, "frozen": 0, "currency": "USD"},
            "/api/v1/wallet/transactions": wallet_transactions_payload(),
            "/api/v1/wallet/withdrawals": [],
            "/api/v1/2fa/status": {"enabled": False},
            "/api/v1/security/antiphishing": {"code": None},
            "/api/v1/partner/dashboard": {
                "is_partner": False,
                "tier": None,
                "codes": [],
                "earnings": [],
                "clients": [],
            },
            "/api/v1/referral/code": {"referral_code": None},
            "/api/v1/referral/stats": {
                "total_referrals": 0,
                "total_earnings": 0,
                "commission_rate": 0,
            },
        }

        if path.startswith("/api/v1/miniapp/payments/"):
            json_response(self, HTTPStatus.OK, {"payment_id": path.rsplit("/", 1)[-1], "status": "completed"})
            return

        if path in payloads:
            json_response(self, HTTPStatus.OK, payloads[path])
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"detail": f"No S1-TG-004 mock route for {path}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        payloads: dict[str, Any] = {
            "/api/v1/auth/telegram/miniapp": {
                "access_token": "s1-local-access-token",
                "refresh_token": "s1-local-refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": auth_user_payload(),
                "is_new_user": False,
                "requires_2fa": False,
                "tfa_token": None,
            },
            "/api/v1/miniapp/trial/activate": {
                "activated": True,
                "trial_end": "2026-05-07T00:00:00Z",
                "message": "Trial activated for local S1-TG-004 smoke.",
            },
            "/api/v1/miniapp/checkout/quote": {
                "base_price": 14.99,
                "addon_amount": 0,
                "displayed_price": 14.99,
                "discount_amount": 0,
                "wallet_amount": 0,
                "gateway_amount": 14.99,
                "partner_markup": 0,
                "is_zero_gateway": False,
                "plan_id": "plan-plus-30",
                "promo_code_id": None,
                "partner_code_id": None,
                "code_input": None,
                "code_resolution": None,
                "discounts": [],
                "addons": [],
                "entitlements_snapshot": offers_payload()["currentEntitlements"],
            },
            "/api/v1/miniapp/checkout/commit": {
                "status": "pending",
                "payment_id": "payment-s1-tg-004",
                "invoice": {
                    "payment_url": "https://t.me/CryptoBot?start=s1_tg_004_local",
                    "currency": "USD",
                },
            },
            "/api/v1/wallet/withdraw": {
                "id": "withdrawal-s1-tg-004",
                "status": "pending",
                "amount": 10,
                "created_at": GENERATED_AT,
            },
            "/api/v1/auth/change-password": {"message": "Password change accepted by local mock."},
            "/api/v1/security/antiphishing": {"message": "Antiphishing code accepted by local mock."},
            "/api/v1/partner/bind": {"status": "bound", "partner_code": "S1LOCAL"},
            "/api/v1/auth/logout": {"message": "Logged out"},
        }

        if path in payloads:
            json_response(self, HTTPStatus.OK, payloads[path])
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"detail": f"No S1-TG-004 mock route for {path}"})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path.startswith("/api/v1/auth/devices/"):
            json_response(self, HTTPStatus.OK, {"message": "Device logged out"})
            return
        if path in {"/api/v1/auth/me", "/api/v1/security/antiphishing"}:
            json_response(self, HTTPStatus.OK, {"message": "Deleted"})
            return
        json_response(self, HTTPStatus.NOT_FOUND, {"detail": f"No S1-TG-004 mock route for {path}"})


def auth_user_payload() -> dict[str, Any]:
    return {
        "id": USER_ID,
        "login": "s1_tg_004",
        "email": "s1-tg-004@cyber-vpn.net",
        "telegram_id": 123456789,
        "is_active": True,
        "is_email_verified": True,
        "created_at": "2026-05-04T00:00:00Z",
        "role": "viewer",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the S1-TG-004 local Mini App mock API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MiniAppMockHandler)
    print(f"S1-TG-004 Mini App mock API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
