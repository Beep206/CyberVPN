# Premium Smart RU VLESS Reality 443 Production Evidence

Date: 2026-07-10
Target: `prod-app-1` (`45.87.41.146`)
Repository baseline: `7c0b44fb993f182b3850ddb622b3cd962b824eb4`
Plan: `docs/plans/CyberVPN_VLESS_Reality_RAW_TCP_443_Fix_TZ_2026_07_10.md`

This document contains only host names, public infrastructure addresses, ports,
counts, versions, timings, safe error classes, and non-secret checksums. It does
not contain user identifiers, VLESS UUIDs, subscription URLs, Reality keys,
short IDs, API tokens, cookies, invite codes, or credentials.

## Outcome

| Requirement | Result | Evidence |
| --- | --- | --- |
| VLESS Reality RAW/TCP 443 | PASS | Four concrete profiles completed DNS, TCP, Reality/Vision handshake, and HTTP probe. |
| VLESS Reality XHTTP 8443 | PASS | Four concrete profiles completed DNS, TCP, Reality/XHTTP handshake, and HTTP probe. |
| Generated subscription | PASS | Exactly four valid RAW/TCP and four valid XHTTP profiles; no invalid profile. |
| Remnawave node/host matrix | PASS | Four connected enabled nodes, two required inbounds, eight enabled hosts, and eight resolved address-to-node links. |
| Premium Smart RU routing contract | PASS | Hardened Mihomo analyzer and generated-core validation passed; transport repair did not replace the routing template. |
| VPN Tester release gate | OPEN | Latest production run passed all 59 checks and no release override is active. |
| INCY server routing follow-up | AGENT PASS / PHONE PENDING | Exact Frankfurt RAW/XHTTP profiles keep DE default egress, send Ozon through Moscow, block common ad/torrent domains, and expose an INCY routing header; the final phone retry remains user-owned. |

## Root Causes

1. Remnawave 2.8 serializes per-user VLESS flow into generated node clients.
   The original backend image left the node-loaded RAW clients without
   `xtls-rprx-vision`, creating a client/server Vision mismatch. The compatibility
   image preserves the Remnawave 2.8 contract, removes the invalid top-level
   flow field, and renders Vision on the RAW clients.
2. The previous Reality camouflage target was incompatible with the deployed
   Xray path. Both inbounds now use the validated `www.yandex.ru:443` target and
   matching server name; the existing Reality key material was not rotated.
3. Russia-bound Reality handshakes from the foreign application host were
   intermittently terminated before Xray could read a complete ClientHello.
   Runtime checks for Moscow and Saint Petersburg now execute from restricted
   regional agents, so the test uses the same network region as the product
   route instead of treating a foreign control-plane probe as the user path.
4. VPN Tester previously accepted weak transport counts and an expanded host
   response shape that Remnawave 2.8 does not return. The tester now resolves
   inbound UUIDs through Config Profiles, resolves host addresses to nodes,
   requires exactly four valid profiles per transport, checks all eight concrete
   profiles, retries only bounded transient transport failures, and keeps such
   failures release-blocking when retries are exhausted.
5. The internal run trigger accepted 60 characters while the persisted column
   allows 40. The API now rejects values longer than 40 with HTTP 422 instead of
   producing a database error.
6. New Remnawave users were still assigned to the legacy `S1_DEFAULT_DE`
   internal squad. The production default and tracked deployment default now
   use `CYBERVPN_PREMIUM_SMART_RU_NODES`; the legacy squad and existing users
   were not mutated. This removed the retired `de-1` pair from fresh Premium
   Smart RU subscriptions while preserving the legacy rollback path.
7. The regional Reality handshake could legitimately take slightly longer than
   the agent's fixed five-second proxy connect budget. The connect budget is now
   ten seconds inside the unchanged twenty-second per-profile limit, with three
   bounded attempts; persistent failures remain release-blocking.
8. INCY imports XRAY_BASE64 links, so the Mihomo YAML routing policy was not
   applied when a user selected an individual Frankfurt profile. Frankfurt now
   has a dedicated server-side Xray policy: default/YouTube traffic exits DE,
   while Russian domains and IPs use an isolated Moscow bridge.
