# Stage1 Task1/Task2 r3 readiness and VPN runtime evidence

## Scope

Sanitized production evidence for the post-fix Premium Smart RU server/generated
path and the Task2 fail-closed boundary. Snapshot window:
`2026-07-11T16:42Z` through `2026-07-11T18:16Z`.

The later recheck at `2026-07-11T19:01Z` is recorded in the final section of
this file. It **supersedes only** the earlier BGP `Connect/DOWN` and DNS
`NXDOMAIN` rows. It does not supersede missing manifest/listener/profile/runtime
matrix or the fail-closed readiness requirement.

This file contains no subscription URL/body, customer identifier, VLESS UUID,
Reality key/short ID, invite code, bridge credential, token, cookie or private
key. Public infrastructure endpoints are omitted because the architecture
document already owns the internal topology inventory.

## Control plane

| Check | Result | Sanitized evidence |
|---|---|---|
| CyberVPN backend image | PASS | `cybervpn/cybervpn-backend:task1-task2-20260711-r3-readiness` |
| Backend container health | PASS | Docker reported `healthy`; `GET http://127.0.0.1:18080/health` returned `{"status":"ok"}` |
| Remnawave | PASS | `2.8.0-raw-vision-flow.2`, Docker health `healthy` |
| Task2 setting | PASS fail-closed | in-container sanitized probe returned `data_plane_ready=false`, expected gate `closed` |

The running `r3-readiness` snapshot uses one environment boolean. This snapshot
proves its present value is closed; it does not prove protection from a future
erroneous configuration change. A signed-attestation implementation was added
to the worktree later and is described separately in the later recheck.

## SPB runtime boundary

| Check | Result | Meaning |
|---|---|---|
| Moscow RAW relay socket | PASS | active/listening; triggered service may be inactive while idle |
| Moscow XHTTP relay socket | PASS | active/listening; triggered service may be inactive while idle |
| Remnanode owner | PASS | Docker `remnawave/node:2.8.0` running; inactive systemd `remnanode` is not the owner |
| BIRD | PARTIAL infrastructure only | BIRD `2.14` active; IPv4 protocol `Connect`, channel `DOWN` |
| Antifilter collector timer | PARTIAL infrastructure only | active; candidate generation remains fail-closed |
| Antifilter exporter | PASS fail-closed | socket access fixed; rejects missing required community instead of publishing partial data |
| Authoritative Antifilter manifest | BLOCKED | missing |

These Task2 checks require readiness to remain false. They are not a degraded
data-plane PASS.

The rollout corrected two infrastructure defects: BIRD config is now
`root:bird 0640`, and the exporter service uses group `bird` to read the BIRD
control socket. It also changed bounded eBGP multihop from an insufficient TTL
5 to TTL 32 after production probes showed TTL 8 expiring and TTL 16 reaching
the official peer. A packet capture then showed correctly sourced TCP/179 SYN
packets with TTL 32 and no peer response. Official peer-side registration for
the SPB source remains external and CAPTCHA-gated; no BGP or manifest PASS is
claimed.

## Task2 DNS boundary

| Check | Result | Meaning |
|---|---|---|
| Dedicated SPB IPv6 | PASS address only | address unit active; DE probe returned `3/3` ICMPv6 at about `33ms` |
| Cloudflare API/export | PASS control plane only | exactly one DNS-only AAAA object has intended address and TTL `300` |
| Cloudflare authoritative NS | BLOCKED | both assigned nameservers returned NXDOMAIN at `2026-07-11T18:16Z` |
| Public resolvers | BLOCKED | `1.1.1.1` and `8.8.8.8` returned NXDOMAIN |

The first create payload was rejected with Cloudflare code `9300` because this
account has DNS tag quota zero. No record was created by that request. The
Task2 Terraform example now omits tags and its focused contract test passed.
The later no-tag API object is not treated as production DNS PASS until the
authoritative answer exists, and it still requires adoption/import into the
canonical Terraform state.

## Task1 seed execution boundary

An isolated disposable PostgreSQL `17.10` rehearsal ran the real INCY seed
wrapper on a clean schema and then repeated the exact command. Both runs
committed with stable `template=1`, hidden injected hosts `8`, virtual host `1`.
Post-rerun checks found eight expected literal bootstrap addresses, zero
mismatches and the expected `4/4` address split. The disposable container and
temporary staging output were removed. Focused contract tests passed with
`--no-cov`; no full backend pytest was run.

## Final generated INCY/HAPP artifact

Sanitized structural contract observed after the literal-bootstrap rollout:

```text
outbounds=10
routing_rules=17
routing_balancers=absent
observatory=absent
default_outbound=eu-de-2
ru_outbound=ru-spb-2
```

