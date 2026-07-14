# Task1 and Task2 Production VPN Runtime Evidence

- Date: 2026-07-13
- Last production recheck: 2026-07-14
- Production application host: `prod-app-1` (`45.87.41.146`)
- Signed artifact and live routing checks exercised backend implementation: `2f7ce2cc8ab31e41c66d4383c8688d7db4dbe39d`
- Current backend after signed-evidence v2 deployment: `2f7ce2cc8ab31e41c66d4383c8688d7db4dbe39d`
- Live 2026-07-14 container readback: image `cybervpn/cybervpn-backend:task1-task2-20260713-r22-signed-evidence-v2-2f7ce2cc`, image ID `sha256:77a3e14d24796fa49a3521f8578376d892c4fb8c75fc555ae12f3389390c5ffc`, healthy, restart count `0`; embedded `cybervpn.release=r10` is stale image metadata and is not used as the runtime-version source
- Final edge configuration exercised in production: `151c9cd7f2d7a23dfc8bcd2e44511cadd1ea67c5`
- Overall status: server-side VPN data plane, torrent-catalog routing and the four-node official plugin configuration are verified; a real `torrent_blocker.report`/nftables enforcement event and physical INCY/HAPP phone checks were not generated and remain explicitly unclaimed

## Scope

This record covers production evidence for:

- Task1, Premium Smart RU with Germany as normal egress, Netherlands as EU reserve, Russian services through SPB/Moscow, EU exceptions, the historical blocking policy evidence captured on 2026-07-13, and local-network `DIRECT`;
- Task2, SPB default egress with the approved Antifilter exceptions through the dedicated DE bridge;
- the target production account's two product grants, provider identities, Remnawave assignment, and campaign invites;
- rollback assets retained after the final backend and edge deployments.

No customer email, invite literal, customer/provider UUID, subscription URL, bearer token, private key, provider credential, or VPN profile secret is included in this file.

## 2026-07-14 Superseded/Clarified Torrent Scope

The historical rows below that say `torrent` or `Ad/Torrent/TOR` remain factual
for the fixtures used on 2026-07-13, but they are **not** acceptance evidence
for the clarified product rule. Torrent catalogs/sites such as RuTracker/Rutor
and similar HTTP(S) resources are not blocked; Task1 routes them through normal
Premium Smart RU policy and Task2 routes them through normal Antifilter/IP
policy. Only recognized BitTorrent protocol is blocked, and its owner is the
official Remnawave Node Plugin `torrentBlocker`
(`https://docs.rw/learn/node-plugins/`), which owns the runtime
`protocol=bittorrent` rule, `RW_TB_OUTBOUND_BLOCK`, webhook/report and nftables
enforcement. No live torrent/swarm test is required or allowed.

Fresh redacted production proof was collected on 2026-07-14. The results below
supersede the earlier pending state and do not rely on live BitTorrent or swarm
traffic:

| Criterion | Status | Production proof |
| --- | --- | --- |
| Task1 torrent catalog/site routing | Pass | Eleven canonical catalog domains are routed by the early `catalog-access-inline` rule to `World / EU`; the fresh full-policy probe logged RuTracker through `eu-de-2` and received HTTP `301` |
| Task2 torrent catalog/site routing | Pass | RuTracker's two current IPv4 addresses classified into the promoted DE exception union; RAW and XHTTP both returned HTTP `301`, while independent matched/unmatched probes exited DE/SPB respectively |
| BitTorrent protocol enforcement | Partial: runtime preflight pass, enforcement event unclaimed | All four loaded Remnanode/Xray configs contain exactly one plugin-owned `protocol=bittorrent` rule first after the management rule, a webhook, and `RW_TB_OUTBOUND_BLOCK`; all four panel records have `torrentBlocker.enabled=true`. No real report/nftables event was created under the no-live-swarm constraint |
| No manual duplicate torrent block | Pass | Fresh Mihomo, INCY/HAPP, generic Task2, and all four node runtime configs contain no handwritten BitTorrent, torrent-catalog, tracker-domain, or torrent-process BLOCK rule |
| Rollback/no-DIRECT leak | Pass | Both operators sanitize restored profile snapshots, focused rollback tests cover this invariant, and current Task2 fault evidence retains matched fail-closed behavior without silently selecting SPB `DIRECT` |

