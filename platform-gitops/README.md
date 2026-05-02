# platform-gitops

This directory mirrors the canonical GitOps repository shape for the initial
control-plane workload migration.

Current committed scope:

- `apps/nonprod-hetzner-hel1-core/platform-workloads`
- `clusters/nonprod-hetzner-hel1-core`

The rollout order is explicit and frozen:

1. namespace
2. backend
3. task-worker
4. task-scheduler
