# Risk Register

## Risk Model

Severity scale:

- `Critical`
- `High`
- `Medium`
- `Low`

Probability scale:

- `High`
- `Medium`
- `Low`

## Active Risk Register

| Risk | Area | Severity | Probability | Mitigation | Owner | Fallback |
|---|---|---:|---:|---|---|---|
| Tenant data leakage across partners | White-Label | Critical | Medium | Strict tenant context, repository filters, audit logs, tests | Backend | Immediate partner surface suspend |
| Payment entitlement activated before authoritative success | Mini App | Critical | Medium | Server-authoritative payment confirmation, reconciliation worker, idempotency | Backend | Manual entitlement rollback |
| Public mock or simulated metrics shown as truth | Network | High | Medium | Snapshot-only public API, freshness, confidence, truthfulness policy | Platform | Remove affected block from public pages |
| Telegram payment compliance drift | Mini App / Bot | Critical | Medium | ADR-backed payment policy, explicit surface payment matrix | Product + Backend | Disable Telegram purchase and keep read-only flow |
| Managed Bots limitations or rollout blockers | White-Label | High | Medium | Managed bot spike, manual token fallback | Platform | Manual bot onboarding path |
| White-Label abuse or impersonation brands | White-Label | High | High | KYB, moderation, blocked brand rules, payout holds | Product + Risk | Emergency suspend and credential revoke |
| Public snapshot becomes stale but still appears live | Network | High | Medium | `generatedAt`, `expiresAt`, stale mode, alerting | Platform | Switch UI to degraded status |
| Mutable settlement state causes payout or refund disputes | White-Label | High | Medium | Append-only partner settlement ledger and reversal entries | Finance + Backend | Freeze payouts until reconciliation |
| Missing operator tooling delays abuse, refunds, or incident response | Operations | High | Medium | Admin control plane and emergency actions before public scale | Platform + Ops | Restrict rollout to manual cohort |
| Overengineering before signal | Program | Medium | Medium | Staged release gates and phased launch | Product | Freeze advanced work until metrics arrive |
| Referral abuse via Telegram loops | Mini App / White-Label | High | Medium | Signed payloads, rate limits, abuse scoring | Backend | Disable reward issuance for flagged flows |
| Incomplete partner settlement model | White-Label | High | Medium | Platform-of-record baseline, explicit commercial policy | Product + Finance | Delay payout automation |
| Support burden spikes after launch | Mini App / White-Label | Medium | Medium | `/paysupport`, help surfaces, incident scripts, dashboards | Product + Support | Scope-limited rollout |
| SEO pages overpromise DPI or uptime claims | Network | High | Medium | Confidence markers, methodology page, legal copy review | Product + Legal | Remove affected SEO pages |

## Product Risks

- Mini App may be functionally complete but still fail on perceived simplicity if the bootstrap and checkout flow feel slow or fragmented.
- White-Label may attract low-quality partners if moderation and commercial boundaries are weak.
- Network Intelligence may underperform as an acquisition lever if public storytelling is strong visually but weak on data freshness and methodology.

## Technical Risks

- current Mini App route and auth inconsistencies can create partial flows and hard-to-debug drop-off;
- partner runtime can drift into static or env-driven behavior if DB-driven branding is not enforced early;
- snapshot generation can become expensive if schema is not designed for efficient periodic updates;
- refund, reversal, and payout state can drift if ledger and reconciliation are modeled as mutable balances only.

## Legal and Compliance Risks

- public claims about service availability in sensitive regions require careful wording and proof confidence;
- partner branding can create impersonation and trademark exposure;
- payment support and refund expectations must align with chosen payment rails and merchant-of-record policy.

## Risk Review Cadence

- weekly during planning;
- twice weekly during payment and provisioning implementation;
- per rollout stage before expansion of audience.
