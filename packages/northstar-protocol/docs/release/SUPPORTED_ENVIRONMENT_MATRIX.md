# Supported Environment Matrix

Northstar `v0.1` supports the following environment shapes for release closure and operator use.
This matrix is intentionally narrow.

| Environment | Deployment Label | Kind | Support Status | Upstream Contract | Configuration Source | Evidence Source |
| --- | --- | --- | --- | --- | --- | --- |
| Local supported staging | `remnawave-local-docker` | `local_supported_staging` | verified | `Remnawave 2.7.x` non-fork path | `infra/docker-compose.yml`, `infra/caddy/Caddyfile` | `Phase I` and `Phase M` ready summaries |
| Operator-managed staging | `control-plane-staging` | `operator_managed_staging` | documented | `Remnawave 2.7.x` non-fork path | `infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml` | sustained verification gates and operator runbooks |
| Operator-managed production | `control-plane-production` | `operator_managed_production` | documented | `Remnawave 2.7.x` non-fork path | `infra/ansible/inventories/production/group_vars/control_plane_production/main.yml` | sustained verification gates and operator runbooks |

## Notes

- The only fully re-verified closure environment in this repository is `remnawave-local-docker`.
- Staging and production operator-managed shapes are supported only within the documented Ansible-managed control-plane model and the maintained non-fork Remnawave boundary.
- `0-RTT` remains disabled in all supported environments.
