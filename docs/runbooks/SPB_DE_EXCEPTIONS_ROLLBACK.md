# SPB DE Exceptions Rollback Runbook

This runbook covers the repository-side Task2 foundation for
`premium_spb_de_exceptions`: SPB customer ingress by default, Antifilter/vendor
exception prefixes through a dedicated DE bridge, and unmatched traffic direct
from SPB.

It does not authorize production mutation by itself. Production Remnawave API
writes, node restarts, firewall changes, DNS changes, or customer assignment
changes require an explicit rollout task and a secret-safe backup.

## Objects

Task2 Remnawave objects:

- product code: `premium_spb_de_exceptions`
- customer internal squad: `CYBERVPN_SPB_DE_NODES`
- external squad: `CYBERVPN_SPB_DE_EXCEPTIONS`
- bridge internal squad: `CYBERVPN_SPB_DE_BRIDGE`
- bridge service user: `CYBERVPN_SPB_DE_BRIDGE_USER`
- DE bridge inbound tag: `DE_SPB_EXCEPTIONS_BRIDGE_9444`
- SPB bridge outbound tag: `DE_EXCEPTIONS_BRIDGE`
- bridge port: `9444`
- bridge transport: SPB `2a01:e5c0:1368::3/128` -> DE
  `2a0b:4140:ba84::2:9444` over IPv6
- SPB customer inbounds (stable Remnawave tags retained for compatibility):
  - `SPB_EXCEPTIONS_REALITY_443` on dedicated IPv4 TCP `4443`
  - `SPB_EXCEPTIONS_XHTTP_REALITY_8443` on dedicated IPv4 TCP `8444`

The bridge is not a public customer Host. Customer subscriptions must only
contain SPB customer inbounds.

## Required Inputs

Use the operator only with an Antifilter artifact manifest produced by the
route pipeline. The operator expects:

- `schemaVersion: 1`
- `product: "premium_spb_de_exceptions"`
- `generatedAt` as a timezone-aware timestamp
- non-empty `union.prefixCount`
- `union.families.ipv4` and `union.families.ipv6`
- `union.sha256`
- `ipv6Policy.mode` as `disabled`, `fallback_block`, or `enabled`
- `artifacts.xrayRulesPath`
- `artifacts.xrayRulesSha256`
- an Xray rules artifact with non-empty `ip` match rules

The operator validates freshness, checksum, product, schema, path containment,
non-empty rule content, CIDR syntax, wildcard routes, and management/self
network exclusions before any write. `ipv6Policy.mode=enabled` is accepted only
when the artifact contains IPv6 prefixes.

## Dry Run

Dry-run is the default. It performs Remnawave reads and artifact validation
only:

```bash
REMNAWAVE_TOKEN="$REMNAWAVE_TOKEN" \
python scripts/remnawave/apply-spb-de-exceptions-server-routing.py \
  --remnawave-url "$REMNAWAVE_URL" \
  --artifact-manifest /path/to/artifacts/antifilter/manifest.json \
  --rollback-manifest /root/cybervpn-spb-de-exceptions-rollback.json
```

Expected dry-run evidence:

- mode is `dry-run`
- `bridgePort` is `9444`
- `bridgePortFree` is `true`
- `bridgePublicHost` is `none`
- `ipv6PolicyMode` matches the Antifilter manifest
- restart order is `["de", "spb"]`
- artifact manifest and rules checksums are present
- no rollback manifest is written
- no non-GET Remnawave calls occur

Abort if dry-run reports a port conflict, a public bridge Host, stale or
checksum-mismatched artifacts, a contaminated bridge user, or missing Task2
squads.

On a shared SPB node, duplicate address/port bindings remain forbidden. The
operator pins preserved Smart RU inbounds to IPv4 `443/8443` and Task2 clones
to dedicated IPv4 ports `4443/8444`. The Task2 customer squad and Task2 routing
rules contain only the two Task2 inbound tags. Preserved Smart RU inbounds must
never be added to Task2 routing: Host/squad visibility does not isolate Xray
routing by product.
The concrete addresses are still supplied through
`--spb-preserved-listen-address` (`SPB_PRESERVED_LISTEN_ADDRESS`) and
`--spb-task2-listen-address` (`SPB_TASK2_LISTEN_ADDRESS`); the operator rejects
wildcard or duplicate address/port pairs before mutation.

The reviewed production mapping is:

```text
Preserved Smart RU:     193.233.91.99:443/8443
Task2 dedicated IPv4:   193.233.91.99:4443/8444
Task2 connect address:  193.233.91.99 (literal IPv4 in generated profiles)
Task2 managed DNS alias: spb-exceptions.cyber-vpn.org (DNS-only A)
Task2 bridge source:    2a01:e5c0:1368::3/128 (not public customer DNS)
```