## 2026-07-14 Final Protocol-Only Runtime Recheck

The production Antifilter artifact was refreshed from the approved 13
communities without `65444:110`, promoted atomically to both active and
last-known-good, and bound to the final readiness attestation:

| Item | Final value |
| --- | --- |
| Feed version | `acc5472b1e39735ab11f9225dfa36db2eea4297d49a3b88488c3ac12ccc9a8ba` |
| Manifest SHA-256 | `84479e175e9020da1ffa48796897bdb4b4fd7c514acd99d3ea50d3f974531b2e` |
| Policy SHA-256 | `8876ebebfecd72a323cb3a00cb5047076e6f9b502e40d56a321b4183425f27c4` |
| IPv4 union | 21,427 unique prefixes |
| IPv6 feed | Zero prefixes; explicit `fallback_block` policy retained |
| Final readiness runtime evidence SHA-256 | `a4446db711579c751e0585576178c4a1b9242ac22d260a7aa4c4e69d9cfa78ee` |
| Final readiness JWT SHA-256 | `12afc6d9d59a59ee7512d59acef2e55839f70034830691f714343f046ee55cd8` |
| Readiness expiry | `2026-10-12T11:47:06.981961+00:00` |

Fresh customer-delivery verification fetched seven generated artifacts through
the production gateway: Task1 Mihomo, INCY and HAPP plus Task2 Mihomo, INCY,
HAPP and generic. All responses were non-empty and correctly product-scoped.
Task1 INCY/HAPP were byte-identical with four RAW and four XHTTP transports;
Task2 INCY/HAPP/generic exposed the same one RAW plus one XHTTP matrix. Both
generated Mihomo documents passed official Mihomo `v1.19.28` validation.
The later stable-failover promotion additionally fetched the internal stable
and exact account canary Task1 responses and proved their sanitized executable
bodies byte-identical at 12 outbounds and 18 rules.

The Task1 generated artifacts contained all eleven catalog exceptions, no
manual torrent policy, and terminal `World / EU`. A complete live Xray run
passed all eight concrete transports. After the final Moscow-primary seed, the
full policy produced DE default, Moscow for Ozon, EU for RuTracker, local
`DIRECT`, and `BLOCK` for ads and TOR.
RuTracker returned HTTP `301`. No BitTorrent packets, magnet fetch, tracker
announce, peer connection, or swarm traffic was generated.

Task2 RAW and XHTTP independently produced DE egress for a promoted-union
member and SPB egress for an unmatched destination. RuTracker was classified
into the current DE exception union and returned HTTP `301` through both
transports. This proves catalog browsing follows normal Antifilter/IP policy;
it is not used as evidence of BitTorrent protocol enforcement.

The four target nodes reported Remnawave Node `2.8.0`, Xray `26.6.27`, Linux
kernel `6.8.0-124-generic`, connected/enabled state, the exact expected plugin,
`blockDuration=86400`, and empty IP/user ignore lists. Safe direct runtime
inspection on DE, NL, SPB, and Moscow proved the single plugin-owned rule,
webhook, blackhole outbound, required `http/tls/quic` sniffing, and absence of
manual catalog/process duplication. This proves plugin deployment/readiness,
not a completed detection-to-report-to-nftables event. No plugin report or
nftables counter was artificially created because the approved verification
explicitly forbids live BitTorrent traffic.

The Moscow RAW/XHTTP relay failure was traced to a source/runtime mismatch:
the SPB socket proxy still used Moscow's unreliable public IPv4 even though the
inventory and operator define the stable IPv6 origin. Both tracked and live
services now proxy through `msk-origin-v6.cybervpn.internal`; RAW and XHTTP then
passed with DE default egress and Ozon HTTP `307`. The pre-change units are
retained under
`/root/cybervpn-backups/msk-relay-ipv6-20260714T113224Z`.

## 2026-07-14 Moscow-Primary Interim Recheck (Superseded)

