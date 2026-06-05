# Rejected Or Removed Evidence Artifacts

Date: `2026-06-04`

Source issue: [CYBA-454](/CYBA/issues/CYBA-454)

## Current Rejection Log

No unsafe artifacts were copied into this evidence zone during [CYBA-454](/CYBA/issues/CYBA-454).

| Rejection ID | Date/time UTC | Artifact source | Artifact type | Reason | Action taken | Owner | Status |
|---|---|---|---|---|---|---|---|
| None | 2026-06-04 | N/A | N/A | No unsafe artifacts rejected in CYBA-454 heartbeat | N/A | qa-lead-flow-mapper | N/A |
| REJ-CYBA-457-PART-001 | 2026-06-04T16:04:00Z | `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-CAPTURE-RESULTS__partner-portal__manual-qa__20260604T155953Z.json` and sibling `MF-PART-*__20260604T1559*.png` screenshots | screenshot/json capture set | Superseded QA evidence: first partner dev run inherited heartbeat `NODE_ENV=production` while running `next dev`; not unsafe, but not accepted for functional conclusions. | Retained in repo for diagnostic continuity; excluded from evidence index; replaced by `MF-PART-CAPTURE-RERUN-DEVENV__partner-portal__manual-qa__20260604T160419Z.json`. | qa-partner-portal-manual | superseded-not-accepted |

## When To Add A Row

Add a row when any of these are encountered, or when a capture is retained but intentionally excluded from accepted QA evidence:

- raw Playwright `storageState`;
- raw cookie/localStorage/session dumps;
- raw trace/HAR/video with cookies, auth headers, JWTs, refresh tokens, payment/customer data, or Telegram `initData`;
- screenshots exposing production PII, VPN config/subscription URLs, QR payloads, `.env` values, admin secrets, payment secrets, or provider payloads;
- bug packets with unredacted user/payment/security details.

## Safe Action

If an artifact is unsafe:

1. Do not commit it.
2. Remove it from the repo evidence tree if it was copied there.
3. Record the rejected artifact type and reason here.
4. Replace it with sanitized console/network notes or a redacted screenshot where possible.
5. Mark the bug packet `BLOCKED - artifact not reviewed` if no safe evidence remains.