9. Moscow's public IPv4 path is unreliable. DNS-only `msk-relay.cyber-vpn.org`
   terminates TCP on the SPB node and forwards over the Moscow node's stable
   inventory IPv6; REALITY and VLESS still terminate on Moscow.
10. The first server-routing bridge user was assigned to the customer Smart RU
    squad. It is now isolated in `CYBERVPN_SMART_RU_BRIDGE`, which contains only
    a Moscow-only Shadowsocks inbound on port `9443`; the customer squad does
    not contain that inbound and the Moscow firewall accepts the port only from
    Frankfurt's fixed IPv6.
11. INCY originally used `DomainStrategy=IPIfNonMatch`, which could resolve a
    domain before Frankfurt's authoritative RU-domain rules saw it. The live
    routing header now uses `AsIs`, preserving the domain for server routing.
12. Moscow's Russian egress opened Ozon reliably but ordinary global HTTPS was
    intermittent. Moscow RAW/XHTTP now use a dedicated profile: RU domains and
    `geoip:ru` remain `DIRECT` in Moscow, while all other traffic uses an
    isolated Moscow-to-Frankfurt Shadowsocks bridge.
13. Remnawave accepted the final node assignments before the running nodes had
    loaded the new service users. The supported node restart action with
    `forceRestart=true` was required; the operator now performs it after both
    node PATCH operations and checkpoints `nodes_restarted`.

## Production Baseline And Backup

| Item | Safe evidence |
| --- | --- |
| Remnawave | `2.8.0`; deployed compatibility image `cybervpn/remnawave-backend:2.8.0-raw-vision-flow.2` |
| Remnanode | `2.8` on all four nodes |
| Xray | `26.6.27` on all four nodes |
| Nodes | Germany `138.124.115.206`, Netherlands `138.16.140.44`, Moscow `178.159.94.225`, Saint Petersburg `193.233.91.99` |
| Node state | Four connected and enabled |
| Backup root | `/srv/cybervpn/backups/remnawave-vless-443-20260710T063109Z` |
| Database dump checksum | SHA-256 `e60e5daa69dddd9f16ee8e8e6dbc50806473f15a17d0c8d8c2adba60b08a2ada` |
| Original Config Profile checksum | SHA-256 `c584e320ecba19e3ed6f73447dedfc5d85488d7ee60d88617e16375a7289c16d` |
| Pre-target-change profile checksum | SHA-256 `6c38bc47b9b2c0443d39c9ae664acd3a9c51c12c2c126b0a9c54d1af609d7b35` |
| Final pre-apply profile checksum | SHA-256 `039b9cfbc5db8cd78e5272fc62ea9423eb56131684a9e02b4b9a4f5cb07f942b` |

The supported Config Profile path was used and the resulting node-loaded Xray
configuration was inspected after synchronization. `VLESS_REALITY_443` remains
VLESS over RAW/TCP Reality on port 443 with Vision client flow;
`VLESS_XHTTP_REALITY_8443` remains VLESS over XHTTP Reality on port 8443.

## DNS, Ports, And Listeners

| Check | Result |
| --- | --- |
| A records | 4/4 resolve to their intended public IPv4 address |
| AAAA records | Baseline had 0 unexpected records; the follow-up intentionally adds one DNS-only `de-3` AAAA record to the same DE node. |
| Provider mode | Node records confirmed DNS-only |
| External reachability | 8/8 TCP endpoints reachable: ports 443 and 8443 on four nodes |
| Node listeners | 8/8 listeners present in the node-loaded Xray runtime |
| Node health | Four Remnanode services healthy after synchronization |

The home monitoring host `10.10.10.34` was not started or contacted because it
is under maintenance and was explicitly excluded from this task.

## DE INCY Dual-Stack Follow-Up

A real INCY report was investigated after the initial rollout. The target
account could use the NL RAW and XHTTP profiles, while neither DE profile
reached the DE Xray access log during the reported phone attempt. This ruled
out a server-side rejection at that timestamp and pointed to the client network
path before the DE node.

The same target account's exact generated DE profiles were then tested through
the production VPN Test Agent. RAW and XHTTP both passed DNS, TCP, Reality
handshake, HTTPS probe, and DE exit-country checks. Before the DNS change, the
same profiles also passed when the DE host was forced to the node-owned global
IPv6 address. The node exposes both `443` and `8443` on dual-stack listeners and
permits those ports over IPv4 and IPv6.