This section records the interim state before stable automatic failover was
promoted. Its `10/16` stable contract and `ee6637...` stage manifest are
historical evidence only; the next section is the current production baseline.

The normative Task1 order was applied end to end: Moscow is the RU primary
and SPB is the RU fallback. The canonical policy compiler produced policy
SHA-256 `104bccaf290a4d79b9c25ef9d371042ae50f03c2eaf2ee0b941eb5302febe112`.
The production seed-stage manifest SHA-256 is
`ee663796612d1dea654272d2e0f8c7cd309cff03ec77df6a4836b08f4e0933bd`.

The seed passed first against an isolated clone of the production Remnawave
database. A full pre-seed database dump is retained at
`/srv/cybervpn/backups/task1-moscow-primary-20260714T121737Z/remnawave-pre-seed.dump`
with SHA-256 `16154bf90c566952fba32371e2b8d325cf8bb5e104427eb2d779ad03cc3d8c5f`.
The first production execution committed both idempotent seed transactions but
found zero matching Valkey keys; the required retry used the explicit
`allow-empty-template-cache` path and was followed immediately by external
fresh generated-body verification.

| Check | Final production result |
| --- | --- |
| INCY/HAPP | Byte-identical generated canary, 12 outbounds and 18 rules |
| Interim stable Xray contract | 10 outbounds, 16 rules, direct RU target `ru-msk-2`; superseded by stable promotion below |
| Canary Xray contract | `ru-primary` selects `ru-msk-2`; `ru-fallback` selects `ru-spb-2` |
| Mihomo | `RU Auto`: Moscow then SPB; official Mihomo `v1.19.28` pass |
| Generated Mihomo SHA-256 | `da6cbd35ad28b9e4a30cd6a9d221f45da2dd04c66ce9ff705de0fa9af3eb11dc` |
| Generated INCY/HAPP SHA-256 | `8d9f9ea039a4066aa60fe62af33e2d594c086f2e658aa062678bc72f1ee10ddc` |
| Catalog policy | 11 websites present, RuTracker HTTP `301`, no manual torrent BLOCK |
| Task1 live matrix | 8/8 RAW/XHTTP profiles passed; Moscow RAW/XHTTP returned Ozon `307` |
| Full policy | DE default, Moscow RU, EU catalog, local DIRECT, ads/TOR BLOCK |
| Task2 regression | RAW/XHTTP matched DE, unmatched SPB, RuTracker `301`; active/LKG and signed readiness unchanged |

## 2026-07-14 Stable Automatic Failover Promotion

The RU-safe four-balancer topology was promoted into the stable INCY/HAPP
template and applied through the same idempotent Remnawave seed path. Canary
selection remains available as a backend-owned response-profile identity, but
it no longer owns a routing capability that stable users lack.

| Item | Current production result |
| --- | --- |
| Stable source template SHA-256 | `0636f79630fa14a096a47b6a38caa56a9958290415cacfea21522dd5a4b8ce1a` |
| Canary source template SHA-256 | `92280f51a8ec79a4a8aacbcb5b41a33dabbbd414fa9893e71709b56bdaf550c9` |
| Seed-stage manifest SHA-256 | `42319647b4c9e445f63430d3643b131be6ee67c1682f294a67ea6ba7a0a0c005` |
| Stable/canary generated executable SHA-256 | `8d9f9ea039a4066aa60fe62af33e2d594c086f2e658aa062678bc72f1ee10ddc` |
| Stable/canary structure | 12 outbounds, 18 rules, four exact regional balancers, one shared observatory, two loopback fallback outbounds |
| EU behavior | DE primary -> NL fallback -> regional `BLOCK` |
| RU behavior | Moscow primary -> SPB fallback -> regional `BLOCK` |
| DB rollback dump | `/srv/cybervpn/backups/task1-stable-failover-20260714T130159Z/remnawave-pre-change.dump`, SHA-256 `f22d5603e8707fbdd767946579cbaac251710754410b6bbacf5152124f3df225` |
| Coordinated profile rollback manifest | `/srv/cybervpn/backups/task1-stable-failover-20260714T130159Z/task2-operator-rollback.json`, SHA-256 `1df3cd076506266c5f0199bd010e0ab0b454b98225b8a60660e95498fb2e4de5` |

