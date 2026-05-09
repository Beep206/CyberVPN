> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-05
> Backlog ID: `S1-VPN-011`
> Статус: local torrent/P2P/TOR node traffic policy completed; real staging/prod plugin evidence remains required.

# S1-VPN-011 Torrent, P2P And TOR Node Policy Evidence

## Purpose

`S1-VPN-011` closes the local documentation/evidence part of the Stage 1 node traffic policy.

The S1 rule is deliberately conservative: CyberVPN must not promise that Torrent, P2P or TOR traffic is available everywhere. Public copy, support answers and UI must be bounded by actual node/provider/plugin evidence.

## Current Remnawave Plugin Finding

Official Remnawave documentation currently documents these node plugins:

- `Torrent Blocker`
- `Ingress Filter`
- `Egress Filter`
- `Connection Drop`
- `Shared Lists`
- `Executor` for temporary block/unblock/reset operations

The current official Remnawave docs do not show a dedicated native `TOR Blocker` plugin/addon. Therefore S1 must treat TOR control as a conditional custom node policy using available primitives, not as a proven Remnawave-native TOR addon.

If Remnawave later adds a dedicated TOR addon/plugin, it must not be silently enabled. It needs a separate evidence task covering docs, config shape, staging/prod smoke, support copy, legal/abuse posture, rollback and alerts.

## Repository Contract Observed

CyberVPN already has a backend node-plugin facade aligned with the Remnawave plugin surface:

```text
backend/src/presentation/api/v1/node_plugins/routes.py
backend/src/presentation/api/v1/node_plugins/schemas.py
backend/docs/api/openapi.json
frontend/src/lib/api/generated/types.ts
admin/src/features/infrastructure/components/node-plugins-console.tsx
docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md
```

The backend schema exposes:

| Field | Purpose |
|---|---|
| `torrentBlocker.enabled` | Enables/disables Torrent Blocker |
| `torrentBlocker.blockDuration` | Temporary source-IP block duration in seconds |
| `torrentBlocker.ignoreLists.ip` | Explicit IP ignore list; CIDR is not supported by Torrent Blocker ignore list |
| `torrentBlocker.ignoreLists.userId` | Explicit user ignore list |
| `torrentBlocker.includeRuleTags` | Optional additional routing rule tags that Torrent Blocker reports can process |
| `ingressFilter.blockedIps` | Inbound IP/CIDR blocking |
| `egressFilter.blockedIps` | Outbound destination IP/CIDR blocking |
| `egressFilter.blockedPorts` | Outbound destination port blocking |
| `sharedLists` | Reusable IP/CIDR lists for plugin policies |
| `connectionDrop.whitelistIps` | Whitelist for connection drop behavior |

The current admin surface also has a node plugins console, but S1 still requires deployed admin persona evidence before relying on it operationally.

## S1 Customer-Facing Policy

| Category | S1 public posture | Operational rule |
|---|---|---|
| Torrent/P2P | Do not promise availability. | Restricted by default on live S1 nodes unless a node is explicitly approved as P2P-allowed. |
| TOR | Do not promise TOR-specific support or blocking. | Off by default as a named feature. If a provider requires TOR control, use approved egress/shared-list/custom-routing evidence before enabling that node. |
| SMTP/spam ports | Do not market as a user feature. | Block or restrict abusive outbound mail ports where provider policy or abuse risk requires it. |
| Public proxies/exit nodes | Prohibited by AUP. | Support/admin may suspend or revoke access after evidence and escalation. |
| Region availability | Only live proven regions may be shown. | Inactive or canary regions stay hidden until plugin/monitoring/provider evidence exists. |

## S1 Node Policy Matrix

This matrix applies to the 12-region catalogue from `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`.

| S1 region ID | Country | Launch posture | Torrent/P2P policy | TOR policy | SMTP/abuse-port policy |
|---|---|---|---|---|---|
| `s1-de-fra` | `DE` | Primary | Restricted by default; enable Torrent Blocker when prerequisites pass | No native TOR plugin; egress/shared-list only if required | Block at least `25`; consider `465`, `587` if provider/support approves |
| `s1-nl-ams` | `NL` | Primary | Restricted by default; provider P2P allowance does not equal public promise | Same as above | Same as above |
| `s1-fi-hel` | `FI` | Primary | Restricted by default | Same as above | Same as above |
| `s1-pl-waw` | `PL` | Primary | Restricted by default | Same as above | Same as above |
| `s1-gb-lon` | `GB` | Secondary | Restricted by default | Same as above | Same as above |
| `s1-fr-par` | `FR` | Secondary | Restricted by default | Same as above | Same as above |
| `s1-us-nyc` | `US` | Secondary | Restricted by default; higher complaint/DMCA sensitivity | Same as above | Same as above |
| `s1-ca-tor` | `CA` | Secondary | Restricted by default | Same as above | Same as above |
| `s1-sg-sin` | `SG` | Primary | Restricted by default; high abuse sensitivity | Same as above | Same as above |
| `s1-jp-tyo` | `JP` | Secondary | Restricted by default | Same as above | Same as above |
| `s1-tr-ist` | `TR` | Canary | Restricted by default; do not show until provider/plugin evidence | Same as above; no public TOR claim | Same as above |
| `s1-kz-ala` | `KZ` | Canary | Restricted by default; do not show until provider/plugin evidence | Same as above; no public TOR claim | Same as above |

