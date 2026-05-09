# VPN / Remnawave Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Local Docker/Compose stack | `../../../23_STAGE1_INFRA_009_LOCAL_DOCKER_COMPOSE_EVIDENCE.md` |
| Local Remnawave API smoke | `../../../24_STAGE1_VPN_012_LOCAL_REMNAWAVE_SMOKE_EVIDENCE.md` |
| Local connected node smoke | `../../../25_STAGE1_VPN_012_LOCAL_REMNAWAVE_NODE_EVIDENCE.md` |
| S1 protocol list | `../../../39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md` |
| Trial provisioning contract | `../../../40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md` |
| Paid provisioning contract | `../../../41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md` |
| Provisioning retry contract | `../../../42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md` |
| Credential regeneration | `../../../43_STAGE1_VPN_008_CREDENTIAL_REGENERATION_EVIDENCE.md` |
| Expiry/grace disable | `../../../44_STAGE1_VPN_007_EXPIRY_GRACE_DISABLE_EVIDENCE.md` |
| Grace period product behavior | `../../../98_STAGE1_PROD_005_GRACE_PERIOD_BEHAVIOR_EVIDENCE.md` |
| Usage display | `../../../85_STAGE1_VPN_009_USAGE_DISPLAY_EVIDENCE.md` |
| Node/region inventory | `../../../86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md` |
| Torrent/P2P/TOR node policy | `../../../87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md` |

## Required Before Go-Live

- Separate staging Remnawave health/API evidence.
- Dedicated production Remnawave health/API evidence.
- Real node/provider evidence for every public region shown as live.
- Staging/prod trial provisioning evidence.
- Staging/prod paid provisioning evidence.
- Remnawave outage/retry evidence with durable worker state.
- Real VPN client connection proof from issued QR/subscription URL/config.
- Remnawave backup/export/rebuild evidence.
- Torrent Blocker or any TOR-control evidence before enabling those controls.

Current status: local/dev proof exists; staging/prod VPN readiness remains a hard go-live blocker.
