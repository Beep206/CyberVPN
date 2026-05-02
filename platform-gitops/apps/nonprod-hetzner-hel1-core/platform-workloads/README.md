# platform-workloads

Cluster:

- `nonprod-hetzner-hel1-core`

Namespace:

- `platform-apps`

Frozen releases:

- `cybervpn-backend`
- `cybervpn-task-worker`
- `cybervpn-task-scheduler`

The scheduler intentionally reuses the `cybervpn-task-worker` chart and the
same OpenBao extract key while applying a different runtime command.
