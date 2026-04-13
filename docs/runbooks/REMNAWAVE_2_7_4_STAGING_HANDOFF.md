# Remnawave 2.7.4 Staging Rollout Handoff

This runbook is the operator handoff for Phase 1 of the Remnawave integration hardening work.

Use it when executing the staging Remnawave edge upgrade from `2.6.1` to `2.7.4`.

## Scope

- upgrade staged Remnawave edge nodes to `remnawave/node:2.7.4`
- verify the rollout through the existing Ansible verify playbook
- run the focused Remnawave smoke against staging
- collect evidence and define the rollback boundary

## Preflight

1. Confirm the rollout window and the canary host(s) for `remnawave_edge_staging`.
2. Confirm the pinned edge version is `2.7.4` in:
   - `infra/ansible/inventories/staging/group_vars/remnawave_edge_staging/main.yml`
   - `infra/ansible/roles/remnawave_edge/defaults/main.yml`
3. Confirm staging secrets are present:
   - Remnawave node secret key in the vaulted `remnawave_edge_staging` vars
   - staging admin credentials for backend login
   - disposable smoke user credentials
4. Ensure operator tooling is available:
   - `ansible-playbook`
   - `jq`
   - `curl`
5. If Terraform inventory is the source of truth, verify the state is current before rollout.

## Execution

Run the staged rollout and the built-in verify step:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase3-staging
```

If you need the explicit sequence instead of the composite target:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-staging
make ansible-remnawave-rollout-staging
make ansible-remnawave-verify-staging
```

## Smoke

Export the staging smoke variables:

```bash
export REMNAWAVE_BASE_URL="https://<staging-remnawave-host>"
export REMNAWAVE_API_TOKEN="<staging-remnawave-api-token>"
export API_BASE_URL="https://<staging-backend-host>/api/v1"
export EXPECTED_NODE_NAME="<staging-node-name>"

export ADMIN_LOGIN="<staging-admin-login-or-email>"
export ADMIN_PASSWORD="<staging-admin-password>"

export SMOKE_USER_LOGIN="<disposable-staging-user-login-or-email>"
export SMOKE_USER_PASSWORD="<disposable-staging-user-password>"

# Optional. Use only for a disposable user because this changes state.
# export SMOKE_ALLOW_CANCEL=true
```

Run the focused smoke:

```bash
cd /home/beep/projects/VPNBussiness/infra
make remnawave-staging-smoke
```

The smoke covers:

- node registration through `/api/nodes`
- backend admin login
- `/api/v1/monitoring/health`
- `/api/v1/monitoring/stats`
- `/api/v1/node-plugins/`
- disposable user login
- `/api/v1/subscriptions/active`
- optional `/api/v1/subscriptions/cancel`

## Success Criteria

The rollout can be considered successful only if all of the following are true:

- the Ansible verify play completes without host failures
- the expected node is present in Remnawave and `isConnected == true`
- backend monitoring health reports healthy for database, redis, and remnawave
- backend monitoring stats show non-zero server inventory
- the node plugins facade returns valid JSON
- subscription read path works for the disposable smoke user
- subscription cancel works when explicitly enabled for the disposable smoke user

## Evidence

Capture and attach:

- rollout timestamp and operator name
- target hostnames
- deployed image tag `remnawave/node:2.7.4`
- `make ansible-phase3-staging` output or task summary
- `make ansible-remnawave-verify-staging` output or task summary
- smoke output for every step
- `/api/nodes` evidence for the expected node

## Rollback Boundary

Roll back immediately if any of the following occurs:

- node disappears from `/api/nodes`
- node remains disconnected after rollout settle time
- monitoring health reports Remnawave as unhealthy
- plugin facade starts failing after the upgrade
- subscription read path regresses

Rollback command:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-remnawave-rollback-staging
```

After rollback, rerun the smoke and capture rollback evidence before closing the window.