Official Xray Core `26.6.27` parsed the final generated body. The cold runtime
series recorded during the same rollout produced:

| Scenario | Result | Selected production path |
|---|---:|---|
| Generic/default traffic | 5/5 | DE XHTTP |
| `ozon.ru` | 5/5 | SPB XHTTP |
| `www.ozon.ru` | 5/5 | SPB XHTTP |

This supersedes the earlier server/generated Ozon failure. It does not prove
phone-side INCY/HAPP import, cache, platform DNS or TUN behavior. Moscow RAW
also remains outside PASS because its repeated `www.ozon.ru` boundary was 3/5.

## Reproduction commands

The commands below are intentionally sanitized and contain no credentials or
subscription material. Authentication and host selection remain in the local
secret store/operator environment.

```bash
docker compose ps --format json
curl -fsS http://127.0.0.1:18080/health
docker exec <backend-container> python -c '<print only readiness boolean>'
systemctl is-active <relay-socket-units>
systemctl is-active bird
systemctl is-active <antifilter-collector-timer>
test -f /var/lib/cybervpn/antifilter/manifest.json
```

Never attach the generated subscription body or replace the placeholders with
credentials in tracked evidence.

## Open items

- fresh phone-side INCY/HAPP TUN matrix;
- safe automatic INCY/HAPP failover design;
- repeated Moscow RAW reliability;
- Task2 authoritative BGP manifest, DNS Terraform-state adoption,
  listener/profile and matched/unmatched runtime matrix;
- deploy and verify the staged signed-attestation readiness implementation;
- full Task2 account assignment only after the data plane passes.

## Later production recheck: `2026-07-11T19:01Z`

This sanitized recheck was performed after the operator reapplied the official
Antifilter policy selection for the SPB collector address. Commands were
read-only except for manually starting the fail-closed exporter service to
observe its validation result. No route candidate was published.

### Backend and staged signed readiness

| Check | Result | Sanitized evidence |
|---|---|---|
| Running backend | PASS current runtime | `r3-readiness`, Docker `healthy`, local health returned `{"status":"ok"}` |
| Running Task2 gate | PASS fail-closed | environment remains false |
| Running readiness mount | ABSENT | `docker inspect` did not report `/run/cybervpn/readiness/task2` on the running `r3` container |
| Production compose | STAGED only | contains attestation/public-key paths and a read-only Task2 readiness mount |
| `r4-signed-readiness` image | STAGED only | loaded on app host, digest `sha256:63ddcaae...f949847`, not running |
| Attestation directory | intentionally empty | no PASS attestation or public key deployed while Task2 data plane is incomplete |

Current worktree source requires the boolean kill switch plus a valid signed
EdDSA attestation. The table above proves that this source/image is staged, not
the current running production code path.

### BGP and exporter

`birdc show protocols all antifilter_v4` returned:

```text
state=Established
source_address=<SPB collector address>
local_as=64999
remote_as=65444
channel_ipv4=UP
routes_imported=29439
routes_exported=0
hold_timer=240
```

Sanitized route counts by required community:

| Community | Routes | Community | Routes |
|---|---:|---|---:|
| `65444:100` | 21 157 | `65444:110` | **0** |
| `65444:700` | 32 | `65444:710` | 43 |
| `65444:720` | 1 143 | `65444:730` | 179 |
| `65444:740` | 453 | `65444:750` | 1 732 |
| `65444:760` | 289 | `65444:770` | 1 325 |
| `65444:780` | 97 | `65444:790` | 7 |
| `65444:800` | 3 042 | `65444:65444` | 72 |

The BGP session restarted at `2026-07-11T18:55:30Z` after the policy update.
All selected categories except companion community `65444:110` became nonempty.
The official FAQ says `:110` is delivered together with `:100` and that source
lists update hourly. The exporter was started once after the recheck and
correctly rejected the feed:

```json
{"reason":"required community 65444:110 has no IPv4 routes","status":"rejected"}
```

No `source.json` or `manifest.json` was created under the Antifilter candidate
directory. This preserves the strict required-community gate and keeps Task2
fail closed.

### DNS, bridge boundary and Remnawave metadata

Read-only command record:

| Checked at UTC | Command | Exit | Sanitization |
|---|---|---:|---|
| `2026-07-11T19:17:20Z` | `Resolve-DnsName -Name spb-exceptions.cyber-vpn.org -Type AAAA -Server <resolver> -DnsOnly` for `1.1.1.1` and `8.8.8.8` | 0 | no secret input |
| `2026-07-11T18:47Z` | `nft list table inet cybervpn_spb_de_exceptions_bridge`; `ufw status numbered`; `ss -lntup` filtered to `9444` on DE | 0 | public topology only |
| `2026-07-11T19:05Z` | `psql -Atc <aggregate Task1/Task2 object-count queries>` inside the Remnawave PostgreSQL container | 0 | names/counts only; UUIDs and users not selected |

