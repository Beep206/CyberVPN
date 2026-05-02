# Partner Bot Provisioning

## Goal

Provision a branded Telegram bot into the shared CyberVPN runtime without per-partner deployments.

## Strategy

Primary path:

- Managed Bots
- shared multi-tenant runtime
- platform-controlled credential lifecycle

Fallback path:

- manual bot token onboarding
- encrypted token storage
- capability validation before activation

## Managed Bots Spike Criteria

Before relying on Managed Bots as the default production path, the platform should validate:

- manager bot permissions and capabilities;
- managed token retrieval behavior;
- managed token rotation behavior;
- webhook binding behavior;
- menu button and Mini App binding behavior;
- profile, commands, descriptions, and branding update behavior;
- revocation and owner update signals;
- scale limits and rate-limit behavior.

## Provisioning State Machine

### Partner Bot Lifecycle

```text
draft
-> pending_review
-> approved
-> provisioning_requested
-> provisioning_running
-> active
-> degraded
-> suspended
-> revoked
-> failed
```

### Provisioning Job Lifecycle

```text
queued
-> validating_partner
-> reserving_bot_identity
-> applying_branding
-> configuring_commands
-> configuring_menu_button
-> binding_webhook
-> binding_miniapp
-> generating_launch_assets
-> publishing
-> completed
```

### Failure States

- `failed_validation`
- `failed_bot_creation`
- `failed_token_fetch`
- `failed_webhook_binding`
- `failed_branding`
- `rollback_required`
- `manual_intervention_required`

## Provisioning Steps

1. Validate workspace and approval state.
2. Validate brand and commercial policy completeness.
3. Reserve or bind bot identity.
4. Apply branding and descriptive fields.
5. Configure commands and menu button.
6. Bind webhook and runtime routing.
7. Bind branded Mini App entry.
8. Generate launch assets.
9. Mark bot active or degraded.

## Webhook Binding

Webhook binding must:

- identify the bot and tenant safely;
- prevent cross-tenant routing mistakes;
- expose validation and retry status.

## Menu Button and Commands

Provisioning should set:

- Mini App launch binding
- support and payment-support routes if applicable
- partner-specific or platform-approved command set

## Branding Setup

Branding is applied only from moderated or approved brand data. Unsafe or rejected branding must block provisioning completion.

## Retry and Rollback

- retry transient failures automatically;
- require manual intervention for trust or policy failures;
- rollback partial binding where a bot would otherwise appear active but broken.

## Token Rotation

Rotation must:

- validate new token or managed credential;
- switch runtime binding safely;
- retire old credential;
- preserve audit trail.

## Bot Suspension

Suspension must support:

- platform-initiated suspend;
- partner-requested suspend;
- emergency suspend with credential revoke if needed.
