# Admin Control Plane

## Purpose

The Growth Platform cannot be production-safe without an internal operations layer. Mini App, White-Label, and Network Intelligence all require internal controls for moderation, risk, finance, incident handling, and audit.

## Scope

The admin control plane should support:

- approve or reject partner applications;
- approve or reject branding;
- suspend partner workspace;
- suspend partner bot;
- rotate or revoke bot credentials;
- review refunds;
- hold or release payouts;
- inspect immutable settlement ledger history;
- manage public incidents;
- inspect and export audit trail.

## Primary Operator Roles

- `Growth Admin`
- `Partner Operations`
- `Risk and Compliance`
- `Finance Operations`
- `Support and Refund Operations`
- `Platform Incident Operator`

Each role should have scoped permissions rather than broad implicit super-admin access.

## Core Surfaces

### Partner Review Queue

- application review;
- KYB state;
- risk score;
- reviewer notes;
- next required action.

### Branding Moderation

- brand assets and copy review;
- impersonation and policy checks;
- moderation decision history.

### Bot Lifecycle Console

- provisioning state;
- credential status;
- rotation and revoke actions;
- suspend and restore actions;
- managed-bot or manual-token path visibility.

### Refund and Payment Console

- payment lookup;
- entitlement state lookup;
- refund review or execution;
- duplicate-payment investigation.

### Settlement and Payout Console

- payout-ready balance derived from ledger;
- hold and release actions;
- payout request review;
- reversal chain inspection.

### Incident and Public Status Console

- create incident;
- update incident;
- resolve incident;
- publish safe public text by region impact.

### Audit and Investigation Console

- search by partner, bot, workspace, payment, payout, incident, or user;
- export operator history;
- inspect emergency actions.

## Required Data Objects

- `PartnerWorkspace`
- `PartnerRiskProfile`
- `PartnerBot`
- `PartnerBotProvisioningJob`
- `PartnerBotCredential`
- `Payment`
- `Order`
- `Entitlement`
- `PartnerSettlementLedgerEntry`
- `PublicIncident`
- `AuditLogEntry`

## Control Plane Invariants

1. Every sensitive action emits an audit record.
2. Refund and payout actions preserve ledger history.
3. Suspension actions are explicit and attributable.
4. Public incident edits are attributable to operator identity.
5. Broad White-Label rollout should not happen before this control plane exists in a usable form.
