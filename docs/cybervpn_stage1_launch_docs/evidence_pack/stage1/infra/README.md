# Infrastructure Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Production topology | `../../../120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md` |
| Staging environment contract | `../../../121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md` |
| Production environment deployability contract | `../../../122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md` |
| DNS/TLS contract | `../../../123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md` |
| Protected ingress contract | `../../../124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` |
| Local Docker/Compose | `../../../23_STAGE1_INFRA_009_LOCAL_DOCKER_COMPOSE_EVIDENCE.md` |
| Secrets inventory/policy | `../../../26_STAGE1_INFRA_006_SECRETS_INVENTORY_AND_POLICY.md` |
| Secrets scan | `../../../27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md` |
| Edge WAF/rate-limit baseline | `../../../119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md` |
| Home lab boundary | `../../../20_HOME_LAB_NON_CRITICAL_OPTION.md` |

## Required Before Go-Live

- Staging environment health evidence.
- Production deployment/health evidence based on `../../../122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`.
- DNS/TLS/redirect/admin-protection evidence based on `../../../123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`.
- Protected admin/backend ingress evidence based on `../../../124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`.
- Managed PostgreSQL private access, backup and restore evidence.
- Private Valkey/Redis memory policy and monitoring evidence.
- Separate staging/production Remnawave health and provisioning evidence.
- Live edge WAF/rate-limit/security-event evidence.

Current status: local topology, staging, production deployability, DNS/TLS, protected ingress and baseline contracts are enough for continued implementation, not staging/production clearance.
