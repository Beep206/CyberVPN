# Control-Plane Workload Charts

Canonical OCI Helm charts for the first Kubernetes control-plane workload set:

- `cybervpn-backend`
- `cybervpn-task-worker`

`task-scheduler` is intentionally a second release of the `cybervpn-task-worker`
chart family and uses `values-scheduler.yaml` plus a dedicated `HelmRelease`.

These charts follow the frozen Phase `P2.5/P2.8` contracts:

- runtime secrets arrive through `ExternalSecret`
- backend runs a pre-install / pre-upgrade migration hook
- Prometheus scraping is enabled through `ServiceMonitor`
- workload images are pinned by digest in GitOps