The stable and canary Remnawave responses were fetched independently; after
delivery metadata normalization their executable bodies were byte-identical.
All eight RAW/XHTTP transports passed exact egress checks. The full policy
selected DE for ordinary traffic, Moscow for Ozon (`307`), EU for RuTracker
(`301`), `DIRECT` for the controlled local destination, and `BLOCK` for the
controlled ad/TOR samples. Moscow RAW and XHTTP both reached the intended RU
path. No long-duration reliability claim is inferred from this bounded run.

The coordinated Task2 operator retained active and last-known-good version
`acc5472b1e39735ab11f9225dfa36db2eea4297d49a3b88488c3ac12ccc9a8ba`
and manifest
`84479e175e9020da1ffa48796897bdb4b4fd7c514acd99d3ea50d3f974531b2e`.
The active Task1 bridge listeners are explicitly bound to
`2a0b:4140:ba84::2:9443` on DE and `2a12:5940:e38b::2:9443` on Moscow; wildcard
`0.0.0.0`/`::` is rejected by the operator. Frankfurt, Moscow and SPB nodes
were connected on the intended active profiles after reassignment/restart.

The post-promotion backend checks returned `task2_signed_readiness=pass` and a
valid approved attestation with matching manifest and expiry
`2026-10-12T11:47:06.981961+00:00`. The four-node plugin postcheck still reports
Remnawave Node `2.8.0`, Xray `26.6.27`, exact `torrentBlocker`, duration `86400`,
and empty user/IP ignore lists.

No BitTorrent packet, magnet fetch, tracker announce, peer connection, or swarm
traffic was generated. Four-node post-check still reports connected Node
`2.8.0`, Xray `26.6.27`, the exact official plugin, enabled `torrentBlocker`,
`blockDuration=86400`, and empty user/IP ignore lists.

## Historical Task1 Generated Subscription And Runtime (Superseded)

The rows in this section are retained as pre-Moscow-primary history. Their
`12/20`, SPB-primary and older artifact hash values are superseded by the stable
automatic-failover promotion above and must not be used as current release
evidence.

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
- ad/tracker, a historical superseded torrent-domain fixture, and TOR probes each selected `block` and failed closed;
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

- run ID: `7453efab-27e5-4117-a13e-64c8172c9373`
- execution attempt: `5a2f6b567d6e2c5c1f1a6c421fd4e71d`
- backend result before operator evidence: 34 pass, zero fail, four intentionally degraded
- selected-outbound matrix: 21 of 21 pass, including RAW/XHTTP and TCP/UDP

A bounded production fault isolated only source `2a01:e5c0:1368::3` to destination `2a0b:4140:ba84::2` on TCP/UDP port `9444`. The nftables mutation had a 240-second automatic watchdog and was removed before its deadline.

| Evidence | Result |
| --- | --- |
| Fault duration | 95 seconds |
| TCP packets dropped | 1,660 |
| UDP packets dropped | 10 |
| RAW matched exception during fault | Timed out; no SPB `DIRECT` fallback |
| XHTTP matched exception during fault | Timed out; no SPB `DIRECT` fallback |
| RAW/XHTTP unmatched traffic during fault | Continued through SPB |
| Post-restore RAW matched route | DE restored |
| Post-restore XHTTP matched route | DE restored after one stale-connection retry |
| Cleanup | nftables table absent; watchdog inactive |

The fault-window classification run was `7f613d9e-dd66-4b0f-9422-d4d482841aa4`, execution attempt `e34f39258b1aa2dcc64187389443c394`. The post-restore classification run was `60662012-1898-40d6-9dd3-47b8b8b7eb47`, execution attempt `91bf302c27f6f36847c4fcfe75761e6e`.

