# Task1 and Task2 Production VPN Runtime Evidence

- Date: 2026-07-13
- Production application host: `prod-app-1` (`45.87.41.146`)
- Backend implementation exercised in production: `742598b1098f14b922e7bb874b4be8933962cdd6`
- Final edge configuration exercised in production: `151c9cd7f2d7a23dfc8bcd2e44511cadd1ea67c5`
- Overall status: server-side VPN data plane verified; physical INCY/HAPP phone checks not run

## Scope

This record covers production evidence for:

- Task1, Premium Smart RU with Germany as normal egress, Netherlands as EU reserve, Russian services through SPB/Moscow, EU exceptions, blocking policy, and local-network `DIRECT`;
- Task2, SPB default egress with the approved Antifilter exceptions through the dedicated DE bridge;
- the target production account's two product grants, provider identities, Remnawave assignment, and campaign invites;
- rollback assets retained after the final backend and edge deployments.

No customer email, invite literal, customer/provider UUID, subscription URL, bearer token, private key, provider credential, or VPN profile secret is included in this file.

## Task1 Generated Subscription And Runtime

The current production subscription was fetched through the customer delivery path after the final backend and Caddy deployments.

| Check | Result |
| --- | --- |
| INCY and HAPP bodies | Byte-identical |
| Xray outbounds and rules | 12 outbounds, 20 rules |
| Server-owned failover marker | Exactly one and enabled |
| Generated Mihomo configuration | Accepted by official Mihomo v1.19.28 |
| Mihomo terminal rule | `MATCH,World / EU`; no `MATCH,DIRECT` |
| Generated INCY artifact SHA-256 | `2610cd5bfc9031e03ededa9975fef3da5486667f20e1a912914b1d0cfe1e1ea9` |

The exact generated Xray canary passed four bounded phases with zero fatal errors:

| Phase | EU selection | RU selection | Result |
| --- | --- | --- | --- |
| Normal | `eu-de-2` | `ru-spb-2` | Pass on first route attempt |
| Primary down | `eu-nl-2` | `ru-msk-2` | Pass on first route attempt |
| All regional paths down | `block` | `block` | Both requests failed closed |
| Recovery | `eu-de-2` | `ru-spb-2` | Pass on first route attempt |

The full generated client policy was then exercised without replacing its routing table:

- ordinary internet returned the DE egress;
- 2ip, Ozon, and Wildberries selected `ru-spb-2` and responded successfully;
- the blocked-in-RU exception probe selected `eu-de-2` and responded successfully;
- a loopback probe selected `direct` and responded successfully;
- ad/tracker, torrent, and TOR probes each selected `block` and failed closed;
- Xray reported zero panic, fatal, or startup failures.

All eight individual Task1 RAW/XHTTP profiles also reached their expected egress and Ozon. Of 24 deliberately cold Docker starts, 21 passed the first sampled cycle; the three early transport/HTTP samples succeeded on the immediately following cold cycle. The health-aware four-phase canary above passed every phase on its first route attempt.

## Task2 Feed, Profile, DNS, And IPv6 Policy

The active and last-known-good artifacts were byte-identical and bound to:

| Check | Result |
| --- | --- |
| Feed version | `0b4748aaa22e7e7ec8114a2348c18a24fe48df62d64653bdd0fd0cd7d2903f71` |
| Manifest SHA-256 | `dc045130d1a532b7dfda8a161726590ffff0c0469cc8e7267371a785e14d92b9` |
| Approved categories | 13, excluding community `65444:110` |
| IPv4 union | 21,415 unique prefixes |
| IPv6 feed | Zero prefixes; explicit fallback block policy |

The active Remnawave profile matched the SPB node assignment and both Task2 inbounds were active. The canonical profile used IPv4-only DNS resolution with Cloudflare and Google DoH, `UseIPv4`, and `IPOnDemand`. Because the current feed has no IPv6 prefixes, the Task2-specific `::/0 -> BLOCK` rule was present for both Task2 inbounds before final SPB `DIRECT`.

The safe DNS and IPv6 evidence hashes bound into the signed runtime record were:

- DNS policy: `b1f5b63224aa3853b19b59b092ad9336a05d8f202d73bf778269d26f1de95f84`
- IPv6 policy: `5f4845d6413b3007dd5ca27421934a8e17becdbfcbfe8e5382e60cb8cef9a2a9`

## Task2 Signed Bridge Fault Evidence

The current baseline VPN Tester run was:

- run ID: `f2024184-10d9-4776-a758-5c038ae87b50`
- execution attempt: `c1f3d73cdbf81ac9418f70d57ad375b4`
- backend result before operator evidence: 34 pass, zero fail, four intentionally degraded
- selected-outbound matrix: 21 of 21 pass, including RAW/XHTTP and TCP/UDP

A bounded production fault isolated only source `2a01:e5c0:1368::3` to destination `2a0b:4140:ba84::2` on TCP/UDP port `9444`. The nftables mutation had a 240-second automatic watchdog and was removed before its deadline.

