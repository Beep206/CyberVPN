# Partner User Flows

## Flow: Partner Application

1. Partner opens portal.
2. Partner creates or resumes application.
3. Partner submits business, audience, and basic compliance data.
4. Portal shows application status and next actions.

Failure cases:

- incomplete application;
- blocked business category;
- duplicate or suspicious application.

## Flow: KYB and Moderation

1. System scores application risk.
2. Manual or automated review determines required next steps.
3. Partner uploads additional materials if needed.
4. Application transitions to approved or rejected.

## Flow: Workspace Creation

1. Approved application creates `PartnerWorkspace`.
2. Commercial and branding defaults are attached.
3. Partner enters onboarding wizard.

## Flow: Brand Setup

1. Partner submits brand name, logo, colors, descriptions, and support contacts.
2. Platform validates formatting and moderation rules.
3. Moderation-approved branding becomes active or staged.

## Flow: Pricing Setup

1. Partner configures pricing within commercial policy.
2. System validates markup, discount, and campaign limits.
3. Partner sees simulator output.

## Flow: Bot Creation

Primary path:

1. Partner requests managed bot provisioning.
2. System creates provisioning job.
3. Bot identity is reserved and bound to workspace.

Fallback path:

1. Partner creates bot manually.
2. Partner submits token.
3. System validates ownership and capabilities.

## Flow: Bot Provisioning

1. Provisioning job validates workspace, brand, and policy.
2. System applies branding, commands, menu button, webhook, and Mini App binding.
3. Launch assets are generated.
4. Bot moves to active or degraded state.

## Flow: Mini App Preview

1. Partner opens preview.
2. Runtime renders branded Mini App with partner context.
3. Partner verifies theme, copy, pricing, and support surfaces.

## Flow: Storefront Preview

1. Partner previews external storefront shell.
2. Brand and legal/support surfaces are validated.
3. Launch checklist highlights missing items.

## Flow: Launch

1. Partner confirms readiness.
2. Platform checks provisioning and moderation status.
3. Bot and storefront enter public-ready state.

## Flow: Analytics

1. Partner views dashboard.
2. Portal shows visits, opens, trials, payments, conversion, revenue, and top geographies.

## Flow: Payout Request

1. Partner opens finance section.
2. Partner sees available balance and hold state.
3. Partner requests payout.
4. Platform validates policy, risk, and account completeness.

## Flow: Bot Suspension

1. Platform or partner requests suspend.
2. Bot status moves to suspended.
3. Customer-facing runtime shows appropriate messaging.

## Flow: Token Rotation

1. Rotation is requested.
2. New credential is validated and bound.
3. Old credential is revoked or retired.
4. Audit log is written.
