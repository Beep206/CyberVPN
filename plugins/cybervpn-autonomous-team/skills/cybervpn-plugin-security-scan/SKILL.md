---
name: cybervpn-plugin-security-scan
description: Perform an authorized security review of CyberVPN changes or a selected code area, validate plausible findings, and prepare tested remediations.
---

1. Confirm the scan scope is code the operator owns or is authorized to assess.
2. Load relevant threat models, ADRs, API contracts, and nested AGENTS.md rules.
3. Spawn `security_reviewer` and a subsystem specialist in parallel.
4. Examine authentication, authorization, realm/tenant isolation, CSRF/origin, sessions, passkeys/2FA, replay, idempotency, concurrency, injection, SSRF, path/command handling, secrets/PII, payment integrity, VPN configuration exposure, cryptography, and resource exhaustion.
5. Reproduce each plausible finding with a deterministic test or minimal proof in a local environment; do not label speculation as confirmed.
6. Prioritize by exploitability and business impact.
7. Implement remediations only after confirming the finding and preserve compatibility unless the task explicitly changes it.
8. Add regression and negative tests, run the affected quality gates, then ask `security_reviewer` and `verifier` to recheck.
9. Record unresolved external or environment-dependent risks explicitly.