The canonical v2 envelope bound the current run and attempt, the canonical sanitized baseline capture, both auxiliary run and attempt IDs with their canonical capture hashes, backend and agent Git/image identities, feed and manifest, all 21 pre-fault/fault/post-restore rows, exact firewall rule digests, packet counters, watchdog/cleanup timestamps, and DNS/IPv6 policy hashes. It was signed offline with the dedicated Ed25519 operator key and ingested over the trusted internal route.

| Signed evidence result | Value |
| --- | --- |
| Artifact SHA-256 | `235ff362b6dfb70d02fa82eac5071550a479777d943464d09f8e509980de6e92` |
| First ingestion | HTTP 200, `created=true` |
| Exact retry | HTTP 200, `created=false` |
| Production DB readback at capture time | 38 pass, zero fail, zero degraded |
| Private operator key on production | Absent |

The exact retry proves idempotent ingestion. A read-only production database
query at capture time confirmed the same run ID, execution attempt, artifact
SHA, `signed_pass` marker, 38 persisted passing checks, and all 21
selected-outbound rows. Promotion affected only the four explicitly promotable
checks for the same execution attempt. This persisted `38 pass` readback is
live production evidence; it is not independently reconstructed by the public
offline bundle.

The signed artifact was accepted on backend r22 (`2f7ce2cc`) after the v2 validator was deployed. The final cleanup timestamp was `2026-07-13T19:18:58Z`, before the automatic watchdog deadline `2026-07-13T19:21:23Z`.

The complete sanitized evidence is retained as an independently replayable public bundle:

- [bundle manifest](task2-runtime-fault-v2/manifest.json), SHA-256 `bfc0c791bffb428f39c83688d3d290cec792cc1f7f5d4de3c543423c3f9198cc`;
- [operator public key](task2-runtime-fault-v2/operator-public-key.pem), raw Ed25519 key fingerprint `fc17bd7039554d281878ae5197868c12c4a24113be8e98eb6f3b8b863a0f76a9`;
- [signed v2 envelope](task2-runtime-fault-v2/signed-envelope.json);
- canonical sanitized [baseline](task2-runtime-fault-v2/baseline-run.json), [fault-window](task2-runtime-fault-v2/fault-window-run.json), and [post-restore](task2-runtime-fault-v2/post-restore-run.json) captures.

The repository CLI verifies the bundle offline, without production credentials or network access. The trusted operator fingerprint is a required out-of-band input, and the release manifest hash can be pinned at the same boundary:

```powershell
backend/.venv/Scripts/python.exe scripts/remnawave/verify-task2-runtime-fault-evidence-bundle.py docs/evidence/releases/task1-task2-20260713/task2-runtime-fault-v2 --expected-operator-public-key-sha256 fc17bd7039554d281878ae5197868c12c4a24113be8e98eb6f3b8b863a0f76a9 --expected-manifest-sha256 bfc0c791bffb428f39c83688d3d290cec792cc1f7f5d4de3c543423c3f9198cc
```

The verifier recomputes every manifest and canonical capture hash, verifies the
Ed25519 signature and v2 schema against that trust anchor, recomputes the
baseline result-set and row digests, checks all three 21-row route fingerprints,
and rejects unexpected files, unsafe paths, malformed JSON, failed
selected-outbound rows, private keys, customer email addresses, subscription
material, and other recognized sensitive markers. A coherently replaced key,
signature and manifest do not validate against the pinned operator fingerprint.
The safe public bundle intentionally retains the baseline/fault/post-restore
inputs and four promotable checks as `degraded`; an offline verifier therefore
proves signed fault behavior and fail-closed route rows, but not the later DB
promotion. Current persisted readiness is covered separately by the live
`task2_signed_readiness=pass` and matching-attestation checks above.

## Task2 Live Customer Policy

The current target subscription was fetched again and both transports were exercised with Xray 26.6.27:

| Transport | Listed exception | Unmatched default | Ozon | Historical superseded block fixtures | Fatal errors |
| --- | --- | --- | --- | --- | --- |
| RAW | DE egress | SPB egress | Pass | Three of three blocked | 0 |
| XHTTP | DE egress | SPB egress | Pass | Three of three blocked | 0 |

The signed selected-outbound matrix and fault counters provide server-side route evidence; the live customer checks provide independent end-to-end transport evidence.

