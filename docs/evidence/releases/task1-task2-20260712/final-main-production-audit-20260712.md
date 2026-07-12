# Task1/Task2 final main and production audit

Date: `2026-07-12`

Status: `PARTIAL`. The source merge, backend rollout, product provisioning,
Remnawave membership, generated delivery and the production slices documented
below are verified. Repository-controlled and external/manual blockers from the
original TZ Definitions of Done remain and are listed explicitly below.

## Source and release identity

| Item | Verified value |
|---|---|
| Repository | `Beep206/CyberVPN` |
| Pull request | `#99` |
| Reviewed head | `12215877380353cc27ce42d80f14ab2600dc4fdb` |
| Main merge commit | `c9dd3ca9ba68ad45510b7e7c3de412ac3b1e1e61` |
| Merge method | merge commit, retained for one-command rollback |
| Previous backend image | `task1-task2-20260712-r9-xray-failover-canary-71728ebe` |
| Current backend image | `task1-task2-20260712-r10-main-c9dd3ca9` |
| Current backend image digest | `sha256:ebde134aab5d6c515c5b8a94abe5a1134b7a3d91ad8c2db040aa54003e1263c3` |

The source archive was generated from the merge commit, transferred through the
approved SSH channel, and verified before build with SHA-256
`b2eba15be67ed07477b759d122776c7ef07422e87fe5761339ec904e3b526a4a`.
The previous immutable image and the pre-rollout compose environment backup were
retained on `prod-app-1`.

## CI and local gates

The GitHub API was queried for pull-request workflows associated with reviewed
head `12215877`. The following twelve runs were `completed/success`:

| Workflow | Run ID |
|---|---:|
| Backend CI | `29202465598` |
| Frontend CI | `29202465584` |
| API Contract Validation | `29202465615` |
| Backend Security | `29202465589` |
| CodeQL Security Analysis | `29202465632` |
| IaC CI | `29202465575` |
| Task Worker CI | `29202465582` |
| Sentry Privacy CI | `29202465577` |
| Partner Admin Conformance | `29202465570` |
| Partner Observability Conformance | `29202465587` |
| Customer Growth Reporting Governance Conformance | `29202465610` |
| Customer Growth Notification Conformance | `29202465637` |