The narrow, reversible production mitigation was therefore limited to DNS. It
does not prove which address family INCY will select on the affected phone
network; that user-visible result remains pending.

| Item | Follow-up evidence |
| --- | --- |
| Existing A | `de-3.cyber-vpn.org -> 138.124.115.206`, retained and DNS-only |
| Added AAAA | `de-3.cyber-vpn.org -> 2a0b:4140:ba84::2`, DNS-only, automatic TTL |
| Cloudflare record | `00a3ab1a6fd0de22b555d0a68ee48446` |
| Public propagation | Cloudflare and Google DoH plus direct `1.1.1.1` and `8.8.8.8` queries returned the intended AAAA |
| Post-change DE RAW | PASS on attempt 1; DNS, TCP, handshake, HTTP, and DE exit passed; 520 ms |
| Post-change DE XHTTP | PASS on attempt 1; DNS, TCP, handshake, HTTP, and DE exit passed; 490 ms |
| DE access log correlation | Both target-account transports were accepted during the post-change test window |
| Remnawave/profile mutation | None; hostname, UUID, Reality fields, SNI, ports, flow, and XHTTP path were not changed |
| Rollback | Remove only the added AAAA record and wait for recursive resolver caches; retain the existing A and all Remnawave state |

The final DE RAW/XHTTP retry in INCY is deliberately not claimed by this
evidence. The account remains available until the user completes that retry;
it will then be removed from both CyberVPN and Remnawave.

## INCY Server Routing And Ad Filtering

The INCY response remains a Base64 list of eight individual VLESS links, so it
does not carry Mihomo proxy groups. Frankfurt now enforces the required Smart RU
decision server-side. Its two public inbounds use `DIRECT` for the default,
YouTube, Discord, Telegram, AI, and GitHub; explicit RU domains plus `geoip:ru`
use `RU_MSK_BRIDGE`; common ads, TOR, BitTorrent, and named torrent sites use
`BLOCK`. Moscow now mirrors this model in the other direction: RU targets stay
on Moscow and non-RU traffic uses `DE_GLOBAL_BRIDGE`. NL and SPB retain their
regional semantics.

The bridge follows the Remnawave service-user pattern but has a separate access
boundary: one internal squad, one Moscow-only inbound, no public Host, and a
source-restricted firewall rule. The generated INCY subscription also carries
a static `routing` header with `GlobalProxy=true` and
`BlockSites=geosite:category-ads-all` plus TOR/torrent domains. This provides
client-side defense in depth without bypassing the Frankfurt server route. Its
`DomainStrategy=AsIs` deliberately leaves target domains intact for the two
server-owned Smart RU policies.

Network/domain filtering cannot guarantee removal of native YouTube in-stream
ads because first-party ads and video content can share delivery domains. The
verified claim is narrower: DoubleClick and the configured ad category are
blocked while YouTube playback remains reachable. Native-app in-stream ad
behavior remains part of the phone-side check.

## Authoritative References

The production model and compatibility decisions were checked against the
current Remnawave documentation and source, rather than inferred from the local
adapter alone:

- Remnawave Config Profiles: <https://docs.rw/learn-en/config-profiles/>
- Remnawave Nodes: <https://docs.rw/learn-en/nodes/>
- Remnawave Hosts: <https://docs.rw/learn-en/hosts/>
- Remnawave Squads: <https://docs.rw/learn-en/squads/>
- Remnawave subscription formats: <https://docs.rw/learn-en/templates/>
- Official Remnawave backend: <https://github.com/remnawave/backend>
- Official Remnawave templates: <https://github.com/remnawave/templates>
- Official XTLS Reality reference: <https://github.com/XTLS/REALITY/blob/main/README.en.md>
- Official Xray Reality server example:
  <https://github.com/XTLS/Xray-examples/blob/main/VLESS-TCP-XTLS-Vision-REALITY/config_server.jsonc>
- Cloudflare DNS proxy status: <https://developers.cloudflare.com/dns/proxy-status/>
- Cloudflare DNS record API: <https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/create/>

## Generated Subscription

The disposable canary was created after profile synchronization through the
supported Remnawave API, assigned the required internal and external squads,
and used to fetch a fresh generated Mihomo document.