Before apply, prove that the bridge-source IPv6 is assigned persistently on
SPB, the public A record resolves exactly to the reviewed IPv4, dedicated TCP
ports `4443/8444` are free before activation and reachable after activation,
and the
existing `ru-spb-3.cyber-vpn.org` A-only Host still reaches
`193.233.91.99:443/8443`. Do not bypass the conflict check or reuse the existing
hostname for Task2.

## Pre-Apply Checks

Before an authorized apply:

1. Capture a Remnawave backup and the current SPB/DE profile JSON outside the
   repository.
2. Validate that `/root/cybervpn-spb-de-exceptions-rollback.json` or the chosen
   manifest path resolves outside the repository and `.codex`.
3. Run the port preflight on DE:

   ```bash
   systemctl start cybervpn-spb-de-exceptions-port-preflight.service
   ```

   This unit is deploy-only and has no `[Install]` section. Do not enable it
   and do not add it to Remnanode boot or restart dependencies. After the
   intended Xray/Remnanode bridge listener owns `9444`, this preflight is
   expected to fail and must not block ordinary restarts.

4. Render and check the peer-only firewall with Ansible check mode.
5. Confirm the firewall allows TCP and UDP `9444` only from
   `2a01:e5c0:1368::3/128`, the listener is pinned to
   `2a0b:4140:ba84::2`, and the deprecated IPv4 allow is absent.
6. Confirm no public Remnawave Host references `DE_SPB_EXCEPTIONS_BRIDGE_9444`.

## Apply Order

The operator applies in dependency-safe order:

1. Write rollback manifest before the first mutation.
2. Create or update the DE bridge Config Profile.
3. Create or update `CYBERVPN_SPB_DE_BRIDGE`.
4. Create or update `CYBERVPN_SPB_DE_BRIDGE_USER`.
5. Render the SPB customer profile with `DE_EXCEPTIONS_BRIDGE` and a
   non-conflicting Task2 listener design.
6. Create or update only the two Task2 public customer Hosts for RAW `4443` and
   XHTTP `8444`.
7. Attach only the two dedicated Task2 inbounds to the Task2 customer squad;
   never attach preserved Smart RU or bridge inbounds.
8. Switch and restart DE first.
9. Switch and restart SPB after the DE bridge is ready.

The rollback manifest records pre-change profiles, node profile assignments,
customer/external squad state, remapped shared SPB/DE Host state, Task2 SPB
Host state, bridge squad state, bridge user squad state, artifact checksums,
and phase checkpoints. It must remain outside the repository, must remain mode `0600`,
and must not be copied into tickets, logs, commits, or evidence bundles.
The profile and Host snapshots are intentionally not redacted because rollback
must restore the shared node configuration byte-equivalent to the pre-change
state where Remnawave returns it.

## Rollback Command

Use the same Remnawave URL and manifest path:

```bash
REMNAWAVE_TOKEN="$REMNAWAVE_TOKEN" \
python scripts/remnawave/apply-spb-de-exceptions-server-routing.py \
  --rollback \
  --remnawave-url "$REMNAWAVE_URL" \
  --rollback-manifest /root/cybervpn-spb-de-exceptions-rollback.json
```

Rollback order:

1. Restore the previous SPB node profile assignment.
2. Restore the previous customer internal squad and external squad headers.
3. Restore remapped shared SPB Host snapshots and restore or delete the two
   Task2 SPB public Hosts.
4. Restore or remove the SPB Task2 profile.
5. Restart SPB so customer traffic no longer points at the Task2 bridge.
6. Restore or remove the bridge user and bridge squad.
7. Restore the previous DE node profile assignment.
8. Restore remapped shared DE Host snapshots.
9. Restore or remove the DE bridge profile.
10. Restart DE.
11. Mark the manifest phase as `rolled_back`.

Rollback is idempotent. Re-running against a `rolled_back` manifest should not
create new objects.

## Route Semantics

Matched exception traffic:

```text
SPB customer inbound -> exception rule -> DE_EXCEPTIONS_BRIDGE
```

If the DE bridge is unavailable, matched traffic must fail closed. It must not
fall through to SPB `DIRECT`.

IPv6 policy:

- `disabled` and `fallback_block` insert a scoped `::/0 -> BLOCK` rule before
  artifact exception rules and set SPB profile DNS `queryStrategy` to
  `UseIPv4`.
- `enabled` requires a non-empty IPv6 artifact and does not insert the fallback
  `::/0` block.
