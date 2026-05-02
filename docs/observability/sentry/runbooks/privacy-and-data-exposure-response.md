# Privacy And Data Exposure Response

Status: draft
Owner: security + platform
Last updated: 2026-04-24
Scope: Sentry data exposure or privacy-policy breach
Depends on: `../07-privacy-pii-scrubbing-and-replay-policy.md`
Related paths: `../02-open-questions-and-decision-log.md`

## Trigger conditions

- secrets or tokens appear in an event
- raw Telegram payloads or VPN configs appear in Sentry
- replay captures restricted forms or sensitive admin content
- unsafe user identity fields are found in production

## Response flow

1. Stop the offending ingress path or disable the affected SDK feature.
2. Restrict access to the affected project if needed.
3. Purge or delete exposed event data where supported.
4. Document exposure scope and time window.
5. Add or tighten both local SDK filters and org-level server-side scrub rules.
6. Record a postmortem and prevention fix.

## Follow-up

- backfill tests for the missed privacy rule
- update the normative privacy document
- review whether replay or attachments should remain enabled on that surface
