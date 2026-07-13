# Task1 and Task2 Production VPN Runtime Evidence

- Date: 2026-07-13
- Production application host: `prod-app-1` (`45.87.41.146`)
- Implementation base exercised by the final runtime checks: `94936f32350b3d1b8364c005e1a51e4f2fddd26f`
- Overall status: server-side VPN data plane verified; physical INCY/HAPP phone checks not run

## Scope

This record covers the production evidence for:

- Task1, Premium Smart RU with Germany as the normal egress, Netherlands as EU reserve, Russian services through Moscow/SPB, EU exceptions, blocking policy, and local-network `DIRECT`;
- Task2, SPB default egress with listed exceptions through the dedicated DE bridge;
- the target production account's product grants, provider identities, and Remnawave squads;
- rollback assets retained after the final backend rollout.

No customer email, invite literal, UUID, subscription URL, bearer token, private key, provider credential, or VPN profile secret is included in this file.

## Task1 Generated Subscription

The final production subscription was fetched through the customer delivery path and checked after the r18 backend deployment:

| Check | Result |
| --- | --- |
| Outbounds | 12 |
| Rules | 20 |
| INCY and HAPP bodies | Byte-identical |
| Hardened policy marker | Exactly one |
| Generated Mihomo configuration | Accepted by official Mihomo v1.19.28 |

The outer remote wrapper returned a nonzero status after these checks because its final shell-status expression was malformed. The individual validation steps completed successfully, and a separate cleanup command returned zero and confirmed that no temporary production files remained. The wrapper itself is therefore not recorded as a passing command.

## Task2 Signed Readiness

The backend verified the production Ed25519 readiness chain against read-only files:

| Check | Result |
| --- | --- |
| Attestation | Exact match to the offline-signed token |
| Active and last-known-good pointers | Byte-identical |
| Promoted manifest SHA-256 | `dc045130d1a532b7dfda8a161726590ffff0c0469cc8e7267371a785e14d92b9` |
| Public verification key SHA-256 | `05a4d29be050ad457b8da2ab32a49cf0daab7314e36382b8b0f2b5d1e53f942e` |
| Private signing key on application host | Absent |
| Backend readiness decision | Pass |

## Task2 Bridge Fault Injection

A bounded production fault isolated only the exact SPB-to-DE bridge tuple for TCP and UDP port `9444`. A transient nftables table was used, and an automatic 240-second rollback timer was armed before the mutation.

Fault-window VPN Tester run: `3519fcdf-2315-4a3c-9666-10cd616b8b59`

| Evidence | Result |
| --- | --- |
| Matched selected-outbound rows | 21 of 21 remained `DE_EXCEPTIONS_BRIDGE` |
| Unmatched RAW/XHTTP TCP/UDP controls | 4 of 4 remained `DIRECT` |
| TCP packets dropped on the exact DE bridge rule | 1963 packets, 157040 bytes |
| UDP packets dropped on the exact DE bridge rule | 7 packets, 728 bytes |
| Matched fallback to SPB `DIRECT` | Not observed |
| Fault cleanup | Transient table removed before watchdog deadline |
| Managed peer-only firewall and listener | Remained active |
| Post-restore direct bridge check | Germany egress `138.124.115.206` restored |

The packet counters and selected-outbound correlation prove that matched traffic reached the bridge fault boundary and did not silently change to the SPB `DIRECT` path. The fault did not stop either Remnanode/Xray service and did not broaden the outage to unmatched traffic.

## Task2 Post-Restore Run

Post-restore VPN Tester run: `a81b5276-1739-425a-96e6-7f3017d94e9c`

The r18 runtime returned 37 pass, zero fail, zero degraded, 21 of 21 selected-outbound rows, and four of four UDP rows. A later adversarial review found that the aggregate runtime PASS could be promoted from the signed readiness state without consuming the specific bridge-fault record. The selected-outbound rows and live fault counters remain valid operator evidence, but the aggregate PASS is not used as proof after that finding.

The follow-up implementation intentionally leaves VPN Tester runtime and bridge-down checks degraded until a structured signed evidence format can bind the current run, image identities, selected-outbound matrix, drop counters, fault window, cleanup, and post-restore result. This reporting correction does not change Task2 customer routing or the live VPN data plane.

## Production Deployment

The exercised backend image was:

`cybervpn/cybervpn-backend:task1-task2-20260713-r18-signed-runtime-94936f32`

Image ID:

`sha256:d88454609343642426703fa52c9eb742ec01a8b56f93ee24f534226907c33fd8`

At final inspection:

- backend health was `healthy`, restart count was zero;
- primary and SPB VPN test agents were `healthy`, restart counts were zero;
- edge Caddy was running, restart count was zero;
- the final backend log window contained zero fatal, traceback, or panic markers.

## Target Account And Remnawave Audit

A sanitized, read-only audit established:

- exactly one active target account;
- exactly two active lifetime grants, one for each required product;
- two distinct active subscription-scoped provider identities;
- Task1 external/internal squads `CYBERVPN_PREMIUM_SMART_RU` and `CYBERVPN_PREMIUM_SMART_RU_NODES`;
- Task2 external/internal squads `CYBERVPN_SPB_DE_EXCEPTIONS` and `CYBERVPN_SPB_DE_NODES`;
- no bridge squad assigned to the customer identities;
- the replacement Task1 and Task2 campaign invites are active;
- the legacy Task1 invite is revoked.

The current active campaign invites are not the target account's historical redemption records. The account nevertheless has both required active lifetime grants and both separate provider identities.

## Rollback

- Git rollback point: `origin/main@64289f2dee89f995bf0d453958dcf749ee1c9633`.
- Previous backend r17 image remains available.
- Production compose backup: `/srv/cybervpn/backups/task1-task2-remnawave-20260713T022819Z/backend-before-r18-signed-runtime-94936f32`.
- The Task2 transient bridge fault was fully removed; it is not part of the rollback state.

## Explicit Remainder

Physical phone verification in INCY and HAPP is not claimed. It remains the owner's manual acceptance step for import, tunnel activation, DNS/TUN behavior, Task1 matched and unmatched routing, Task2 matched and unmatched routing, and application-specific cache/retry behavior.