Normalized DNS output:

```text
1.1.1.1|spb-exceptions.cyber-vpn.org|AAAA|ttl=300|2a01:e5c0:1368::3
8.8.8.8|spb-exceptions.cyber-vpn.org|AAAA|ttl=299|2a01:e5c0:1368::3
```

Normalized DE firewall/listener output:

```text
nft table inet cybervpn_spb_de_exceptions_bridge:
  set spb_ipv4 = { 193.233.91.99 }
  tcp dport 9444 ip saddr @spb_ipv4 accept
  udp dport 9444 ip saddr @spb_ipv4 accept
  tcp dport 9444 counter packets 1 bytes 52 drop
  udp dport 9444 counter packets 0 bytes 0 drop

ufw:
  9444/tcp ALLOW IN 193.233.91.99
  9444/udp ALLOW IN 193.233.91.99

ss listener on 9444: absent
```

Normalized aggregate SQL output:

```text
task1_external_squad|1
task1_customer_squad|1
task2_external_squad|1
task2_customer_squad|1
task2_bridge_squad|1
task2_mihomo_template|1
task2_bridge_inbound_total|0
task2_customer_bridge_membership|0
```

| Check | Result | Sanitized evidence |
|---|---|---|
| Dedicated Task2 AAAA via `1.1.1.1` | PASS DNS boundary | returned the configured SPB IPv6 |
| Dedicated Task2 AAAA via `8.8.8.8` | PASS DNS boundary | returned the same configured SPB IPv6 |
| SPB dedicated IPv6 address | PASS persistent | `cybervpn-spb-listener-ipv6.service` enabled/active, `Result=success`, owned marker matches the configured CIDR |
| DE `9444` firewall | PASS prepared boundary | nftables and UFW allow TCP/UDP only from the exact SPB IPv4; exact allow/drop excerpts recorded above |
| DE `9444` listener | ABSENT | no TCP/UDP listener; firewall readiness is not bridge readiness |
| Task2 Remnawave external/customer/bridge squads | PRESENT metadata only | sanitized read-only SQL returned one of each |
| Task2 Mihomo template | PRESENT metadata only | sanitized read-only SQL returned one |
| Task2 bridge inbound | ABSENT | sanitized read-only SQL returned zero; customer bridge membership also zero |

The DNS record still requires import/adoption into canonical Terraform state.
The bridge firewall was applied with a production override despite the source
role default remaining disabled. The listener/profile, authoritative manifest,
matched/unmatched route matrix and bridge-down proof remain absent.

### Remaining blockers after the later recheck

- `65444:110` must become nonempty or receive an authoritative provider/product
  decision; the exporter gate must not be weakened merely to generate output;
- approved candidate/manifest and compile/publish/LKG proof;
- DE bridge credential/listener and SPB customer profile/Host;
- RAW/XHTTP x TCP/UDP matched/unmatched and bridge-down route matrix;
- deployment and negative verification of `r4-signed-readiness`, followed by a
  signed PASS attestation only after the complete data plane succeeds;
- fresh phone-side INCY/HAPP TUN/DNS/cache proof and unresolved Task1 failover
  reliability checks.

## `r4` deployment and follow-up: `2026-07-11T19:25..19:32Z`

This later section supersedes the previous `r3`/staged-readiness rows. The
earlier rows remain as deployment history.

### Signed-readiness backend

| Check | Result | Sanitized evidence |
|---|---|---|
| Running image | PASS | `task1-task2-20260711-r4-signed-readiness`, digest `sha256:63ddcaae...f949847` |
| Container health | PASS | Docker `healthy`; `/health` returned `{"status":"ok"}` |
| Dependency readiness | PASS | `/readiness`: database, Redis and queue `ok`; queue depth `0` |
| Task2 kill switch | PASS fail-closed | runtime value `false` |
| Signed readiness mount | PASS | `/srv/cybervpn/readiness/task2 -> /run/cybervpn/readiness/task2`, `rw=false` |
| Readiness files | intentionally absent | directory empty; no public key or PASS-attestation deployed |
| Task1 decision | PASS unaffected | readiness helper returned false/no block for `premium_smart_ru` |
| Task2 decision | PASS fail-closed | blocked with reason `spb_de_exceptions_data_plane_not_ready` |
| Startup errors | PASS | no `ERROR`, `CRITICAL` or `Traceback` in the deployment log window |
| Rollback | PREPARED | timestamped `.env` backup and r3 rollback image retained |

