# Remnawave Upgrade Guardrails

This runbook defines the non-negotiable checks for any future Remnawave upgrade in this repository.

## Current baseline

- panel/backend image: `remnawave/backend:2.7.4`
- edge node image: `remnawave/node:2.7.4`
- vendored SDK snapshot: `SDK/python-sdk-production` version `2.7.4`
- canonical internal contract: `backend/src/infrastructure/remnawave/contracts.py`

## Non-negotiable rules

1. Upgrade panel/backend and edge node together on the same `2.7.x` compatibility line.
2. Do not introduce new raw Remnawave calls outside `backend/src/infrastructure/remnawave/client.py`.
3. Do not use the vendored SDK as a runtime source of truth; it is reference material and contract-test input only.
4. Validate Remnawave webhooks with `X-Remnawave-Signature` and `X-Remnawave-Timestamp` using `REMNAWAVE_WEBHOOK_SECRET`.
5. Keep `Helix` outside Remnawave `Node Plugins`; plugins are optional node-local helpers only.
6. Update high-signal docs in the same change set as any Remnawave version change.

## Mandatory change set for an upgrade

1. Update image pins:
   - `infra/docker-compose.yml`
   - `infra/ansible/inventories/*/group_vars/remnawave_edge_*/main.yml`
   - `infra/ansible/roles/remnawave_edge/defaults/main.yml`
2. Refresh the vendored SDK snapshot under `SDK/python-sdk-production/`.
3. Review and, if needed, extend `backend/src/infrastructure/remnawave/contracts.py`.
4. Re-run webhook compatibility checks if upstream headers or signing semantics changed.
5. Update operator docs and smoke runbooks before rollout.

## Required verification

### Contract and backend checks

```bash
cd /home/beep/projects/VPNBussiness/backend
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  --no-cov \
  tests/contract/remnawave/test_vendored_sdk_contracts.py \
  tests/contract/remnawave/test_repo_docs_alignment.py \
  tests/integration/api/v1/webhooks/test_remnawave_webhook.py \
  tests/integration/api/v1/monitoring/test_monitoring_ops.py
```

### Consumer guardrails

```bash
cd /home/beep/projects/VPNBussiness
bash scripts/check-generated-artifacts.sh
```

The generated-artifact check must finish clean and keep these files unchanged:

- `backend/docs/api/openapi.json`
- `frontend/src/lib/api/generated/types.ts`
- `frontend/src/i18n/messages/generated`

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/unit/test_remnawave_normalizers.py \
  tests/test_services.py \
  tests/test_analytics.py \
  tests/test_monitoring.py \
  tests/test_subscriptions.py \
  tests/test_sync.py \
  tests/test_payments.py
```

```bash
cd /home/beep/projects/VPNBussiness/services/helix-adapter
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test remnawave::client::tests::node_inventory_item_accepts_current_remnawave_shape -- --nocapture
cargo test remnawave::client::tests::list_nodes_response_accepts_wrapped_payloads -- --nocapture
cargo test node_registry_inventory_helper_accepts_current_remnawave_fixture -- --nocapture
cargo test --locked
```

### Staging rollout and smoke

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase3-staging
make remnawave-staging-smoke
```

### Drift scan

```bash
cd /home/beep/projects/VPNBussiness
rg -n "2\\.4\\.4|2\\.6\\.1|v2\\.4\\.4\\+|Remnawave SDK: 2\\.4\\.4" \
  docs/PROJECT_OVERVIEW.md \
  docs/CYBERVPN_FULL_DESCRIPTION.md \
  docs/menu-frontend/USER_MENU_STRUCTURE.md \
  docs/menu-frontend/user_menu_structure.md \
  SDK/python-sdk-production/README.md
```

The drift scan must return no matches.

## Exit criteria

- version pins are aligned on the intended baseline
- vendored SDK version matches the intended baseline
- contract tests are green
- webhook tests are green
- consumer guardrails are green
- staging rollout and smoke are green
- high-signal docs do not reference stale Remnawave versions
- Helix architecture docs still state that `Helix` does not move into Remnawave `Node Plugins`
