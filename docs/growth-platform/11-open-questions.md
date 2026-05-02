# Open Questions

## Purpose

This file captures unresolved product, technical, legal, and commercial questions that must be answered before later implementation phases.

## Open Questions Table

| Question | Area | Owner | Decision Deadline | Current Recommendation |
|---|---|---|---|---|
| Are partners allowed to customize final customer pricing freely or only within policy bands? | White-Label | Product | Phase 1 | Allow controlled bands within `PartnerCommercialPolicy` |
| Should platform customers and partner customers share one catalog with visibility rules or have separate derived catalogs? | Platform | Product + Backend | Phase 1 | Shared canonical catalog with policy-based visibility |
| Which locales are required for first public launch of network pages? | Network | Product | Phase 1 | Launch priority locales, then expand to full set |
| Should DPI score be public in first release? | Network | Product + Infra | Phase 2 | No, launch after real probes and confidence model |
| Can Managed Bots satisfy required behavior for permissions, token rotation, webhook binding, menu button binding, and scale? | White-Label | Platform | Phase 2 | Run managed-bot spike and keep manual token fallback |
| What is the minimum review tier for a partner to provision a branded bot? | White-Label | Risk + Product | Phase 2 | Approval required before active provisioning |
| Are Telegram-only users required to pass additional recovery steps before payout-affecting actions? | Security | Product + Backend | Phase 2 | Keep support-mediated recovery for sensitive actions |
| How much branding freedom can partners have for support and legal copy? | White-Label | Product + Legal | Phase 2 | Controlled override with moderation |
| Do we support recurring subscription behavior inside Telegram at initial launch? | Payments | Product | Phase 3 | Launch with reliable one-time purchase and renewal flows first |
| How should Stars revenue map into partner settlement accounting? | White-Label | Finance + Product | Phase 3 | Convert to internal settlement ledger under platform-of-record model |
| What public promise language is acceptable for sensitive geographies in SEO pages? | Network | Legal + Product | Phase 3 | Use confidence-based wording, no absolute claims |

## Decision Rules

- no payment implementation without payment-policy closure;
- no public DPI claims without methodology and confidence closure;
- no White-Label public launch without partner risk and moderation policy closure.

## Update Cadence

- review during weekly platform planning;
- convert resolved items into ADRs, accepted policy docs, or implementation plan updates.
