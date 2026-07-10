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
| AAAA records | 0 unexpected public node records |
| Provider mode | Node records confirmed DNS-only |
| External reachability | 8/8 TCP endpoints reachable: ports 443 and 8443 on four nodes |
| Node listeners | 8/8 listeners present in the node-loaded Xray runtime |
| Node health | Four Remnanode services healthy after synchronization |

The home monitoring host `10.10.10.34` was not started or contacted because it
is under maintenance and was explicitly excluded from this task.

## Authoritative References

The production model and compatibility decisions were checked against the
current Remnawave documentation and source, rather than inferred from the local
adapter alone:

- Remnawave Config Profiles: <https://docs.rw/learn-en/config-profiles/>
- Remnawave Nodes: <https://docs.rw/learn-en/nodes/>
- Remnawave Hosts: <https://docs.rw/learn-en/hosts/>
- Remnawave Squads: <https://docs.rw/learn-en/squads/>
- Official Remnawave backend: <https://github.com/remnawave/backend>
- Official XTLS Reality reference: <https://github.com/XTLS/REALITY/blob/main/README.en.md>
- Official Xray Reality server example:
  <https://github.com/XTLS/Xray-examples/blob/main/VLESS-TCP-XTLS-Vision-REALITY/config_server.jsonc>

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
- Remnawave compatibility patch: 4 Node tests PASS.
- Independent adversarial and security re-reviews found no unresolved finding
  in the final requested remediation set; final verifier findings were resolved
  by canonical CIDR and control-plane URL/secret validation.

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

## User-Owned INCY Verification

The target account is absent from both the CyberVPN application database and
Remnawave, so a clean registration can start without reusing cached state.

1. Register the account in the public cabinet and complete email verification.
2. Enter the authorized invite code during onboarding and confirm that the
   subscription becomes active without an Internal Server Error.
3. Import the new subscription into the latest INCY client. Do not reuse an old
   QR code, cached profile, or previously imported subscription.
4. Confirm that INCY shows the four target locations and both RAW/TCP and XHTTP
   variants where the client exposes transport names.
5. Select each concrete location/transport instead of Auto. Open an HTTPS site,
   then check the exit country with `https://ipwho.is/`.
6. Repeat at least one Russian and one European profile on Wi-Fi and mobile data.
7. Confirm normal DNS resolution, no immediate disconnect, and expected Smart RU
   routing for representative RU and non-RU sites.

For a failed phone check, report only: local timestamp and timezone, INCY
version, phone OS/version, Wi-Fi or mobile network, selected location and
transport, whether connection state changed, whether HTTPS traffic passed, exit
country if available, and the exact visible error or screenshot. Never send the
subscription URL, QR payload, VLESS UUID, Reality key, short ID, token, cookie,
or invite code.
