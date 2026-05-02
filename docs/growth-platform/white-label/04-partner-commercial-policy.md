# Partner Commercial Policy

## Purpose

`PartnerCommercialPolicy` defines what a partner is allowed to sell, how prices are derived, how revenue is split, and how settlement behaves.

## Pricing Model

Required controls:

- allowed base plans
- markup mode
- markup ceilings
- discount rules
- optional campaign constraints

Markup modes:

- fixed
- percentage
- custom within approval range

## Revenue Share

Supported models:

- commission
- reseller margin
- hybrid

Required outputs:

- gross sale
- platform share
- partner share
- payout-ready share
- held share

## Trial Policy

Commercial policy must define:

- whether trials are enabled;
- which trial policy is attached;
- any partner-specific restrictions or incentives;
- whether certain acquisition sources disable trial.

## Refunds

Policy must define:

- whether partner balance is adjusted on refund;
- which sale states become payout-ineligible;
- who handles support and dispute communication.

## Payouts

Required fields:

- payout currency
- minimum payout
- payout cadence
- hold rules
- required account verification
- ledger-based payout-ready balance derivation

## Settlement Periods

Recommended controls:

- configurable settlement windows;
- pending, hold, ready, paid states;
- manual and automated payout support.

## Fraud Holds

Fraud hold logic may depend on:

- risk score;
- refund spike;
- unusual conversion behavior;
- chargeback or dispute signals where relevant.

Hold and release actions must be represented in the settlement ledger, not as hidden balance mutations.

## Merchant / Platform of Record

Baseline decision:

- CyberVPN remains platform-of-record and merchant-of-record.
- Partner acts as reseller or distribution channel.

## Supported Payment Rails

By default:

- Telegram surfaces: Stars / XTR
- external web or storefront: approved non-Telegram rails according to platform policy
- internal wallet: optional for credits, bonuses, or settlement support

## Policy Boundaries

Partners may configure within policy. They do not create independent payment, entitlement, or legal systems.
