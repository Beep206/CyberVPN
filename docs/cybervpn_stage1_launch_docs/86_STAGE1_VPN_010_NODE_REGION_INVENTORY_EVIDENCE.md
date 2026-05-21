> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-05
> Backlog ID: `S1-VPN-010`
> Статус: local region inventory contract completed; real provider/node activation evidence remains required.

# S1-VPN-010 Node And Region Inventory Evidence

## Purpose

`S1-VPN-010` closes the documentation/evidence part of the Stage 1 startup node and region inventory.

This is not a purchase order and not production node proof. The goal is to define the S1 candidate catalogue so marketing, public network surfaces, Remnawave setup and support do not promise locations that were never approved.

## Contract Observed In The Monorepo

Current backend public network surfaces derive public regions from live Remnawave node inventory:

```text
backend/src/presentation/api/v1/public_network/routes.py
backend/src/presentation/api/v1/public_network/schemas.py
backend/src/domain/entities/server.py
backend/src/infrastructure/remnawave/server_gateway.py
```

The important implementation detail is that the current public API groups nodes by `Server.country_code`. It does not expose city-level region IDs yet. For S1, the customer-facing region inventory is therefore defined as 12 distinct countries with one preferred launch city/provider-region per country.

If S1 later needs city-level public regions, the API contract must be extended before public copy advertises multiple cities inside the same country.

## S1 Startup Region Catalogue

These are the approved candidate regions for S1 Controlled Public Beta.

| # | S1 region ID | Public country/region | ISO country code | Preferred city / provider region | S1 role | Launch posture |
|---:|---|---|---|---|---|---|
| 1 | `s1-de-fra` | Germany | `DE` | Frankfurt / Falkenstein / Nuremberg | EU core, default low-risk first path | Primary |
| 2 | `s1-nl-ams` | Netherlands | `NL` | Amsterdam | EU alternate, good peering and fallback | Primary |
| 3 | `s1-fi-hel` | Finland | `FI` | Helsinki | Northern/Eastern Europe and CIS-adjacent latency | Primary |
| 4 | `s1-pl-waw` | Poland | `PL` | Warsaw | Eastern EU fallback and regional coverage | Primary |
| 5 | `s1-gb-lon` | United Kingdom | `GB` | London | Western Europe and English-speaking support coverage | Secondary |
| 6 | `s1-fr-par` | France | `FR` | Paris | Western/Central EU fallback | Secondary |
| 7 | `s1-us-nyc` | United States | `US` | New York / Ashburn | North America baseline; one city only in S1 public API | Secondary |
| 8 | `s1-ca-tor` | Canada | `CA` | Toronto | North America fallback and lower-risk alternate | Secondary |
| 9 | `s1-sg-sin` | Singapore | `SG` | Singapore | Southeast Asia baseline | Primary |
| 10 | `s1-jp-tyo` | Japan | `JP` | Tokyo | East Asia baseline | Secondary |
| 11 | `s1-tr-ist` | Turkey | `TR` | Istanbul | Regional access path; higher provider/legal/abuse validation required | Canary |
| 12 | `s1-kz-ala` | Kazakhstan | `KZ` | Almaty | CIS/Central Asia canary; provider quality validation required | Canary |

## Recommended Activation Tiers

| Tier | Regions | Rule |
|---|---|---|
| Tier A / first live beta | `DE`, `NL`, `FI`, `PL`, `SG` | Activate first if provider contracts, Remnawave node smoke and monitoring pass. |
| Tier B / controlled expansion | `GB`, `FR`, `US`, `CA`, `JP` | Activate after Tier A is stable and support has connection guides. |
| Tier C / canary only | `TR`, `KZ` | Activate only after provider, legal/support, abuse and monitoring evidence. No public promise until live. |

The full S1 catalogue is 12 regions. A smaller first live beta subset is allowed only if the UI and public copy show beta-limited coverage and hide inactive regions.

## Node Slot Template

Each activated region must have at least one production node slot and one staging/test slot. Values containing IPs, hostnames, UUIDs or provider account details must be stored only in protected/redacted evidence, not in public docs.