- There is no implicit IPv6 DIRECT fallback when the IPv6 feed is not proven.

Unmatched traffic:

```text
SPB customer inbound -> final scoped tcp,udp DIRECT
```

The final DIRECT rule and every Task2 block/exception rule must remain exactly
scoped to the two dedicated Task2 inbound tags. Preserved Smart RU tags are a
cross-product routing leak and must fail review:

```json
{
  "type": "field",
  "inboundTag": [
    "SPB_EXCEPTIONS_REALITY_443",
    "SPB_EXCEPTIONS_XHTTP_REALITY_8443"
  ],
  "network": "tcp,udp",
  "outboundTag": "DIRECT"
}
```

Domain destinations require `routing.domainStrategy=IPOnDemand` and a
non-empty built-in DNS server list. For disabled/fallback IPv6 mode the operator
uses Xray server-side local DoH (`https+local://1.1.1.1/dns-query` and
`https+local://8.8.8.8/dns-query`), which bypasses the routing table but sends
DNS metadata to those reviewed third-party resolvers. `IPIfNonMatch` is insufficient here because
the final scoped `DIRECT` rule matches during the first pass and prevents the
second IP-matching pass. This follows the Xray routing and built-in DNS
contracts documented at <https://xtls.github.io/en/config/routing> and
<https://xtls.github.io/en/config/dns>.

The dedicated Task2 XHTTP inbound and generated Remnawave Host must use one
synchronized path. The operator derives the path from the preserved XHTTP
source profile during cloning rather than imposing a fixed production value.
The current production path is `/s1-xhttp-9fec0898`; any mismatch between Host
and listener causes HTTP `404` before VLESS traffic is established.

## Production Data-Plane Evidence (2026-07-12)

The production rollout established the following outcomes with an isolated
temporary Remnawave canary. No subscription URL, UUID, bridge credential, or
private config is stored in repository evidence.

| Path | Unmatched destination | Antifilter matched domain | Matched literal IP | UDP DNS to matched `8.8.8.8:53` |
|---|---|---|---|---|
| RAW Reality `4443` | SPB `193.233.91.99` | DE `138.124.115.206` | DE `138.124.115.206` | pass |
| XHTTP Reality `8444` | SPB `193.233.91.99` | DE `138.124.115.206` | DE `138.124.115.206` | pass |

The bridge itself returned DE egress `138.124.115.206` from SPB over the
IPv6-only peer path. A temporary firewall failure test blocked only
SPB -> DE `9444`: matched traffic timed out, while unmatched traffic continued
through SPB. The diagnostic rule was removed immediately after the check.

The prior IPv4 bridge path is intentionally disabled. Packet captures proved
that its TCP three-way handshake completed but every client payload packet was
lost before DE, including control payloads sent to DE ports `22`, `443`, and
`9444`. The equivalent IPv6 path transferred bidirectional payload and passed
the complete bridge test.

Customer subscriptions and Mihomo templates must not expose a `DIRECT` proxy
choice. The template may reference Remnawave-injected SPB proxies, but all
customer proxy traffic must enter through the SPB public Hosts.

## Evidence Boundaries

Safe evidence:

- operator mode, status, object action summaries, and phase names
- artifact SHA-256 values
- profile checksums
- route rule tags
- bridge health status
- sanitized Remnawave object names and tags

Never store in the repository, commit, ticket, chat, log, or evidence bundle:

- Remnawave tokens
- bridge passwords
- VLESS UUID values
- Reality private keys
- subscription URLs
- customer PII
- rollback manifest contents
- raw production route feeds if the rollout policy keeps them out of Git

## Failure Handling

If apply fails after the rollback manifest is written, the operator attempts
automatic rollback and records:

- `failurePhase`
- `failureClass`
- a safe `failureReason` only for runtime validation errors

If automatic rollback fails, stop further mutation and preserve the manifest,
candidate artifact, and Remnawave backup outside the repository for manual
operator recovery.

## Post-Rollback Checks

After rollback:

1. Dry-run the operator again and confirm it plans the same create/update work
   as before the failed apply.
2. Confirm no public Host references `DE_SPB_EXCEPTIONS_BRIDGE_9444`.
3. Confirm the Task2 customer squad has exactly the two dedicated IPv4
   RAW/XHTTP inbounds on `4443/8444`, and has no preserved Smart RU, bridge or
   DE customer inbound.
4. Confirm SPB customer traffic is no longer assigned to the Task2 profile.
5. Confirm DE port `9444` is closed or still peer-only according to the chosen
   rollback mode.
6. Record checksums and timestamps without secrets.