| Evidence | Result |
| --- | --- |
| Fault duration | 111 seconds |
| TCP packets dropped | 1,676 |
| UDP packets dropped | 10 |
| RAW matched exception during fault | Timed out; no SPB `DIRECT` fallback |
| XHTTP matched exception during fault | Timed out; no SPB `DIRECT` fallback |
| RAW/XHTTP unmatched traffic during fault | Continued through SPB |
| Post-restore RAW matched route | DE restored |
| Post-restore XHTTP matched route | DE restored after one stale-connection retry |
| Cleanup | nftables table absent; watchdog inactive |

The fault-window classification run was `df2c3378-8fae-498d-b6e7-52233a24e25c`; the post-restore classification run was `273832f9-5eaa-4657-a023-b7c5c4172ca8`.

The complete envelope bound the current run and attempt, backend and agent Git/image identities, feed and manifest, all 21 pre-fault/fault/post-restore rows, exact firewall rule digests, packet counters, watchdog/cleanup timestamps, and DNS/IPv6 policy hashes. It was signed offline with the dedicated Ed25519 operator key and ingested over the trusted internal route.

| Signed evidence result | Value |
| --- | --- |
| Artifact SHA-256 | `6758f08f2d15632257298a58f6075795fcbb9f1f90c74a50e3bd17c586886125` |
| First ingestion | HTTP 200, `created=true` |
| Exact retry | HTTP 200, `created=false` |
| Promoted run | 38 pass, zero fail, zero degraded |
| Private operator key on production | Absent |

The exact retry proves idempotent ingestion. Promotion affected only the four explicitly promotable checks for the same execution attempt.

## Task2 Live Customer Policy

The current target subscription was fetched again and both transports were exercised with Xray 26.6.27:

| Transport | Listed exception | Unmatched default | Ozon | Ad/Torrent/TOR | Fatal errors |
| --- | --- | --- | --- | --- | --- |
| RAW | DE egress | SPB egress | Pass | Three of three blocked | 0 |
| XHTTP | DE egress | SPB egress | Pass | Three of three blocked | 0 |

The signed selected-outbound matrix and fault counters provide server-side route evidence; the live customer checks provide independent end-to-end transport evidence.

## Production Deployment

The exercised backend image was:

`cybervpn/cybervpn-backend:task1-task2-20260713-r20-signed-fault-742598b1`

Image ID:

`sha256:fec0610265d6925cc32e39653ee704156fd944affd8546e9f294d97974ba64e3`

Both VPN test agents used:

`cybervpn/cybervpn-vpn-test-agent:task1-task2-20260713-r25-udp-handoff-runtime`

Image ID:

`sha256:1df47f47adad493bac554be81fe3ec9049089ad50b8d0d0e5ce229a659557808`

The final edge Caddy configuration strips caller-supplied route-evidence and trusted-ingress markers while preserving the dedicated Task2 webhook secret, then sets the trusted route-evidence marker only inside the owned route. The current backend webhook ignores all other `X-CyberVPN-*` headers; this statement does not claim a wildcard strip on that dedicated route.

At final inspection:

- backend, Remnawave, the primary VPN test agent, and the SPB-target agent were healthy with restart count zero;
- edge Caddy was running with restart count zero;
- backend `/health` and `/readiness` returned HTTP 200;
- the 30-minute backend, Remnawave, agent, and Caddy log window contained zero panic, fatal, or traceback markers;
- no transient profile config, signed envelope, or private signing key remained on production.

## Target Account And Invite Audit

A final sanitized read-only audit established:

- exactly one active target account;
- exactly two active lifetime grants, one for each required product;
- two distinct subscription keys and two distinct provider subjects;
- both service identities are active and subscription-scoped;
- the Task1 server-owned failover canary remains enabled;
- the Task2 service context points to the intended product and `S1 SPB DE Exceptions` profile;
- the Task1 and Task2 replacement campaign invites are active with the reviewed lifetime/device policy;
- the legacy Task1 invite is revoked;
- the Task2 Remnawave user is active and unexpired, the SPB node is connected, the active profile matches, and both RAW/XHTTP inbounds are assigned.

## Rollback

- Git rollback point: `origin/main@64289f2dee89f995bf0d453958dcf749ee1c9633`.
- Backend rollback: `/srv/cybervpn/backups/task1-task2-remnawave-20260713T141558Z/backend-before-r20-signed-fault-742598b1`.
- Edge rollback: `/srv/cybervpn/backups/task1-task2-remnawave-20260713T143909Z/caddy-before-webhook-auth-151c9cd7`.
- The Task2 transient bridge-fault table and watchdog are absent from the final state.

## Explicit Remainder

Physical phone verification in INCY and HAPP is not claimed. It remains the owner's manual acceptance step for import, tunnel activation, application cache behavior, and device-specific DNS/TUN behavior. Server-side subscription generation, transport reachability, selected routes, egress regions, blocking, failover, fail-closed behavior, and restoration are verified above.