| Field | Required rule |
|---|---|
| `environment` | `staging` or `production`; never shared between environments |
| `node_name` | Suggested format: `s1-<country>-<city>-<ordinal>`, for example `s1-de-fra-01` |
| `country_code` | ISO 3166-1 alpha-2 uppercase; must match Remnawave node metadata |
| `provider` | Provider name/account reference, redacted where needed |
| `provider_region` | Provider-native region/datacenter slug |
| `remnawave_node_uuid` | Redacted UUID evidence after node registration |
| `protocol_profiles` | Must use S1 allowlist from `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md` |
| `traffic_policy` | Customer traffic eligibility and abuse/P2P policy; finalized locally in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md` |
| `monitoring` | Health, uptime and provisioning smoke probes attached |
| `activation_status` | `planned`, `staging_proven`, `production_proven`, `visible`, `disabled` |

## Public Visibility Rules

| Rule | Reason |
|---|---|
| Show only regions that have live Remnawave nodes and passed smoke/evidence. | Prevents marketing from promising unavailable locations. |
| Do not show canary regions as available until production activation evidence exists. | `TR` and `KZ` carry higher provider/abuse/quality uncertainty. |
| Do not advertise city-level choices unless API supports city-level public regions. | Current API groups by country code. |
| Do not expose exact hostnames, IPs, Remnawave UUIDs or provider labels to customers. | Protects topology and reduces abuse targeting. |
| If region data is stale or unavailable, show degraded/unavailable state, not fake green status. | Matches public network snapshot freshness rules. |

## Provider Location Sanity Check

This document does not select a final VPS/provider for nodes. It only confirms that several selected S1 locations are common enough to be realistic:

- DigitalOcean documentation lists datacenters including New York, Amsterdam, Singapore, London, Frankfurt and Toronto: `https://docs.digitalocean.com/platform/regional-availability/`
- Hetzner documentation lists Cloud locations in Germany, Finland, USA and Singapore: `https://docs.hetzner.com/cloud/general/locations/`
- Vultr documentation exposes official region listing commands/API for datacenter regions and availability checks: `https://docs.vultr.com/reference/vultr-cli/regions`

Provider choice, price, abuse policy, VPN acceptability, DDoS posture and actual stock/availability still require real account evidence before activation.

## Cost-Control Position For S1

No server purchase is required to close this task. The current output is a planned catalogue and activation checklist.

Before spending money, CyberVPN should:

1. keep inactive regions hidden in public UI;
2. activate the smallest Tier A subset needed for beta proof;
3. add Tier B/C only after measured user demand or launch need;
4. delete unused test nodes immediately after evidence runs;
5. keep home-lab resources only for non-critical lab/evidence/device testing, never for customer VPN nodes or critical production path.
6. keep production VPN nodes node-only: no public app/API/admin probe relays, no unrelated exporters and no business/runtime services outside the VPN node stack.

## What This Closes

| Item | Status |
|---|---|
| `S1-VPN-010` 12 startup regions listed | Closed locally |
| Country-code aligned inventory | Closed locally |
| Public visibility rules for inactive/future regions | Closed locally |
| Node activation evidence template | Closed locally |
| Cost-control rule for not buying nodes yet | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Real staging node inventory | Requires staging Remnawave and provider/test nodes |
| Real production node inventory | Requires production Remnawave and paid/provider nodes |
| Provider account/location proof | Requires selected VPS/provider accounts and region availability checks |
| Node backup/fallback policy | Local inheritance rule covered in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`; real staging/prod backup/fallback evidence remains open |
| Public UI screenshot evidence | Requires deployed/staging UI with real live region data |
| Monitoring evidence per region | Requires observability stack and live probes |

## Local Verification Evidence

Documentation consistency commands:

```bash
git diff --check -- docs/cybervpn_stage1_launch_docs/00_INDEX.md docs/cybervpn_stage1_launch_docs/04_STAGE1_TECHNICAL_SPEC.md docs/cybervpn_stage1_launch_docs/06_STAGE1_IMPLEMENTATION_BACKLOG.md docs/cybervpn_stage1_launch_docs/11_STAGE1_REVIEW_CHECKLIST.md docs/cybervpn_stage1_launch_docs/21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md docs/cybervpn_stage1_launch_docs/77_STAGE1_REMAINING_WORK_TO_LAUNCH.md docs/cybervpn_stage1_launch_docs/85_STAGE1_VPN_009_USAGE_DISPLAY_EVIDENCE.md docs/cybervpn_stage1_launch_docs/86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md docs/cybervpn_stage1_launch_docs/CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md
rg -n "S1-VPN-010|Next ID to execute|Current next step|12 startup regions listed|86_STAGE1_VPN_010" docs/cybervpn_stage1_launch_docs
```

Observed result:

```text
git diff --check passed
S1-VPN-010 references point to this evidence file
Current next step is S1-OBS-004 after S1-OBS-003 local revalidation
Combined launch pack was regenerated from the current markdown documents
```

Security/documentation checks:

```bash
Run a targeted sensitive-value scan on this evidence file.
Run a dangerous-code pattern scan on this evidence file.
cd frontend && npm audit --omit=dev --audit-level=high
cd backend && uvx pip-audit --progress-spinner off
```

Observed result:

```text
No sensitive key material in the new S1-VPN-010 evidence file
No dangerous code patterns in the new S1-VPN-010 evidence file
npm audit: no high/critical findings; existing moderate PostCSS advisory remains through Next.js dependency path
pip-audit: No known vulnerabilities found
```

## Acceptance Result

`S1-VPN-010` is **completed locally** as the S1 node/region inventory contract.

Before S1 go-live, public copy and UI must only display regions with real Remnawave node evidence. The 12-region catalogue is the approved roadmap for beta coverage, not proof that all 12 regions are already live.

Next task after this evidence was `S1-VPN-011`, which is now closed locally in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`.