The one-time local and remote image tar files and deployment helper were removed
after verification. The rollback image and production `.env` backup remain.

### BGP and direct-RKN source

At `2026-07-11T19:25:19Z`, BGP remained `Established`, IPv4 channel `UP`, with
29 462 imported and 0 exported routes. Current required-community counts:

```text
100=21156 110=0 700=32 710=41 720=1143 730=179 740=453
750=1731 760=289 770=1352 780=97 790=7 800=3042 65444=72
```

Sample `birdc show route ... all` output confirmed BGP communities are preserved
by the import filter. No route in the received RIB carries `65444:110`.
Antifilter's official FAQ links `:110` to the direct-RKN JSON source; a focused
request to that official API returned HTTP `522`. This explains a plausible
provider-source outage but does not permit an empty category. Exporter behavior
remains unchanged: reject, no candidate, no manifest.

### Parameterized invite operator

The rollout SQL now requires three psql variables from the approved operator
channel and contains no invite literals. It avoids code values in exceptions
and output. Focused contract test and Ruff checks passed.

An idempotent production execution discovered the existing values inside the
database session without printing them. Sanitized result:

```text
legacy | revoked | premium_smart_ru
task1  | active  | premium_smart_ru
task2  | active  | premium_spb_de_exceptions
```

Both product rows remain `multi_use`, `lifetime`, device limit `5`, per-user
redemption cap `1`, and max redemptions `100000`. Task2 redemption/provisioning
is protected by the current `r7` fail-closed readiness decision.

## `r5` bearer-sanitization deployment: `2026-07-11T19:45..19:51Z`

This section supersedes `r4` only as the current backend runtime. The `r4`
section remains valid deployment history and its signed-readiness behavior is
preserved by `r5`.

| Check | Result | Sanitized evidence |
|---|---|---|
| Focused source tests | PASS | 46 exception-handler, rate-limit, shared logging and invite contract tests |
| Static checks | PASS | Ruff and focused mypy passed for the changed backend modules |
| Image build | PASS | `task1-task2-20260712-r5-bearer-sanitization`, image ID `sha256:8e023a6f...d91700` |
| Image smoke | PASS | `/api/sub/{token}` became `/api/sub/[REDACTED]`; bucket was `subscription_gateway` |
| Artifact integrity | PASS | local and remote tar SHA-256 matched before load; loaded image ID matched the built image |
| Running image | PASS | production container uses the exact `r5` tag and image ID |
| Container health | PASS | Docker `healthy`; `/health` returned `status=ok` |
| Dependency readiness | PASS | `/readiness`: database, Redis and queue `ok`; queue depth `0` |
| Task1 decision | PASS unaffected | runtime helper returned false/no block for `premium_smart_ru` |
| Task2 decision | PASS fail-closed | kill switch remains `false`, no attestation file, reason `spb_de_exceptions_data_plane_not_ready` |
| Bearer-path runtime smoke | PASS | production container redacted the test path and used the shared non-secret bucket |
| Post-deploy logs | PASS | no `ERROR`, `CRITICAL`, `Traceback` or test bearer value in the deployment window |
| Rollback | PREPARED | timestamped pre-r5 `.env` backup and timestamped r4 rollback image retained |
| Temporary artifacts | REMOVED | local/remote tar and one-time deployment scripts removed after verification |

The post-selection BGP sample at `2026-07-11T19:51:04Z` remained
`Established` with the same complete 13-community counts shown above and
`65444:110=0`. The provider-side selection had therefore not populated the
direct-RKN companion community by that checkpoint; the bounded poll continued.

At the ten-minute checkpoint `2026-07-11T19:56:42Z`, `65444:110` was still
zero. A read-only browser inspection of the Antifilter form for the SPB source
IP showed the combined `65444:100, 65444:110` option checked, together with all
required `700..800` options and the custom `65444:65444` list. There is no
separate provider checkbox for `:110`.

A BIRD inbound Route Refresh then completed without dropping the established
session. Received update count increased from about 29.6k to 49.7k as the peer
replayed its export, while accepted routes remained 29 462 and a direct query
still returned no `65444:110` route. The official direct-RKN API also timed out
from the SPB node after 20 seconds with HTTP code `000` and zero bytes. Together
these observations make stale session state, missing local selection and the
import filter unlikely explanations. They do not independently prove the
provider's internal root cause; the missing authoritative companion feed
remains the fail-closed blocker.

## `r6` product-security deployment: `2026-07-11T20:28..20:33Z`

This section supersedes `r5` only as the current backend runtime. Earlier r4/r5
sections remain valid deployment history.