## Torrent Blocker Enablement Contract

Torrent Blocker can be used as a node-local abuse control, not as a perfect technical guarantee.

Minimum S1 prerequisites per node:

| Requirement | S1 rule |
|---|---|
| Remnawave version | Panel and Node must be on a plugin-capable 2.7.x+ line proven in staging/prod evidence |
| Xray-core | Must meet the Torrent Blocker minimum required by Remnawave docs |
| Linux/node host | Kernel and `nftables` prerequisites must be proven |
| Container capability | Remnawave Node must include `cap_add: NET_ADMIN` where plugins are enabled |
| Inbound sniffing | `sniffing.enabled=true` with `destOverride` covering `http`, `tls`, `quic` for the relevant inbound |
| Config ownership | Plugin config must be applied through Remnawave/approved backend/admin path, not hand-edited ad hoc on production nodes |
| Block duration | S1 default: `3600` seconds unless support/ops records a different provider requirement |
| Reports | `/api/v1/node-plugins/torrent-blocker/reports` and `/stats` must work for admin/support evidence |
| Webhooks | `torrent_blocker.report` must be signature-verified and routed to support/ops if used for enforcement |
| Support action | Remnawave report alone does not automatically mean account termination; S1 uses manual review unless immediate harm requires pause/suspension |

Recommended S1 plugin config shape:

```json
{
  "torrentBlocker": {
    "enabled": true,
    "ignoreLists": {
      "ip": [],
      "userId": []
    },
    "blockDuration": 3600,
    "includeRuleTags": ["TORRENT_BY_DOMAIN", "TORRENT_BY_PORT"]
  }
}
```

`includeRuleTags` is optional and must reference only tested routing rules. Do not add rule tags that silently affect non-torrent traffic unless a separate evidence task approves that behavior.

## TOR Control Contract

No dedicated Remnawave-native TOR blocker was found in the official Remnawave node-plugin docs. For S1, TOR control is therefore **planned but disabled by default**.

Allowed S1 design if a provider or abuse case requires TOR control:

| Mechanism | Status | Rule |
|---|---|---|
| Dedicated Remnawave TOR addon | Not found in current official docs | Do not rely on it until upstream docs/API evidence exists |
| `egressFilter.blockedIps` | Allowed with evidence | May block destination IP/CIDR lists such as approved TOR exit/relay feeds |
| `egressFilter.blockedPorts` | Allowed with evidence | May block known TOR-related ports where this does not break ordinary traffic; partial only |
| `sharedLists` | Allowed with evidence | Use only maintained, timestamped, source-approved lists; record update cadence and rollback |
| Xray custom routing to `blackhole` | Allowed with evidence | Use only in a tested Config Profile; route order must be proven because routing is order-sensitive |
| Torrent Blocker `includeRuleTags` for TOR | Not approved for S1 | Do not overload Torrent Blocker for TOR unless upstream docs explicitly support it and staging proof exists |

TOR control limitations:

1. Blocking TOR exit lists alone does not fully block a user from connecting to the TOR network.
2. TOR bridges and obfuscation can use ordinary ports such as `443`.
3. IP lists can become stale quickly.
4. False positives can break ordinary sites or privacy tools.
5. S1 must describe this as partial abuse control, not complete TOR prevention.

Recommended future config placeholder, disabled until evidence:

```json
{
  "sharedLists": [
    {
      "name": "ext:tor-exits",
      "type": "ipList",
      "items": []
    }
  ],
  "egressFilter": {
    "enabled": false,
    "blockedIps": ["ext:tor-exits"],
    "blockedPorts": []
  }
}
```

## Backup/Fallback Node Rule

Backup/fallback nodes must inherit the same or stricter traffic policy as the node they replace.

| Scenario | Required behavior |
|---|---|
| Primary node with Torrent Blocker fails over to backup | Backup must already have equivalent plugin policy before traffic is shifted |
| Backup lacks plugin evidence | Keep backup hidden or mark as operational emergency only; do not advertise normal availability |
| Canary node becomes production-visible | Must pass the same plugin, monitoring, abuse and support evidence as primary nodes |
| Plugin breaks traffic | Disable affected node or plugin through approved rollback, then update support/status wording |

## Public Copy And Support Rules

