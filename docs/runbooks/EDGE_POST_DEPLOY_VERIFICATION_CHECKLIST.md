# Edge Post-Deploy Verification Checklist

Use this checklist after any staging or production edge rollout.

## Preconditions

1. Generate or refresh the inventory snapshot:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-staging
```

2. Ensure the relevant vault files are present and decrypted for the operator session.

3. Keep rollout execution manual. Do not auto-apply Terraform or auto-run Ansible after merge.

## Staging rollout order

1. Bootstrap host baseline if the node is new:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase2-staging
```

2. Roll out Remnawave if that node carries the Remnawave workload:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase3-staging
```

Immediately after the rollout, run the focused Remnawave smoke checklist:

- `/home/beep/projects/VPNBussiness/docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md`

Operator shortcut:

```bash
cd /home/beep/projects/VPNBussiness/infra
make remnawave-staging-smoke
```

3. Roll out Helix if that node carries the Helix workload:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase4-staging
```

4. Roll out Alloy telemetry on all edge nodes:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase5-staging
```

## Health evidence

1. On the host, confirm Alloy metrics answer locally:

```bash
curl -fsS http://127.0.0.1:9100/metrics | grep alloy_build_info
```

2. In Prometheus, confirm the edge target is up:

```bash
curl -fsS http://localhost:9094/api/v1/query --data-urlencode 'query=up{job="alloy-edge"}'
```

3. In Loki or Grafana Explore, confirm new logs arrive with labels:

```text
{job="alloy-edge", environment="staging"}
```

4. Open the Grafana dashboards:
   - `CyberVPN Edge Observability`
   - `CyberVPN Helix`
   - `Logs Overview`

5. Keep the generated inventory snapshot and Prometheus target snapshot as operator artifacts.

## Rollback points

1. Remnawave rollback:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-remnawave-rollback-staging
```

2. Helix rollback:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-helix-rollback-staging
```

3. Alloy rollback:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-alloy-rollback-staging
```

## Close-out

1. Record the deployed commit SHA, image tags, inventory snapshot artifact, and Prometheus target artifact.
2. Record the Grafana dashboard screenshots or query evidence for the rollout window.
3. Only widen the rollout after the canary host is healthy and log flow is visible.