| Check | Result | Sanitized evidence |
|---|---|---|
| Integrated focused tests | PASS | 92 Sentry/path, fake-Redis, exception, rate-limit, invite, gateway-squad and entitlement-replay tests |
| Static checks | PASS | Ruff, format check and mypy passed on 13 affected files / 6 source modules |
| Sentry path privacy | PASS | event and transaction URLs redact `/api/sub/{token}`, including mixed-case path variants |
| Tokenized route keys | PASS | admin invite and Telegram magic-link paths use redacted fallback buckets; fake Redis contains no synthetic tokens |
| Gateway squad isolation | PASS | resolved product must match actual Remnawave external squad; Smart RU and Task2 mismatch tests fail closed |
| Task2 grant replay | PASS | persisted Task2 replay re-evaluates readiness; Smart RU and generic non-Task2 idempotency remain unchanged |
| Image build/smoke | PASS | `task1-task2-20260712-r6-product-security`, image ID `sha256:00ff10d8...70608a`; Sentry, Redis, squad and readiness smoke passed |
| Artifact integrity | PASS | local/remote tar SHA-256 matched; loaded/running image ID matched the built image |
| Running image | PASS | production container uses exact r6 tag/image ID and reports Docker `healthy` |
| Health/readiness | PASS | `/health` status `ok`; database, Redis and queue `ok`, queue depth `0` |
| Task1 gateway | PASS live | active Smart RU short UUID stayed inside the server process; gateway returned HTTP `200`, JSON, 10 814 bytes |
| Task2 decision | PASS fail-closed | kill switch `false`, attestation absent, reason remains `spb_de_exceptions_data_plane_not_ready` |
| Post-deploy logs | PASS | no `ERROR`, `CRITICAL`, `Traceback` or r6 synthetic bearer value in deployment window |
| Rollback | PREPARED | timestamped pre-r6 `.env` backup and r5 rollback image retained |
| Temporary artifacts | REMOVED | local/remote tar and all one-time deploy/probe scripts removed |

The real Task1 gateway smoke also exercises the new provider-squad comparison,
so `Task1 unaffected` is no longer based only on a helper invocation. No real
subscription token, account identifier, squad UUID or response body was
printed or persisted in this evidence.

The bounded post-selection BGP poll completed all 12 attempts from
`2026-07-11T19:39:53Z` through `20:41:21Z`. Every checkpoint returned
`community_65444_110=0`; the process exited normally after the final attempt.
No readiness state, candidate or manifest was changed by the poll.

## `r7` sparse-replay guard deployment: `2026-07-11T20:43..20:46Z`

The final adversarial recheck found a sparse existing-grant shape where Task2
identity lived only in `service_identity.service_context`. The idempotent
pre-return gate now considers persisted grant snapshot, service context and
incoming candidate metadata before deciding whether readiness must be
re-evaluated.

| Check | Result | Sanitized evidence |
|---|---|---|
| Sparse replay regression | PASS | empty existing grant snapshot + Task2 service context + readiness false raises `spb_de_exceptions_data_plane_not_ready` |
| Focused entitlement slice | PASS | 13 tests; Smart RU, generic non-Task2 and metadata-drift behavior retained |
| Integrated focused slice | PASS | 93 tests across all r6/r7 security and replay paths |
| Static checks | PASS | scoped Ruff, format and mypy passed after the final code change |
| Image build/smoke | PASS | `task1-task2-20260712-r7-sparse-replay-guard`, image ID `sha256:9150df21...5634f`; sparse service-context decision failed closed |
| Running image | PASS | exact r7 tag/image ID; Docker `healthy` |
| Health/readiness | PASS | `/health` ok; database, Redis and queue ready, queue depth `0` |
| Task1 gateway | PASS live | repeated sanitized active Smart RU request returned HTTP `200`, JSON, 10 814 bytes |
| Task2 decision | PASS fail-closed | kill switch `false`, attestation absent, sparse and normal Task2 decisions blocked |
| Post-deploy logs | PASS | no `ERROR`, `CRITICAL`, `Traceback` or r7 synthetic bearer value |
| Rollback | PREPARED | timestamped pre-r7 `.env` backup and r6 rollback image retained |
| Temporary artifacts | REMOVED | local/remote tar and one-time deploy/probe scripts removed |

### Post-r7 target-account and collector audit

Sanitized production reads proved the exact target account exists once and has:

```text
identity | premium_smart_ru | active | 1
identity | unknown          | active | 1
grant    | premium_smart_ru | active | 1
```

