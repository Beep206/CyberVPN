# ADR-001: Telegram Stars as Primary Telegram Payment Rail

## Status

Accepted

## Context

CyberVPN plans to sell digital VPN access inside Telegram Mini Apps and Telegram bots. Telegram platform rules require digital goods and services inside Telegram app surfaces to use Telegram-native payment rails.

## Decision

All Telegram-native purchase flows use Telegram Stars / XTR as the primary payment rail.

## Consequences

- Mini App and Telegram bot checkout flows must use Telegram invoice behavior.
- entitlement activation must be tied to Telegram-authoritative payment success;
- non-Telegram payment rails remain available only on approved external surfaces.

## Alternatives Considered

- Continue using CryptoBot as default in-Telegram rail
- Redirect all Telegram checkout to external web

Both were rejected because they either conflict with platform expectations or increase checkout friction materially.