## Production Deployment

The signed runtime evidence and final production checks used:

`cybervpn/cybervpn-backend:task1-task2-20260713-r22-signed-evidence-v2-2f7ce2cc`

Image ID:

`sha256:77a3e14d24796fa49a3521f8578376d892c4fb8c75fc555ae12f3389390c5ffc`

Both VPN test agents used:

`cybervpn/cybervpn-vpn-test-agent:task1-task2-20260713-r25-udp-handoff-runtime`

Image ID:

`sha256:1df47f47adad493bac554be81fe3ec9049089ad50b8d0d0e5ce229a659557808`

The final edge Caddy configuration strips caller-supplied route-evidence and trusted-ingress markers while preserving the dedicated Task2 webhook secret, then sets the trusted route-evidence marker only inside the owned route. The current backend webhook ignores all other `X-CyberVPN-*` headers; this statement does not claim a wildcard strip on that dedicated route.

At final inspection:

- backend, Remnawave, the primary VPN test agent, and the SPB-target agent were healthy with restart count zero;
- edge Caddy was running with restart count zero;
- backend `/health` and `/readiness` returned HTTP 200;
- the post-deployment backend, Remnawave, agent, and Caddy log window contained zero panic, fatal, or traceback markers;
- the Task2 fault table was absent, its watchdog was inactive, and SPB reached the peer-restricted DE IPv6 bridge on TCP `9444`;
- no transient Task2 capture, signed envelope, diagnostic log, or private signing key remained on the application host, backend container, or DE fault-state path.

## Target Account And Invite Audit

A final sanitized read-only audit established:

- exactly one active target account;
- exactly two active lifetime grants, one for each required product;
- two distinct subscription keys and two distinct provider subjects;
- both service identities are active and subscription-scoped;
- the Task1 server-owned canary marker remains enabled, while stable and canary
  now share the same automatic regional failover topology;
- the Task2 service context points to the intended product and `S1 SPB DE Exceptions` profile;
- the Task1 and Task2 replacement campaign invites are active with the reviewed lifetime/device policy;
- the legacy Task1 invite is revoked;
- the Task2 Remnawave user is active and unexpired, the SPB node is connected, the active profile matches, and both RAW/XHTTP inbounds are assigned.

## Rollback

- Git rollback point: `origin/main@64289f2dee89f995bf0d453958dcf749ee1c9633`.
- Backend rollback: `/srv/cybervpn/backups/task1-task2-remnawave-20260713T191206Z/backend-before-r22-signed-evidence-v2` (restores r21/`4e1974a9`).
- Edge rollback: `/srv/cybervpn/backups/task1-task2-remnawave-20260713T143909Z/caddy-before-webhook-auth-151c9cd7`.
- Final Moscow-primary Remnawave DB rollback source: `/srv/cybervpn/backups/task1-moscow-primary-20260714T121737Z/remnawave-pre-seed.dump`.
- Stable automatic-failover rollback source: `/srv/cybervpn/backups/task1-stable-failover-20260714T130159Z/remnawave-pre-change.dump`; coordinated supplemental-profile rollback manifest is retained in the same directory.
- The Task2 transient bridge-fault table and watchdog are absent from the final state.
- This historical rollback evidence predates the 2026-07-14 torrent clarification. The current operators additionally sanitize restored snapshots, do not require the live plugin metadata API before emergency rollback, and focused Linux rollback tests prove that restoration cannot reintroduce manual BitTorrent, process, or catalog-domain blocking.

## Explicit Remainder

Physical phone verification in INCY and HAPP is not claimed. It remains the owner's manual acceptance step for import, tunnel activation, application cache behavior, and device-specific DNS/TUN behavior. A real recognized-BitTorrent detection event, redacted `torrent_blocker.report`, and resulting nftables enforcement evidence are also not claimed because no live BitTorrent/swarm traffic was generated. Server-side subscription generation, all Task1 and Task2 RAW/XHTTP transports, selected routes, egress regions, catalog access, official plugin deployment/configuration, ad/TOR policy samples, failover, fail-closed behavior, and restoration safeguards are verified above.