| Generated check | Result |
| --- | --- |
| YAML parse | PASS |
| `mihomo -t` against generated YAML | PASS, exit code 0 |
| Valid RAW/TCP Reality 443 profiles | 4 |
| Valid XHTTP Reality 8443 profiles | 4 |
| Invalid or duplicate-compensated required profiles | 0 |
| Required locations | Germany, Netherlands, Moscow, Saint Petersburg |
| Mihomo headers | HTTP 200; subscription info, profile title, update interval, and Premium Smart RU plan header present |
| HAPP headers and links | HTTP 200; required headers plus 4 RAW and 4 XHTTP links |
| INCY headers and links | HTTP 200; required headers plus 4 RAW and 4 XHTTP links |

The canary was then deleted. Final safe Remnawave and application counts were
zero, including zero disposable canary users. No generated subscription
artifact, subscription URL, or canary credential remains in production state.

## Runtime Transport Evidence

Final run: `d3e745ae-8ad6-4dbe-b69e-50876528e01e`
Status: `pass`
Checks: `59 pass`, `0 fail`, `0 degraded`, `0 skipped`
Runtime mode: `proxy-only`

All three persisted agent matrix results report
`server_matrix_valid=true`, `raw_server_matrix_valid=true`, and
`xhttp_server_matrix_valid=true`. The release gate is `pass`,
`blocking=false`, linked to the final run, with no active override.

A later independent code-path review found that regional-agent profile checks
could be persisted under role-prefixed or display-name-derived keys while the
release gate required canonical `de`, `nl`, `moscow`, and `spb` keys. The local
implementation now derives keys from the allowlisted server identity, preserves
those eight canonical keys across shards, and emits one validated global matrix
check. The historical gate response is retained as incident evidence but is not
treated as final proof; AC-11 requires a new production run after those backend
and agent images are deployed.

| Location | Transport | Attempt | DNS | TCP | Proxy handshake | HTTPS probe | Exit country | Latency |
| --- | --- | ---: | --- | --- | --- | --- | --- | ---: |
| Moscow | RAW/TCP 443 | 3 | PASS | PASS | PASS | PASS | RU | 761 ms |
| Moscow | XHTTP 8443 | 1 | PASS | PASS | PASS | PASS | Not captured | 5457 ms |
| Germany | RAW/TCP 443 | 1 | PASS | PASS | PASS | PASS | DE | 596 ms |
| Netherlands | RAW/TCP 443 | 1 | PASS | PASS | PASS | PASS | NL | 412 ms |
| Germany | XHTTP 8443 | 1 | PASS | PASS | PASS | PASS | DE | 539 ms |
| Netherlands | XHTTP 8443 | 1 | PASS | PASS | PASS | PASS | NL | 383 ms |
| Saint Petersburg | RAW/TCP 443 | 1 | PASS | PASS | PASS | PASS | RU | 634 ms |
| Saint Petersburg | XHTTP 8443 | 1 | PASS | PASS | PASS | PASS | RU | 524 ms |

### Current exact-link post-routing smoke

| Profile | Default/YouTube | Ozon | Blocking | Exit |
| --- | --- | --- | --- | --- |
| Frankfurt RAW | `example.com=200`, YouTube `204` | `307` through Moscow bridge | DoubleClick and Rutracker blocked | DE |
| Frankfurt XHTTP | `example.com=200`, YouTube `204` | `307` through Moscow bridge | DoubleClick and Rutracker blocked | DE |
| Moscow RAW | five consecutive `example.com=200`, YouTube `204` through Frankfurt | `307` direct in Moscow | DoubleClick and Rutracker blocked | DE default (`138.124.115.206`) |
| Moscow XHTTP | five consecutive `example.com=200`, YouTube `204` through Frankfurt | `307` direct in Moscow | DoubleClick and Rutracker blocked | DE default (`138.124.115.206`) confirmed by five IP services |
| Netherlands RAW/XHTTP | `example.com=200` | Regional profile | N/A | NL |
| Saint Petersburg RAW/XHTTP | `example.com=200` | Regional profile | N/A | RU |

The INCY `routing` response header is present on the exact account subscription,
decodes to the expected `AsIs` profile, contains seven block entries, and has
SHA-256 `b482c6901a1a697dd602dc2ec95a9702f71c19fed646eb137b408483a99fa8f1`.

