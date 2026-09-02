# Supported Environment Matrix

Verta `v0.1` supports the following environment shapes for release closure and operator use.
This matrix is intentionally narrow.

| Environment | Deployment Label | Kind | Support Status | Upstream Contract | Configuration Source | Evidence Source |
| --- | --- | --- | --- | --- | --- | --- |
| Local supported staging | `remnawave-local-docker` | `local_supported_staging` | verified deployment shape; 3.4.1 live recheck pending | `Remnawave 3.4.1` numeric-ID contract; explicit `2.8` rollback profile | `infra/docker-compose.yml`, `infra/caddy/Caddyfile` | retained `Phase I` / `Phase M` deployment evidence plus automated 3.4.1 adapter contract tests |
| Operator-managed staging | `control-plane-staging` | `operator_managed_staging` | documented; rollout pending | `Remnawave 3.4.1` numeric-ID contract; explicit `2.8` rollback profile | `infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml` | sustained verification gates and operator runbooks |
| Operator-managed production | `control-plane-production` | `operator_managed_production` | documented; not deployed by this change | `Remnawave 3.4.1` numeric-ID contract; explicit `2.8` rollback profile | `infra/ansible/inventories/production/group_vars/control_plane_production/main.yml` | sustained verification gates and operator runbooks |

## Notes

- The `remnawave-local-docker` deployment shape has retained closure evidence, but this change does **not** claim a live Remnawave `3.4.1` upstream pass. The new adapter path has deterministic contract/fixture coverage only until the staging lane is run.
- Staging and production operator-managed shapes are supported only within the documented Ansible-managed control-plane model and the maintained non-fork Remnawave boundary.
- `target-3.4.1` is the default adapter profile and uses numeric user IDs. `legacy-2.8-rollback` is opt-in, retains UUID identity only while rollback is active, and is never selected by automatic fallback.
- `0-RTT` remains disabled in all supported environments.
- Machine-readable evidence now defaults to canonical `target/verta/` paths, with legacy `target/verta/` mirrors preserved for compatibility.