The unknown identity is legacy account-scoped metadata with an empty
`service_context` and no entitlement grant. The target Smart RU identity maps
to an active Remnawave user in the configured Smart RU external squad, and its
own gateway request returned HTTP `200`, JSON, 10 814 bytes. No account ID,
provider subject, short UUID or response body was printed.

The three production invite roles were revalidated without printing code
values: legacy is revoked on `premium_smart_ru`; Task1 is active on
`premium_smart_ru`; Task2 is active on `premium_spb_de_exceptions`. There is no
Task2 grant on the target account while readiness is false.

The BGP exporter timer remains `enabled` and `active`, with hourly retries. The
latest service run failed closed with exact reason
`required community 65444:110 has no IPv4 routes`; the candidates directory is
empty. Once the peer supplies the missing community, the timer can create a
candidate automatically, but approval/promotion and bridge deployment remain
explicit operator steps.

### Third consecutive goal blocker audit

At `2026-07-11T21:03:06Z`, the third consecutive goal audit reproduced the same
external condition:

```text
BGP state: Established
IPv4 imported: 29451
community_65444_110: 0
collector timer: active
collector result/status: exit-code / 1
candidate files: 0
reject reason: required community 65444:110 has no IPv4 routes
```

The exact unlock signal is a non-empty production `65444:110` route set and a
complete exporter candidate/manifest. Until then, Task2 bridge/profile,
readiness attestation and target-account grant remain intentionally withheld.

## `r8` signed readiness and Task2 activation: `2026-07-12`

This section supersedes `r7` as the current backend runtime and supersedes the
earlier Task2 BGP, readiness-false, bridge-pending, route-matrix-not-run and
target-account-withheld blockers. The r3-r7 sections above remain immutable
deployment and rollback history. The owner-approved Task2 BGP contract now has
13 required communities and does not require `65444:110`.

| Check | Result | Sanitized evidence |
|---|---|---|
| Running image | PASS | production backend uses `task1-task2-20260712-r8-task2-live`; container health is `healthy` |
| Task2 signed readiness | PASS active | read-only signed attestation accepted; runtime readiness is true; invalid, stale, revoked or mismatched evidence remains fail-closed |
| Task2 BGP contract | PASS | BIRD `Established`, approximately 29.5k IPv4 routes; all 13 approved required categories present; deterministic artifact `ebc9e9e499bf1c63...` active and LKG with 21,407 IPv4 union prefixes |
| Public DNS | PASS | `spb-exceptions.cyber-vpn.org` resolves to the reviewed A record; customer AAAA was removed after ingress isolation review |
| SPB-DE bridge | PASS | IPv6 TCP/UDP `9444` listener active; firewall accepts only the exact SPB IPv6 peer and drops other sources; bridge returned DE egress |
| Isolated customer ingress | PASS | SPB listens on dedicated IPv4 RAW `4443` and XHTTP `8444`; Task2 routing/squad contain only the two Task2 tags and do not include preserved Smart RU inbounds |
| XHTTP synchronization | PASS | dedicated Task2 inbound and public Host use the same path derived from the preserved source profile; generated profile no longer receives a listener-side `404` |
| Route matrix | PASS | RAW/XHTTP ordinary destination exits SPB; matched domain/literal and UDP traffic exit DE; bridge-down matched traffic fails closed while unmatched SPB traffic remains available |
| Gateway formats | PASS | generic, INCY, HAPP and Mihomo returned HTTP `200`; the Task2 subscription exposes exactly RAW and XHTTP customer profiles and no bridge profile |
| Target account | PASS | sanitized database audit found two active lifetime grants and two subscription-scoped identities, one per product; provider subject/subscription key fields are present and Task2 context matches its product/profile |
| Invites | PASS | replacement Task1 and Task2 lifetime invite rows are active; the legacy row remains revoked; literal codes are not recorded here |
| Final logs | PASS | backend, Remnawave and both Remnanodes reported zero `ERROR`/`CRITICAL`/traceback/fatal pattern lines in the final 30-minute audit window |
| Canary and temporary artifacts | PASS removed | activation canary, temporary Xray containers/configs and remote audit files were removed; timestamped rollback manifests remain mode `0600` outside the repository |
| Rollback | SUPERSEDED | this r8 snapshot predates the production drill; the later `v13 -> v14` section records the completed rollback, restore and post-restore route matrix |

The final exact-account data-plane check used the official Xray core without
persisting the subscription URL, VLESS UUID, short UUID, account identifier or
generated body. RAW and XHTTP both returned an ordinary HTTP response for an
unmatched destination and the reviewed DE public egress for an Antifilter-
matched destination. Phone-side INCY import/cache/DNS/TUN behavior remains a
separate manual evidence boundary and is not claimed by this server-side proof.

