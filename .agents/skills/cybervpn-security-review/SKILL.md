---
name: cybervpn-security-review
description: Perform a focused CyberVPN security and privacy review for auth, cookies, sessions, passkeys, Telegram, RBAC, tenant isolation, payments, partner attribution, VPN configuration, protocol, desktop, mobile, or infrastructure changes.
---

# Security Review

1. Identify assets, actors, trust boundaries and attacker-controlled inputs.
2. Review authentication, session rotation/revocation, cookie flags/path/domain, CSRF/Origin, OAuth/WebAuthn/Telegram validation and token lifetime.
3. Review realm, tenant, workspace, partner-owner, role and object-level authorization on reads and mutations.
4. Review replay, idempotency, duplicate delivery, race conditions and transaction boundaries.
5. Review SQL/command/template/header/path injection, SSRF, redirects, file handling and external callbacks.
6. Review secret/PII/VPN config leakage through logs, analytics, errors, URLs, screenshots and support evidence.
7. Review payment/refund/settlement integrity and provider-webhook authenticity.
8. Review cryptography, downgrade/cross-protocol confusion, nonce/key handling and resource exhaustion for Verta/network code.
9. Add negative tests for every credible trust-boundary bypass.
10. Spawn `security_reviewer`, triage concrete findings, fix confirmed issues, and rerun tests. Clearly label unconfirmed hypotheses.