The merge PR is [#99](https://github.com/Beep206/CyberVPN/pull/99); each run is
available at `https://github.com/Beep206/CyberVPN/actions/runs/<run-id>`.

PR #99 records the following focused release evidence after the final plan-code
correction:

- backend mypy: no issues in `1121` source files;
- focused plan-code, manifest and route tests: pass;
- Ruff check and format: pass;
- frontend, admin and partner `tsc --noEmit`: pass;
- OpenAPI export and generated clients: deterministic on the second generation;
- disposable PostgreSQL migration scenarios: `8/8` pass.

The full local pytest suite was not rerun because the owner explicitly requested
focused local tests. The full backend suite ran successfully in GitHub Actions.

## Production backend rollout

The production backend was recreated only after the new image had built. The
unchanged services were not restarted. Alembic ran before the backend health
gate. A bounded health loop had an automatic restore path to the previous image.

Post-rollout readback:

```text
docker health = healthy
restart count = 0
health = ok
readiness database = true
readiness redis = true
readiness queue = true
queue depth = 0
alembic = 20260711_plan_code_len (head)
recent traceback/critical/exception/internal-error lines = 0
```

The live OpenAPI/Pydantic schemas expose plan-code limits `40,40,40` for create,
update and manual-subscription requests. This accepts the complete Task2 plan
code while retaining the database bound.

## Invite and account contract

The audit used the exact owner-supplied invite values and target account through
the approved private execution channel. Literals, customer identifiers and
provider UUIDs are intentionally omitted from this evidence.

| Role | Plan | Status | Policy |
|---|---|---|---|
| Task1 replacement invite | `premium_smart_ru` | active | multi-use, lifetime, device limit 5, per-user cap 1, no expiry |
| Task2 invite | `premium_spb_de_exceptions` | active | multi-use, lifetime, device limit 5, per-user cap 1, no expiry |

The target account has exactly the two required active lifetime product grants
and active Remnawave identities. For both products, provider status is active,
the external squad matches the backend product contract, and the public gateway
resolves the same authoritative product.

Authoritative Remnawave PostgreSQL membership readback:

| Product path | External squad | Internal squad | Internal-squad inbounds |
|---|---|---|---:|
| Smart RU legacy-compatible identity | none | `CYBERVPN_PREMIUM_SMART_RU_NODES` | 10 |
| Smart RU product identity | `CYBERVPN_PREMIUM_SMART_RU` | `CYBERVPN_PREMIUM_SMART_RU_NODES` | 10 |
| Task2 product identity | `CYBERVPN_SPB_DE_EXCEPTIONS` | `CYBERVPN_SPB_DE_NODES` | 2 |

## Generated subscription delivery

The post-deploy probe resolved real provider users from the two active product
grants and called the production gateway. It emitted only structural booleans;
subscription identifiers, URLs and bodies were never printed or persisted.

| Product | Generic | INCY | HAPP | Mihomo |
|---|---|---|---|---|
| `premium_smart_ru` | pass | pass | pass | pass |
| `premium_spb_de_exceptions` | pass | pass | pass | pass |

Every cell means:

```text
HTTP status = 200
content non-empty = true
product header matches authoritative grant = true
private bridge port 9444 absent = true
```

## Fresh production logs and client activity

The production logs were inspected again after the owner reported a phone-side
connectivity failure. During the inspected window, the backend gateway and its
Remnawave upstream returned `HTTP 200` for subscription delivery. No backend or
Remnawave exception, traceback, `5xx`, fatal startup error or container restart
was present.

Authoritative Remnawave traffic state recorded both product identities online:
Task2 through the connected SPB node and Task1 through the connected Moscow
node. Both identities had non-zero traffic counters. This telemetry does not
distinguish a physical client from the isolated operator probes that use the
same identities, so it is evidence of an active data path, not proof of the
phone-side TUN/DNS/user experience.

The Cloudflare API was queried read-only with the approved private token. It
returned exactly one DNS-only `A` record for the Task2 managed alias, pointing
to `193.233.91.99` with TTL `300`. Public recursive DNS returned the same A
record, no customer `AAAA`, and TCP connection checks to `4443` and `8444`
succeeded. The A-only boundary is intentional so client IPv6 resolution cannot
select the private bridge-source address.

## Fresh Task2 egress matrix

The loaded Remnawave profile was read before the probe. Current DNS resolution
places `checkip.amazonaws.com` inside the 21 415-prefix
`DE_EXCEPTIONS_BRIDGE` rule and `whatismyip.akamai.com` outside the union, so it
selects the final SPB `DIRECT` rule. The exact account subscription was then
converted to isolated official Xray `26.6.27` clients:

| Transport | Matched egress | Unmatched egress | Fatal Xray lines |
|---|---|---|---:|
| RAW `4443` | `138.124.115.206` (DE) | `193.233.91.99` (SPB) | 0 |
| XHTTP `8444` | `138.124.115.206` (DE) | `193.233.91.99` (SPB) | 0 |

One bounded XHTTP matched attempt timed out and the next attempt returned the
expected DE egress. The final matrix passed and all temporary subscription and
Xray files were removed. This records the transient rather than converting a
retry into a false first-attempt success.

The matrix was repeated after the phone-side report using a newly downloaded
exact-account subscription. Both transports passed without a retry: matched
destination through DE, unmatched destination through SPB, zero fatal Xray
lines and successful cleanup.

## Fresh Task2 13-category matrix

The complete current active/LKG artifact was read from the retained immutable
release copy. Its version is
`0b4748aaa22e7e7ec8114a2348c18a24fe48df62d64653bdd0fd0cd7d2903f71` and its
raw manifest SHA-256 is
`dc045130d1a532b7dfda8a161726590ffff0c0469cc8e7267371a785e14d92b9`.

The loaded Remnawave `DE_EXCEPTIONS_BRIDGE` rule and artifact union were equal:
`21 415` loaded and expected CIDRs, zero missing, zero extra. Collapsing all
category CIDRs produced the same union, and every category was non-empty and
semantically covered by the loaded rule.

| Category | Category CIDRs | RAW | XHTTP |
|---|---:|---|---|
| RKN | 21 161 | HTTPS pass | HTTPS pass |
| Meta | 32 | HTTPS pass | HTTPS pass |
| Twitter/X | 44 | HTTPS pass | HTTPS pass |
| Netflix | 1 143 | HTTPS pass | HTTPS pass |
| CloudFront | 179 | HTTPS pass | HTTPS pass |
| Microsoft | 453 | HTTPS pass | HTTPS pass |
| Amazon | 1 732 | HTTPS pass | HTTPS pass |
| OpenAI | 289 | TCP `443` pass | TCP `443` pass |
| YouTube | 1 324 | HTTPS pass | HTTPS pass |
| Google | 97 | HTTPS pass | HTTPS pass |
| Telegram | 7 | HTTPS pass | HTTPS pass |
| Discord | 3 042 | HTTPS pass | HTTPS pass |
| Custom networks | 72 | HTTPS pass | HTTPS pass |

Each probe used a current DNS address that was first proven to belong to its
category file, then forced that exact address through the current exact-account
RAW or XHTTP profile. OpenAI uses Azure OpenAI service ranges whose controlled
address accepts TCP but not a generic TLS hostname, so that row is correctly
limited to TCP-connect evidence. Bounded transient timeouts and one XHTTP Meta
HTTP/2 retry occurred before success. Both transports ended with zero fatal
Xray lines and cleanup passed.

The separate matched/unmatched matrix above proves the common loaded rule's DE
egress and SPB default egress on both transports. This category matrix proves
membership, exact loaded-union equality and transport reachability; direct
server-side selected-outbound log capture per category remains an explicit
blocker below.

## Fresh Task1 regional outbound matrix

The current exact-account INCY response contained exactly one full Xray config.
The audit structurally matched the four expected regional selectors and forced
each selector in a separate official Xray `26.6.27` process:

| Selector | Exact egress | RU service check | Fatal Xray lines |
|---|---|---|---:|
| `eu-de-2` | `138.124.115.206` | not applicable | 0 |
| `eu-nl-2` | `138.16.140.44` | not applicable | 0 |
| `ru-spb-2` | `193.233.91.99` | Ozon `307` | 0 |
| `ru-msk-2` | `178.159.94.225` | Ozon `307` | 0 |

The RU egress check uses Yandex Internetometer's IPv4 endpoint because generic
international IP-echo destinations may be sent through the server-side Smart
RU EU compatibility layer and therefore cannot prove the selected RU node.
Bounded transient timeouts were observed before successful DE and Moscow
outcomes; no fatal Xray startup/runtime line was present, and cleanup passed.

## Fresh Task1 route, block and LAN matrix

The current exact-account INCY canary config was validated by official Xray
`26.6.27`, then every request was paired with new access-log lines and its
selected outbound tag:

| Check | Selected tag | Terminal evidence |
|---|---|---|
| Default world | `eu-de-2` | exact egress `138.124.115.206` |
| Yandex RU | `ru-spb-2` | exact egress `193.233.91.99` |
| Ozon RU | `ru-spb-2` | HTTP `307` |
| Gosuslugi RU | `ru-spb-2` | HTTP `200` |
| OpenAI EU | `eu-de-2` | HTTP `403` from the destination |
| GitHub EU | `eu-de-2` | HTTP `200` |
| Discord EU | `eu-de-2` | HTTP `200` |
| YouTube EU | `eu-de-2` | HTTP `200` |
| Loopback LAN | `direct` | local HTTP `200` |
| Ads fixture | `block` | TLS failed closed |
| Torrent fixture | `block` | TLS failed closed |
| TOR best-effort fixture | `block` | TLS failed closed |

The final process had zero fatal Xray lines and all temporary subscription,
config, log, container and local HTTP-server artifacts were removed.

## Fresh Task1 failover and recovery matrix

The canary response was downloaded again from the current exact-account INCY
and HAPP gateway paths. The bodies matched, the four selectors were unique, the
two-stage balancer topology matched the contract, and official Xray `26.6.27`
accepted the generated configuration.

| Phase | EU route | RU route | Outcome | Fatal Xray lines |
|---|---|---|---|---:|
| Normal | `eu-de-2` | `ru-spb-2` | both requests succeeded | 0 |
| Primary down | `eu-nl-2` | `ru-msk-2` | both requests succeeded | 0 |
| All down | `block` | `block` | both requests failed closed | 0 |
| Recovery | `eu-de-2` | `ru-spb-2` | both requests succeeded | 0 |

The primary-down phase selected both expected fallback routes on bounded
attempt 7. Normal and recovery selected their expected primaries on attempt 1.
The all-down phase emitted only the explicit `block` route and did not leak to
`direct`. Temporary configs and containers were removed, and the account's
canary marker remains enabled after the successful run.

## Validation ledger

| Command | Working directory | Exit | Result/evidence |
|---|---|---:|---|
| `backend/.venv/Scripts/python.exe -m pytest backend/tests/contract/test_remnawave_tz_manifest.py -q --no-cov` | `F:\CyberVPN` | 0 | raw-byte manifest contract pass |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests/contract/remnawave/test_repo_docs_alignment.py -q --no-cov` | `F:\CyberVPN` | 0 | four repository/document alignment contracts pass |
| `backend/.venv/Scripts/python.exe -m ruff check backend/tests/contract/test_remnawave_tz_manifest.py backend/tests/contract/remnawave/test_repo_docs_alignment.py scripts/testing/check-remnawave-tz-evidence.py scripts/testing/check-task2-cloudflare-dns.py` | `F:\CyberVPN` | 0 | changed Python lint pass |
| `backend/.venv/Scripts/python.exe -m ruff format --check backend/tests/contract/test_remnawave_tz_manifest.py backend/tests/contract/remnawave/test_repo_docs_alignment.py scripts/testing/check-remnawave-tz-evidence.py scripts/testing/check-task2-cloudflare-dns.py` | `F:\CyberVPN` | 0 | changed Python format pass |
| `backend/.venv/Scripts/python.exe -m json.tool docs/plans/CyberVPN_Remnawave_2_8_0_TZ_manifest.json` | `F:\CyberVPN` | 0 | JSON pass |
| `backend/.venv/Scripts/python.exe scripts/testing/check-remnawave-tz-evidence.py` | `F:\CyberVPN` | 0 | links, fences and secret patterns pass |
| `git diff --check` | `F:\CyberVPN` | 0 | pass |
| `ssh -i <approved-key> root@45.87.41.146 "docker inspect cybervpn-stage1-cybervpn-backend-1 --format '{{.State.Health.Status}} {{.RestartCount}}'; curl -fsS http://127.0.0.1:18080/health; curl -fsS http://127.0.0.1:18080/readiness"` | `prod-app-1` | 0 | healthy, ready, restart count 0 |
| `$env:CLOUDFLARE_API_TOKEN='<private>'; backend/.venv/Scripts/python.exe scripts/testing/check-task2-cloudflare-dns.py` | `F:\CyberVPN` | 0 | token input redacted; A-only DNS and listeners pass |
| `ssh -i <approved-key> root@45.87.41.146 /tmp/run_task2_egress_check.sh` | `prod-app-1` | 0 | private wrapper deleted after run; DE matched, SPB unmatched, fatal 0 |
| `ssh -i <approved-key> root@45.87.41.146 /tmp/run-task2-category-matrix.sh` and `ssh -i <approved-key> root@45.87.41.146 'ONLY_TRANSPORT=xhttp /tmp/run-task2-category-matrix.sh'` | `prod-app-1` | 0 | private wrapper deleted after run; 13/13 RAW and 13/13 XHTTP pass |
| `ssh -i <approved-key> root@45.87.41.146 /tmp/run_task1_outbound_audit.sh` | `prod-app-1` | 0 | private wrapper deleted after run; DE, NL, SPB, Moscow exact egress pass |
| `ssh -i <approved-key> root@45.87.41.146 /tmp/enable-and-verify-exact-canary.sh` | `prod-app-1` | 0 | private wrapper deleted after run; normal/fallback/all-down/recovery pass |
| `ssh -i <approved-key> root@45.87.41.146 /tmp/run-task1-full-route-matrix.sh` | `prod-app-1` | 0 | private wrapper deleted after run; 12/12 route outcomes pass, fatal 0 |

The production wrappers receive subscription URLs and credentials only through
the approved private execution channel. Their sanitized outcome summaries are
recorded above; raw customer configs were removed by cleanup traps.

No invite literal, customer email, short UUID, subscription URL, VLESS UUID,
Reality key, bridge secret, API token or private key is stored in this file.

## Remaining blocker evidence

1. Fresh physical INCY/HAPP device import/TUN verification is not available.
   Server-side official Xray and generated-subscription checks do not replace it.
2. The valid Task2 EdDSA readiness JWT still names predecessor manifest hash
   `f91c659b19257b6d5d1f689af7814076de53d81f0c0711afdc7c6450be27597f`;
   active and LKG use current manifest SHA-256
   `dc045130d1a532b7dfda8a161726590ffff0c0469cc8e7267371a785e14d92b9`. The
   backend currently validates signature, product, policy, time and revocation,
   but does not compare this claim with a trusted current active/LKG hash. The
   repo therefore needs that binding, while the approved offline signer and the
   complete current checksum are required for a truthful JWT rotation. A
   truncated or fabricated hash must not be signed.
3. The Cloudflare A record is live and correct, but canonical Terraform import
   and a no-replace plan require the production AWS/S3 remote-state credentials.
4. The owner-approved monitoring host is under maintenance. Repository metrics
   and alert definitions exist, but fresh dashboard/scrape evidence is deferred.
5. The internal VPN Tester still has no Task2-aware runtime-agent protocol. Its
   Task2 suite truthfully remains `runtime_evidence_status=not_claimed` and
   runtime dispatch fails closed instead of reusing Smart RU assumptions.
6. The 13-category matrix proves the exact loaded union and transport outcomes,
   but direct SPB Xray selected-outbound logs per category are unavailable
   without node access or a Task2-aware runtime agent.
7. A security follow-up must decide whether stable HWID/device metadata and
   client IP forwarding to Remnawave are necessary, then minimize or document
   retention and redaction accordingly.

These items prevent a full `VERIFIED`/`COMPLETE` claim for the original TZ
Definition of Done. They do not contradict the verified live subscription,
gateway, grant, squad or current VPN data-plane evidence.