### Security superseding check: dedicated IPv4 ingress `v13`

The initial dual-stack workaround temporarily added preserved Smart RU
inbound tags to Task2 routing. Security review correctly rejected that shape:
Host/squad visibility cannot isolate Xray rules that match only `inboundTag`.
Production was migrated to dedicated IPv4 ports `4443/8444`; preserved Smart RU
remains on `443/8443`, Task2 routing and customer squad contain only the two
Task2 inbounds, customer AAAA is absent, and UFW allows the two new TCP ports.

Official Xray `26.6.27` exact-account recheck passed for both RAW and XHTTP:
controlled non-listed traffic reached the probe from SPB `193.233.91.99`, while
Antifilter-matched traffic exited DE `138.124.115.206`; Xray reported zero
error lines. Rollback manifest
`remnawave-task2-dedicated-ipv4-v13.json` is retained mode `0600` outside the
repository. This section supersedes the r8 shared-ingress rows above as the
current customer-ingress design.

### Production rollback drill `v13 -> v14` and SMTP enforcement

On `2026-07-12`, Task2 completed an actual rollback-and-restore drill against
production Remnawave state. A fresh PostgreSQL dump and checksum were captured
before mutation. A private copy of the mode `0600` v13 manifest reached
`rolled_back`; the current operator then reapplied the same reviewed artifact
into a fresh mode `0600` v14 manifest with phase `applied`.

Post-restore exact-account checks used the official Xray `26.6.27` image:

| Check | Result | Sanitized evidence |
|---|---|---|
| Task2 RAW unmatched | PASS | terminal egress `193.233.91.99` (SPB) |
| Task2 RAW matched | PASS | terminal egress `138.124.115.206` (DE) |
| Task2 XHTTP unmatched | PASS | terminal egress `193.233.91.99` (SPB) |
| Task2 XHTTP matched | PASS | terminal egress `138.124.115.206` (DE) |
| Xray runtime errors | PASS | zero error lines for both transports |
| Gateway outputs | PASS | generic, INCY, HAPP and Mihomo returned HTTP `200`; dedicated `4443/8444` remained present and bridge `9444` absent |

The canonical Smart RU policy was also corrected so the already-declared SMTP
abuse ports are executable policy rather than metadata only. The compiler now
emits a TCP `25,465,587 -> block` rule before EU/RU routing in Xray and a
`smtp-abuse -> REJECT` rule in Mihomo. Production seeds were applied from a
checksum-bound private stage after another PostgreSQL backup. Remnawave was
restarted to invalidate its in-process template cache.

Production generated-subscription checks proved that INCY, HAPP and Mihomo all
contain the rule. An official Xray `26.6.27` run loaded the final injected INCY
body with 10 outbounds and 18 routing rules; a synthetic connection to
`example.com:25` was rejected with access route `[socks -> block]` and zero
fatal error lines. No subscription URL, user UUID, VLESS credential, template
body or rollback manifest content was persisted in this evidence.

The generated `xray-server.json` was then applied to the existing Frankfurt
and Moscow Smart RU server profiles with the dedicated Task1 operator. Its
read-only plan changed only the two owned profiles from 14 to 15 rules; base
profile and legacy routing header were no-ops. Apply captured another database
backup and a mode `0600` version-3 rollback manifest, switched both nodes and
restarted them successfully.

The exact-account generic/Base64 path was exported without printing links or
credentials. Official Xray `26.6.27` loaded the DE RAW compatibility profile;
normal HTTPS traffic exited DE `138.124.115.206`, while the synthetic SMTP
connection was rejected (`curl` exit `56`) and the client had zero fatal error
lines. This closes the server-side enforcement gap for generic clients in
addition to the full-config INCY/HAPP/Mihomo rule proof. Browser delivery is a
subscription webpage and does not itself create a VPN data plane.

## `r9` isolated Smart RU failover canary and exact cache refresh: `2026-07-12`

This section supersedes the previous statement that automatic INCY/HAPP
failover was still pending. It does not supersede the phone-side evidence gap.
The running backend image is
`task1-task2-20260712-r9-xray-failover-canary-71728ebe`; Remnawave remains
`2.8.0-raw-vision-flow.2`.

The stable Smart RU XRAY_JSON Git blob stayed unchanged across the canary
commits. The isolated canary is selected only by an exact backend-owned JSON
`true` marker on the authoritative Smart RU service identity. Caddy strips
incoming `X-CyberVPN-*` values and the backend reconstructs trusted upstream
headers, so User-Agent, query, cookie or a spoofed canary header cannot enroll
a client.

### Checksum-bound seed and Remnawave cache refresh