| Surface | S1 rule |
|---|---|
| Marketing/pricing | No "torrent allowed", "P2P supported everywhere", "TOR supported", "TOR blocked" or "unlimited unrestricted traffic" claims |
| AUP | Keep bounded wording from `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md` |
| Support templates | Explain that Torrent/P2P/TOR behavior depends on node/provider policy and beta evidence |
| Admin/support | Show plugin reports only to authorized roles; redact raw source/destination values when not required |
| Status page | Mention region/node impairment, not sensitive detection details |

## Evidence Required Before Enabling On Staging/Production

| Evidence | Required before |
|---|---|
| Remnawave `/api/v1/node-plugins/` facade returns valid JSON | Any plugin-dependent staging rollout |
| `torrentBlocker.enabled=true` visible in redacted plugin config | Claiming Torrent Blocker is active on a node |
| Test report or controlled synthetic event reaches reports/stats | Operational reliance on reports |
| `torrent_blocker.report` webhook signature validation passes | Automated alert/support escalation |
| Admin node plugin console/persona proof | Support/admin operational use |
| Alert delivery to Telegram/email | Treating reports as monitored |
| Rollback command/procedure | Production enablement |
| Provider accepts this traffic policy | Making node customer-visible |
| TOR list provenance/update cadence if TOR control enabled | Any TOR-specific enforcement claim |

## Source Notes

Official Remnawave sources checked on 2026-05-05:

- Node Plugins docs: `https://docs.rw/docs/learn/node-plugins/`
- Remnawave webhooks docs: `https://docs.rw/docs/features/webhooks/`
- Server-side routing docs: `https://docs.rw/docs/learn-en/server-routing/`

TOR list source candidates for future work:

- Tor bulk exit list exporter: `https://check.torproject.org/api/bulk`
- Tor Metrics CollecTor exit-list documentation: `https://metrics.torproject.org/collector.html`

These TOR sources are not integrated in S1. They are listed only so a future TOR-control task has a clear source-evidence path.

## What This Closes

| Item | Status |
|---|---|
| `S1-VPN-011` Torrent/P2P public posture | Closed locally |
| `S1-VPN-011` Remnawave Torrent Blocker policy | Closed locally |
| `S1-VPN-011` TOR addon finding | Closed locally: no dedicated native TOR plugin found in official docs |
| `S1-VPN-011` TOR future-control placeholder | Closed locally |
| `S1-VPN-011` backup/fallback node inheritance rule | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Real staging Torrent Blocker proof | Requires staging Remnawave/node with plugin prerequisites |
| Real production Torrent Blocker proof | Requires production Remnawave/node and provider-approved policy |
| TOR control implementation | Disabled by default; requires separate provider need, list provenance, config, smoke and rollback evidence |
| Admin support screenshots | Requires deployed admin and persona proof |
| Alert/webhook evidence | Requires Remnawave webhook setup and alert delivery proof |
| Provider-specific P2P/TOR acceptance | Requires selected node provider accounts and policy review |

## Local Verification Evidence

Documentation consistency commands:

```bash
rg -n "S1-VPN-011|torrent|P2P|TOR|Tor|torrentBlocker|egressFilter" docs backend/src frontend/src admin/src
git diff --check -- docs/cybervpn_stage1_launch_docs/00_INDEX.md docs/cybervpn_stage1_launch_docs/04_STAGE1_TECHNICAL_SPEC.md docs/cybervpn_stage1_launch_docs/06_STAGE1_IMPLEMENTATION_BACKLOG.md docs/cybervpn_stage1_launch_docs/10_STAGE1_RISK_REGISTER.md docs/cybervpn_stage1_launch_docs/11_STAGE1_REVIEW_CHECKLIST.md docs/cybervpn_stage1_launch_docs/19_STAGE1_TECH_DEBT_REGISTER.md docs/cybervpn_stage1_launch_docs/21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md docs/cybervpn_stage1_launch_docs/77_STAGE1_REMAINING_WORK_TO_LAUNCH.md docs/cybervpn_stage1_launch_docs/86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md docs/cybervpn_stage1_launch_docs/87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md docs/cybervpn_stage1_launch_docs/CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md
```

Observed result:

```text
Existing backend/admin plugin facade found
S1-VPN-011 references point to this evidence file
git diff --check passed
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
No sensitive key material in the new S1-VPN-011 evidence file
No dangerous code patterns in the new S1-VPN-011 evidence file
npm audit: no high/critical findings; existing moderate PostCSS advisory remains through Next.js dependency path
pip-audit: No known vulnerabilities found
```

## Acceptance Result

`S1-VPN-011` is **completed locally** as the S1 torrent/P2P/TOR node traffic policy.

Before go-live, every live node must either have matching staging/prod plugin/provider evidence or remain hidden from public availability claims.

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ID: `S1-FE-002` - dashboard states for active/trial/grace/expired/payment/provisioning.
