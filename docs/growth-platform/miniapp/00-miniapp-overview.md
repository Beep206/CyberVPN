# Telegram Mini App Overview

## Purpose

The Telegram Mini App is the canonical customer conversion runtime for CyberVPN. It should compress the path from first open to active service access into one Telegram-native flow:

`open -> bootstrap -> trial or payment -> config -> connect -> share`

## Role in the Growth Loop

- receives users from public Network Intelligence pages;
- converts Telegram-native demand faster than web handoff flows;
- acts as the customer runtime reused later in partner-branded mode;
- feeds referral sharing and partner attribution back into the shared platform core.

## User Personas

### First-Time Telegram Buyer

- wants fast access;
- does not want to leave Telegram;
- responds well to simple plans and strong default recommendations.

### Returning Customer

- needs renewal, device recovery, and support;
- wants a quick status view and low-friction config access.

### Referral Customer

- comes via friend or partner link;
- should keep attribution context from `startapp` payload to purchase.

### Partner-Branded Customer

- enters through a branded bot or Mini App;
- still uses the same underlying entitlement and payment core.

## Screen Set

Required screens:

- home
- plans
- checkout
- servers
- devices
- wallet
- referral
- profile
- support
- payments history

## Current Baseline

CyberVPN already has a Mini App baseline in `frontend/src/app/[locale]/miniapp/` with multiple screens and Telegram auth hooks. The current baseline is strong enough to build on, but not yet canonical because:

- root routing is inconsistent;
- auth success can leave the Mini App route space;
- checkout is not yet fully aligned with Telegram Stars-first policy;
- Telegram lifecycle handling is partial;
- there is no full server picker experience yet.

## Backend Dependencies

The Mini App depends on:

- Telegram identity validation
- subscriptions and entitlements
- plans and add-ons
- wallet and payment state
- devices and config delivery
- referral and attribution
- support and incident-aware messaging
- Network Intelligence for recommended server data

## Runtime Modes

### Platform Mode

- tenant kind is `platform`
- CyberVPN brand and support profile apply
- platform commercial policy applies

### Partner-Branded Mode

- tenant kind is `partner`
- brand theme and support profile come from partner workspace
- commercial policy, attribution, and bot binding are partner-scoped

## Full Version Scope

- validated Telegram bootstrap
- Telegram Stars checkout
- server recommendation and manual selection
- device and config lifecycle
- partner-branded runtime support
- analytics and abuse controls
- support and payment issue paths

## Explicitly Out of Scope for First Integrated Release

- separate codebase for partner-branded Mini App
- direct public network queries from the Mini App
- unsupported payment rails inside Telegram
- unrestricted partner-level UI overrides