The final bidirectional-routing backup is
`/srv/cybervpn/backups/vpn-smart-ru-moscow-global-20260710T190105Z`.
The pre-change dump SHA-256 is
`be28561542fcc2430aa2c87bc8336d90c09325a103518084fbfd72a8cb9810bb`,
the post-change dump SHA-256 is
`6871a7ab654ecef035ac07497e470db404206c3c70a9f195f37dbcfb608bf730`,
and the root-only v3 API rollback manifest SHA-256 is
`f30ca4aaa23371f8617b699e2b6a86620ce80df968f74d36d52a71a836538329`.
Two preceding apply attempts stopped on enforced invariants and ended with
`phase=rolled_back`; no failed-attempt state remained active.

Moscow RAW passed within the configured three-attempt transient-failure budget.
The retry delay is bounded at 0.75 and 1.5 seconds; a persistent failure remains
`fail` and blocks the release gate. A separate diagnostic also passed with the
Chrome, Firefox, Safari, iOS, and randomized Xray fingerprints, confirming that
the observed intermittent Russian route was not tied to one fingerprint.

## Regional Probe Security

The regional agents are dedicated, authenticated, proxy-only probes. Their
ports are not generally exposed:

- the Saint Petersburg-hosted probe accepts only the production application
  host as source;
- the Moscow-hosted probe accepts only the production application's fixed IPv6;
- the application-host relay binds only to the Docker egress bridge and forwards
  over IPv6 to Moscow;
- UFW/nftables negative probes from the Germany node were rejected;
- agent environment files are root-owned with mode `0600`;
- no VPN link, user UUID, key, token, or subscription URL is written to results.

## Deployed Artifacts

| Component | Production artifact |
| --- | --- |
| Backend | `cybervpn/cybervpn-backend:vless-reality-regional-agents-20260710-5` |
| Primary VPN test agent | `cybervpn/cybervpn-vpn-test-agent:vless-raw-fix-20260710-8` |
| Regional VPN test agents | Same `vless-raw-fix-20260710-8` image |
| Remnawave backend | `cybervpn/remnawave-backend:2.8.0-raw-vision-flow.2` |

Runtime VPN testing is enabled. Scheduled and synthetic testing remain disabled;
the production release gate reads the persisted final run. A 41-character
internal trigger is rejected with HTTP 422, both regional health endpoints are
200 from the authorized production path, the relay is active, and recent backend
error count after the final deployment is zero.

## Repository Validation

- Focused backend VPN Tester/Remnawave/settings suites: PASS with `--no-cov`;
  the full backend suite was intentionally not run by user instruction.
- VPN test agent: 27 focused tests, Ruff check/format, and mypy PASS.
- Infrastructure: 15 focused tests, stage1/local Compose config, and Ansible
  syntax for regional, relay, control-plane rollout, verify, and rollback PASS.
- DE3 DNS follow-up: 3 focused Python contract tests plus 5 native OpenTofu
  plan/validation tests PASS. The native tests prove explicit dual-stack records
  do not read edge remote state and reject mixed proxying, edge explicit/blank
  content, and VPN-node blank content.
- The documented post-import plan gate was exercised with synthetic plan JSON:
  it accepted DE3 no-op/update actions, rejected a DE3 create action, and
  rejected an unrelated managed-resource mutation in the same saved plan.
- Remnawave compatibility patch: 4 Node tests PASS.
- Current server-routing/operator, generated-subscription, runtime-client,
  Remnawave matrix, infrastructure-client, and contract slice: 90 backend tests
  PASS with `--no-cov`.
- VPN Test Agent relay endpoint slice: 27 tests, Ruff, format, and mypy PASS.
- Fresh production Remnawave dump replayed twice in PostgreSQL 17.7: 8 hosts,
  8 policy links, 0 stale Frankfurt links, 1 isolated bridge inbound, and no
  duplicate state.
- The final seed was then replayed twice against the isolated post-routing dump:
  Moscow retained 2 `MSK_SMART_*` node links and 2 `MSK_SMART_*` public Host
  bindings, with 0 stale Moscow base links. Its exact visible Premium-host
  invariant passed on both runs.
