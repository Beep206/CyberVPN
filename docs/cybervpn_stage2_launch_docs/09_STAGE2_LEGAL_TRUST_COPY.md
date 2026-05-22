# Stage 2 Legal, Public Copy, And Trust Pages

**Stage:** `S2-STAGE-10`
**Status:** Approved for S2 implementation baseline
**Date:** 2026-05-23
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 public legal/trust copy contract.

The goal is not to create a legal opinion in the repository. The goal is to keep all public product promises aligned with the deployed CyberVPN architecture, support process, payment flow, VPN provisioning model and evidence gates.

---

## 2. Public Legal Pack

S2 public legal pack consists of:

| Public page | Route | Source |
|---|---|---|
| Terms of Service | `/terms` | `frontend/messages/*/Terms.json` |
| Privacy Policy | `/privacy-policy` | `frontend/messages/*/privacy-policy.json` |
| Acceptable Use Policy | `/acceptable-use` | `frontend/messages/*/AcceptableUse.json` |
| Refund Policy | `/refund-policy` | `frontend/messages/*/RefundPolicy.json` |
| Cookie Policy | `/cookie-policy` | `frontend/messages/*/CookiePolicy.json` |
| Privacy summary | `/privacy` | `frontend/messages/*/Privacy.json` |
| Trust center | `/trust` | `frontend/src/content/seo/trust.ts` |
| Audit posture | `/audits` | `frontend/src/content/seo/trust.ts` |

All public legal files were moved from S1 candidate wording to S2 Public Release 1.0 wording.

---

## 3. Public Contacts

S2 public support/legal contact contract:

| Purpose | Contact |
|---|---|
| General support | `support@cyber-vpn.net` |
| Privacy questions, deletion/export requests and privacy complaints | `privacy@cyber-vpn.net` |
| Abuse reports | `abuse@cyber-vpn.net` |
| Refund requests | `refund@cyber-vpn.net` |

Support channels may also include approved Telegram flows.

Do not ask users to send:

```text
passwords
2FA/TOTP codes
full card numbers
CVV/CVC
seed phrases
raw QR codes
raw subscription URLs
raw vless:// configs
private keys
```

---

## 4. Legal Seller Copy

The public copy uses the approved S2 seller category:

```text
CyberVPN project owner, individual founder/owner
```

Personal names, private addresses and private legal documents are intentionally not committed to the repository.

If the owner later changes the commercial structure, the public legal pack must be updated before the new seller receives payments or appears in checkout receipts.

---

## 5. Domain Boundary

S2 domain copy must stay consistent with the route contract:

| Domain | S2 role |
|---|---|
| `cyber-vpn.net` | Primary public customer domain |
| `admin.cyber-vpn.net` | Primary admin domain |
| `cyber-vpn.org` | VPN node and subscription delivery routes only where CyberVPN presents them |
| `de-1.cyber-vpn.org` and future node hostnames | VPN node hostnames |

Hard rule:

```text
.org must not be described as a general customer-site mirror of .net.
```

---

## 6. Privacy And No-Logs Claim Boundary

Allowed public privacy claim:

```text
CyberVPN app/backend is not designed to store browsing content, visited website content, DNS query content or raw VPN traffic content.
```

Required limitation:

```text
This is not an independent audited no-logs certification.
```

Public copy must continue to disclose that operational records may exist for:

1. authentication and security;
2. payments, refunds and reconciliation;
3. support and abuse handling;
4. VPN provisioning;
5. Remnawave/node operations;
6. observability and incident response;
7. backups and audit logs.

Do not publish stronger no-logs, RAM-only, zero-logs, independent-audit or warrant-canary style claims unless they are separately approved and evidenced.

---

## 7. Product Promise Boundary

Public copy may say:

1. CyberVPN uses VLESS Reality RAW as the default public profile where configured.
2. CyberVPN uses VLESS Reality XHTTP as an alternate path where configured.
3. Regions are enabled only when node evidence exists.
4. Paid-but-no-access cases must be escalated and must not age beyond the 24-hour policy.
5. Support, refund, abuse and privacy contacts are visible.

Public copy must not promise:

1. guaranteed access to every blocked site or app;
2. universal DPI bypass;
3. guaranteed speed, latency or uptime;
4. torrent/P2P availability on every node;
5. all listed countries as live regions before node evidence exists;
6. independent audited no-logs status;
7. automatic renewal unless the checkout explicitly says so and the provider flow is enabled with user consent.

---

## 8. Localization Contract

The legal/trust public files were updated across all existing locale directories.

Current practical policy:

1. `ru-RU` receives Russian S2 wording where it is launch-critical.
2. Other locales receive English S2 fallback copy until professional localization is approved.
3. No locale may retain S1 candidate, final-review-placeholder, mirror-domain or pre-go-live wording on public legal/trust pages.

Professional legal localization remains a future quality improvement, not an S2 runtime blocker.

---

## 9. Trust And Audit Pages

Trust center and audit posture pages must remain careful:

1. they can explain evidence expectations;
2. they can link to security, status, help and contact pages;
3. they must not imply an external audit exists unless one is published;
4. they must keep no-logs, uptime, speed, geography and protocol claims bounded.

The audit page should frame what independent verification would need to inspect, not pretend that such verification already exists.

---

## 10. Exit Criteria

S2-STAGE-10 is complete when:

1. Terms, Privacy Policy, AUP, Refund Policy and Cookie Policy no longer contain S1 candidate placeholders.
2. `.org` is described only as node/subscription delivery surface, not as a customer-site mirror.
3. Support, privacy, abuse and refund contacts are visible.
4. Public no-logs wording is bounded and not presented as an independent audit.
5. Public copy avoids unsupported SLA, speed, unblock, protocol and geography promises.
6. Evidence is recorded in `docs/evidence/releases/s2-stage-10-legal-trust-copy-20260523.md`.

