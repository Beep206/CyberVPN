# White-Label Overview

## Purpose

White-Label turns CyberVPN into a distribution platform. Partners should be able to launch branded customer entry points without requiring per-partner deployments or manual code changes.

## Target Partners

- Telegram-native resellers
- regional distributors
- community operators and creators
- affiliate operators graduating into branded distribution
- strategic distribution partners with stronger brand needs

## Business Model

Baseline model:

- CyberVPN remains platform-of-record and merchant-of-record;
- partner operates as branded reseller or distribution channel;
- revenue share, margin rules, and payout behavior are controlled by `PartnerCommercialPolicy`.

## Partner Journey

1. Apply
2. Pass KYB and moderation
3. Receive workspace
4. Configure brand and pricing
5. Provision branded bot and Mini App
6. Launch storefront and campaigns
7. Monitor sales and request payouts

## Self-Service Scope

Required self-service capabilities:

- application and review status
- brand setup
- pricing and margin setup within approved policy
- bot creation or binding
- Mini App preview
- storefront preview
- analytics visibility
- payout request flow

## Managed Bot Strategy

Primary path:

- Telegram Managed Bots
- shared multi-tenant runtime
- credential lifecycle controlled by the platform

Fallback path:

- partner-created bot token onboarding with encryption and validation

## Storefront Strategy

- partner storefront remains part of shared CyberVPN platform;
- branding and legal/support context become DB-driven;
- external web checkout is allowed only under approved payment policy.

## Branded Mini App Strategy

The branded Mini App is not a second product. It is the canonical Mini App runtime with:

- partner theme
- partner support links
- partner attribution
- partner commercial policy

## Non-Goals

- one codebase per partner
- one deployment per partner
- unrestricted partner copy, pricing, or legal override
- isolated entitlement or payment systems per partner