- Rollback now restores profiles and node assignments before force-restarting
  both affected nodes; it cannot checkpoint `rolled_back` while an old dataplane
  remains loaded. Existing bridge users fail preflight if any non-bridge squad
  is present, and every reuse patch assigns exactly one bridge squad.
- Backend and task-worker Remnawave clients ignore ambient proxy environment
  variables. The Moscow relay socket definitions now cap each source at 256
  connections in addition to the global 4096 limit; production rollout of the
  socket-only hardening is intentionally deferred until the phone-test window
  closes.
- Final production operator dry-run after both node restarts: base profile and
  INCY header were no-op; Frankfurt and Moscow each exposed 2 public hosts and
  3 profile inbounds; both isolated bridge users were reused; neither bridge
  had a public host. Backend and Remnawave containers remained healthy.
- Temporary production operator files, in-container working rollback manifests,
  disposable probe files, and the diagnostic Xray image were removed. The
  checksummed rollback manifests and database dumps remain only in the named
  backup directories with mode `0600`.
- Independent adversarial and security re-reviews found no unresolved finding
  in the final requested remediation set; final verifier findings were resolved
  by canonical CIDR and control-plane URL/secret validation.
- Independent follow-up verifier, adversarial, and security re-reviews found no
  actionable finding after the DNS source-class, remote-state, import, plan
  allowlist, lifecycle, Ozon-boundary, and PII remediations. The user-owned phone
  retry and post-retry account deletion remain intentionally open.

## Rollback

1. Stop new VPN Tester runs and restore the backend compose file from the
   timestamped `pre-trigger-guard` backup, returning the backend to the previous
   image tag. Restore the primary agent compose backup and previous agent image.
2. Stop and disable the application-host relay service, remove only its named
   bridge-scoped UFW rule, and verify no listener remains on the relay port.
3. Stop the two regional agent services or restore their immediately preceding
   compose backups. Remove only the source-specific regional UFW/nftables rules.
4. Restore the previous Remnawave Config Profile from the checksummed backup
   through the supported profile editor/API. Use the database dump only as a
   last-resort scoped restore, never as a broad application rollback.
5. Reapply the restored profile to all four nodes, restart them through
   Remnawave, and verify Xray health plus both 443 and 8443 listeners.
6. Fetch a fresh disposable subscription, run `mihomo -t`, check the generated
   transport counts, and prove XHTTP before reopening the gate.
7. For the isolated server route, run the operator with `--rollback` and the
   root-only API manifest, then remove only the named source-restricted Moscow
   and Frankfurt `9443` firewall rules. The pre-change and post-change
   Remnawave dumps remain the last-resort recovery artifacts.

## User-Owned INCY Verification

The initial rollout cleanup removed its disposable target and canary accounts
before this follow-up began. The user subsequently registered a new follow-up
account. Current production checks show exactly one corresponding CyberVPN
account with a subscription/Remnawave reference and exactly one Remnawave user;
that account is intentionally retained for the post-DNS phone retry.

1. Fully close INCY and toggle airplane mode before the retry so the phone and
   client do not retain the pre-AAAA negative DNS cache.
2. Refresh the existing subscription in the latest INCY client. Do not reuse an
   old QR code or a profile imported before this follow-up account was created.
3. Confirm that INCY shows the four target locations and both RAW/TCP and XHTTP
   variants where the client exposes transport names.
4. Select each concrete location/transport instead of Auto. Frankfurt and
   Moscow should show DE for an ordinary non-RU IP check; both Moscow profiles
   now use Frankfurt for default traffic by design.
5. On every Frankfurt and Moscow profile, verify YouTube playback and open
   Ozon. Ozon must open without disabling VPN and stays on the Moscow route.
6. Confirm that a common DoubleClick URL and Rutracker do not load. Native
   YouTube in-stream ads remain a phone-side observation, not a guaranteed
   domain-filter result.
7. After the phone result is captured, remove the exact follow-up account from
   both CyberVPN and Remnawave and verify zero exact matches.

For a failed phone check, report only: local timestamp and timezone, INCY
version, phone OS/version, Wi-Fi or mobile network, selected location and
transport, whether connection state changed, whether HTTPS traffic passed, exit
country if available, and the exact visible error or screenshot. Never send the
subscription URL, QR payload, VLESS UUID, Reality key, short ID, token, cookie,
or invite code.