The canonical canary changed its single background observatory from the
EU-only gstatic probe to the shared RU-accessible Ozon URL. Xray core
`v26.6.27` does not require HTTP `204` for background observatory: it disables
redirect following and treats any completed HTTP response as alive without
checking the status code. The external harness still verifies actual route,
HTTP outcome, failure behavior and recovery instead of treating observatory
state as sufficient evidence.

Production applied the then-current `98d52df0` seed runner from a private
archive whose SHA-256 was checked before extraction. The artifact contract
validated the compiler source and generated byte hashes before opening the SQL
transaction. A PostgreSQL subscription-template backup was captured first.
Commit `7fd6011a` is a post-production guard/test/docs hardening change: it makes
cache-container omission and zero-key invalidation fail closed by default, but
it is not claimed as the binary that performed this recorded production seed.

| Check | Result | Sanitized evidence |
|---|---|---|
| Seed transaction | PASS | two XRAY_JSON templates, eight injected Hosts and one virtual Host remained at the exact idempotent counts |
| Stable artifact | PASS unchanged | checked Git blob is identical before/after canary change |
| Canary artifact | PASS | staged SHA-256 begins `caf2da52c6b1...`; observatory probe is the reviewed Ozon URL |
| Cache refresh | PASS | runner resolved the two fixed template names and UUIDs, then issued exact-key Valkey `UNLINK`; one currently cached key was removed |
| Cache safety | PASS | no wildcard scan/delete, no shell command, invalid prefix/mode fails before mutation; `--seed main` cannot request INCY cache refresh |
| Stale-cache regression | PASS | before exact invalidation the generated response still exposed the prior probe; after invalidation the final generated body exposed the canonical probe |
| Rollback | PASS available | pre-seed PostgreSQL backup retained outside the repository; canary opt-in is independently reversible by removing the server-owned marker |

An earlier Windows-created `git archive` changed JSON line endings. The
checksum gate rejected it before seed execution. Deployment then used the exact
working-tree bytes after proving no diff from the reviewed commit. This is
retained as fail-closed packaging evidence, not as a successful apply.

### Final Remnawave-generated four-phase Xray proof

The canary marker is written before the probe and removed automatically by the
trap on any failed or experimental run. It remained enabled only after both
INCY and HAPP generated bodies matched and all four official Xray `26.6.27`
phases passed:

| Phase | EU selected route | RU selected route | Result |
|---|---|---|---|
| Normal | `eu-de-2` | `ru-spb-2` | PASS, both HTTP probes succeeded, zero fatal lines |
| Primaries unavailable | `eu-nl-2` | `ru-msk-2` | PASS, regional fallback only, zero fatal lines |
| All four transports unavailable | `block` | `block` | PASS, both connections failed closed; no `DIRECT` or cross-region route |
| Recovery | `eu-de-2` | `ru-spb-2` | PASS after bounded retry, primaries restored, zero fatal lines |

The final canary structure is 12 outbounds and 20 rules: eight injected VLESS
outbounds, `direct`, `block`, two loopback outbounds, four regional balancers
and one observatory. The stable structure remains 10 outbounds and 18 rules
without balancers or observatory.

### Task2 and Cloudflare regression checks after the canary seed

Task2 was rechecked because the INCY seed updates shared Remnawave Host rows.
Fresh official Xray clients returned Yandex HTTP `301` and example.com HTTP
`200` over both dedicated RAW `4443` and XHTTP `8444`, with zero fatal errors.
Generic, INCY, HAPP and Mihomo gateway requests all returned HTTP `200`; exact
Task2 squads and service context matched, dedicated ports were present and the
private bridge port `9444` was absent from customer output.

The Cloudflare credential was passed to the API over process stdin and was not
printed. A read-only request through the production app network confirmed:

```text
token_status=active
active_zone_count=1
record_count=1
record=A spb-exceptions.cyber-vpn.org 193.233.91.99 ttl=300 proxied=false
```

The token and DNS record ID are not stored in this evidence. Public DNS and
Cloudflare state are correct, but canonical Terraform adoption remains open:
the local environment does not have the AWS/S3 credentials or real backend
configuration required to access `cybervpn-terraform-state` safely.

### Remaining boundaries

- Physical phone-side INCY/HAPP import, TUN, cache and DNS behavior is not
  proven by the server-side canary and remains manual evidence.
- The canary is enabled only for the exact opted-in service identity; broad
  rollout requires a separate device soak and staged expansion decision.
- Raw HWID/device/client-IP forwarding and third-party DoH still require an
  explicit privacy/retention decision.
- Home monitoring remains under owner-approved maintenance; direct runtime
  evidence is used temporarily and monitoring silence is not health evidence.
