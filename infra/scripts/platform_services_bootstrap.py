#!/usr/bin/env python3
"""Render the P2.2 platform-services GitOps scaffold for the first non-prod workload cluster."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme(*, workload_cluster_name: str, management_cluster_name: str, openbao_server: str) -> str:
    return f"""# P2.2 platform-services scaffold

This scaffold freezes the first non-prod workload-cluster platform-services baseline for CyberVPN.

Cluster ids:

- management cluster: `{management_cluster_name}`
- workload cluster: `{workload_cluster_name}`

Control-surface decisions frozen here:

- `Flux` remains the reconciler and Git remains the desired-state source;
- `P2.2` deploys cluster base services through `Flux`, not through ad hoc `kubectl apply`;
- there is **no** separate ingress-controller chart in this scaffold because `Cilium Gateway API` is the in-cluster ingress substrate already frozen in `P2.1`;
- the current implementation uses `External Secrets Operator` for the `OpenBao -> operator -> Kubernetes Secret` flow;
- the archived `openbao-secrets-operator` is intentionally not used;
- `cert-manager` authenticates to OpenBao over the JWT auth mount via the cert-manager `vault.auth.kubernetes` configuration path;
- `trust-manager` is installed now, and trust distribution uses the current `Bundle` API with an explicit note that upstream is evolving toward `ClusterBundle`;
- observability baseline is:
  - `kube-prometheus-stack`
  - `Loki` monolithic for non-prod
  - `Tempo` monolithic for non-prod
  - `Alloy` DaemonSet for node or pod collection
  - `Alloy` Deployment for OTLP gateway traffic

OpenBao integration assumptions frozen by this scaffold:

- OpenBao server placeholder: `{openbao_server}`
- OpenBao namespace: `platform`
- workload-cluster JWT auth mount: `jwt-k8s-{workload_cluster_name}`
- shared KV mount: `kv-shared`
- application KV mount: `kv-apps`

Important boundaries:

- this scaffold does not claim the workload cluster or its platform services already exist;
- it does not bypass the `platform-gitops` boundary frozen in `P1.6`;
- secret **values** are never committed here;
- this scaffold freezes the repo surface, reconciliation ordering, and baseline manifests only.
"""


def render_cluster_readme(*, workload_cluster_name: str) -> str:
    return f"""# {workload_cluster_name}

This directory is the cluster-local Flux entrypoint for the `{workload_cluster_name}` workload cluster.

Rules:

- `kustomization.yaml` registers only Flux `Kustomization` objects for ordered reconciliation;
- no manual `kubectl apply` history is a source-of-truth replacement for files under this path;
- cluster-local `Flux` ordering exists so controller CRDs and follow-up custom resources are not forced into one unsafe apply wave;
- no standalone ingress-controller chart is introduced here because `Cilium Gateway API` is already the canonical ingress substrate.
"""


def render_platform_services_readme(*, workload_cluster_name: str) -> str:
    return f"""# platform-services/{workload_cluster_name}

This path contains the frozen `P2.2` base platform-services scaffold for `{workload_cluster_name}`.

Directory purpose:

- `sources/`
  - Flux source objects for OCI and Helm chart retrieval
- `namespaces/`
  - required namespaces and base labels
- `cert-manager/`
  - `cert-manager` HelmRelease only
- `external-secrets/`
  - `External Secrets Operator` HelmRelease only
- `openbao-integration/`
  - service accounts, RBAC, `ClusterSecretStore`, `ExternalSecret`, and `ClusterIssuer`
- `trust-manager/`
  - `trust-manager` HelmRelease only
- `trust-bundles/`
  - current `Bundle` resources for trust distribution
- `kube-prometheus-stack/`
  - Prometheus, Alertmanager, and Grafana baseline
- `observability-backends/`
  - `Loki` and `Tempo`
- `alloy/`
  - `Alloy` DaemonSet and OTLP gateway Deployment

Implementation note:

- this scaffold chooses `External Secrets Operator` because the upstream `openbao-secrets-operator` repository is archived and read-only as of February 2026;
- the architecture boundary stays the same: `OpenBao -> operator -> Kubernetes Secret`;
- `P2.2` intentionally avoids a separate ingress-controller chart and builds on the already frozen `Cilium Gateway API` substrate from `P2.1`.
"""


def render_cluster_kustomization() -> str:
    return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - platform-sources.yaml
  - platform-namespaces.yaml
  - platform-cert-manager.yaml
  - platform-external-secrets.yaml
  - platform-openbao-integration.yaml
  - platform-trust-manager.yaml
  - platform-trust-bundles.yaml
  - platform-kube-prometheus-stack.yaml
  - platform-observability-backends.yaml
  - platform-alloy.yaml
"""


def render_flux_kustomization(*, name: str, path: str, depends_on: list[str] | None = None) -> str:
    depends_block = ""
    if depends_on:
        items = "\n".join(f"    - name: {dependency}" for dependency in depends_on)
        depends_block = f"  dependsOn:\n{items}\n"

    return (
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 10m\n"
        "  prune: true\n"
        "  wait: true\n"
        "  timeout: 10m\n"
        f"{depends_block}"
        "  sourceRef:\n"
        "    kind: GitRepository\n"
        "    name: flux-system\n"
        f"  path: {path}\n"
    )


def render_sources_kustomization() -> str:
    return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - cert-manager-chart.yaml
  - trust-manager-chart.yaml
  - external-secrets-repository.yaml
  - kube-prometheus-stack-chart.yaml
  - loki-chart.yaml
  - tempo-chart.yaml
  - alloy-repository.yaml
"""


def render_ocirepository(*, name: str, url: str, tag: str) -> str:
    return (
        "apiVersion: source.toolkit.fluxcd.io/v1\n"
        "kind: OCIRepository\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 30m\n"
        f"  url: {url}\n"
        "  ref:\n"
        f"    tag: {tag}\n"
    )


def render_helmrepository(*, name: str, url: str) -> str:
    return (
        "apiVersion: source.toolkit.fluxcd.io/v1\n"
        "kind: HelmRepository\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 30m\n"
        f"  url: {url}\n"
    )


def render_namespace_objects() -> str:
    return """apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
  labels:
    cybervpn.io/platform-service: cert-manager
    cybervpn.io/trust-bundle: "enabled"
---
apiVersion: v1
kind: Namespace
metadata:
  name: external-secrets
  labels:
    cybervpn.io/platform-service: external-secrets
---
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    cybervpn.io/platform-service: kube-prometheus-stack
    cybervpn.io/trust-bundle: "enabled"
---
apiVersion: v1
kind: Namespace
metadata:
  name: observability
  labels:
    cybervpn.io/platform-service: observability
    cybervpn.io/trust-bundle: "enabled"
"""


def render_simple_kustomization(*, resources: list[str]) -> str:
    rendered_resources = "\n".join(f"  - {resource}" for resource in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
{rendered_resources}
"""


def render_cert_manager_helmrelease(*, cert_manager_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cert-manager
  namespace: cert-manager
spec:
  interval: 30m
  chartRef:
    kind: OCIRepository
    name: cert-manager-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    crds:
      enabled: true
    prometheus:
      enabled: true
    global:
      leaderElection:
        namespace: cert-manager
    webhook:
      timeoutSeconds: 4
# upstream chart tag pinned from cert-manager OCI docs and release metadata
# version: {cert_manager_version}
"""


def render_external_secrets_helmrelease(*, external_secrets_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: external-secrets
  namespace: external-secrets
spec:
  interval: 30m
  chart:
    spec:
      chart: external-secrets
      version: "{external_secrets_version}"
      sourceRef:
        kind: HelmRepository
        name: external-secrets
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    installCRDs: true
    serviceMonitor:
      enabled: true
"""


def render_eso_jwt_rbac() -> str:
    return """apiVersion: v1
kind: ServiceAccount
metadata:
  name: openbao-jwt
  namespace: external-secrets
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: openbao-jwt
  namespace: external-secrets
rules:
  - apiGroups: [""]
    resources: ["serviceaccounts/token"]
    resourceNames: ["openbao-jwt"]
    verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: openbao-jwt
  namespace: external-secrets
subjects:
  - kind: ServiceAccount
    name: external-secrets
    namespace: external-secrets
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: openbao-jwt
"""


def render_cert_manager_jwt_rbac() -> str:
    return """apiVersion: v1
kind: ServiceAccount
metadata:
  name: openbao-issuer
  namespace: cert-manager
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: openbao-issuer
  namespace: cert-manager
rules:
  - apiGroups: [""]
    resources: ["serviceaccounts/token"]
    resourceNames: ["openbao-issuer"]
    verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: openbao-issuer
  namespace: cert-manager
subjects:
  - kind: ServiceAccount
    name: cert-manager
    namespace: cert-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: openbao-issuer
"""


def render_clustersecretstore_openbao_shared(*, workload_cluster_name: str, openbao_server: str) -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: openbao-shared
spec:
  provider:
    vault:
      server: "{openbao_server}"
      namespace: "platform"
      path: "kv-shared"
      version: "v2"
      auth:
        jwt:
          path: "jwt-k8s-{workload_cluster_name}"
          role: "k8s-{workload_cluster_name}-external-secrets-openbao-jwt"
          kubernetesServiceAccountToken:
            serviceAccountRef:
              name: "openbao-jwt"
              namespace: "external-secrets"
            audiences:
              - openbao
            expirationSeconds: 600
  conditions:
    - namespaces:
        - cert-manager
        - monitoring
        - observability
        - platform-system
"""


def render_clustersecretstore_openbao_apps(*, workload_cluster_name: str, openbao_server: str) -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: openbao-apps
spec:
  provider:
    vault:
      server: "{openbao_server}"
      namespace: "platform"
      path: "kv-apps"
      version: "v2"
      auth:
        jwt:
          path: "jwt-k8s-{workload_cluster_name}"
          role: "k8s-{workload_cluster_name}-external-secrets-openbao-jwt"
          kubernetesServiceAccountToken:
            serviceAccountRef:
              name: "openbao-jwt"
              namespace: "external-secrets"
            audiences:
              - openbao
            expirationSeconds: 600
"""


def render_external_secret_openbao_server_ca() -> str:
    return """apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: openbao-server-ca
  namespace: cert-manager
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: openbao-shared
    kind: ClusterSecretStore
  target:
    name: openbao-server-ca
    creationPolicy: Owner
  data:
    - secretKey: ca.crt
      remoteRef:
        key: pki/openbao-server
        property: ca.crt
"""


def render_external_secret_openbao_k8s_ca() -> str:
    return """apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: openbao-k8s-ca
  namespace: cert-manager
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: openbao-shared
    kind: ClusterSecretStore
  target:
    name: openbao-k8s-ca
    creationPolicy: Owner
  data:
    - secretKey: ca.crt
      remoteRef:
        key: pki/k8s-internal-ca
        property: ca.crt
"""


def render_clusterissuer_openbao_internal(*, workload_cluster_name: str, openbao_server: str) -> str:
    return f"""apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: openbao-k8s-internal
spec:
  vault:
    server: "{openbao_server}"
    namespace: "platform"
    path: "pki-k8s/sign/k8s-{workload_cluster_name}-cert-manager"
    caBundleSecretRef:
      name: openbao-server-ca
      key: ca.crt
    auth:
      kubernetes:
        mountPath: /v1/auth/jwt-k8s-{workload_cluster_name}
        role: "k8s-{workload_cluster_name}-cert-manager-openbao-issuer"
        serviceAccountRef:
          name: openbao-issuer
"""


def render_trust_manager_helmrelease(*, trust_manager_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: trust-manager
  namespace: cert-manager
spec:
  interval: 30m
  dependsOn:
    - name: cert-manager
      namespace: cert-manager
  chartRef:
    kind: OCIRepository
    name: trust-manager-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    secretTargets:
      enabled: false
    app:
      trust:
        namespace: cert-manager
# upstream release tag pinned from trust-manager release metadata
# version: {trust_manager_version}
"""


def render_bundle_openbao_k8s_ca() -> str:
    return """apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: openbao-k8s-internal-ca
spec:
  sources:
    - secret:
        name: openbao-k8s-ca
        key: ca.crt
  target:
    configMap:
      key: ca.crt
    namespaceSelector:
      matchLabels:
        cybervpn.io/trust-bundle: "enabled"
"""


def render_kube_prometheus_stack_helmrelease(*, kube_prometheus_stack_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: kube-prometheus-stack
  namespace: monitoring
spec:
  interval: 30m
  chartRef:
    kind: OCIRepository
    name: kube-prometheus-stack-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    grafana:
      enabled: true
      persistence:
        enabled: false
    alertmanager:
      enabled: true
    prometheus:
      prometheusSpec:
        retention: 15d
        podMonitorSelectorNilUsesHelmValues: false
        serviceMonitorSelectorNilUsesHelmValues: false
        scrapeConfigSelectorNilUsesHelmValues: false
# upstream chart tag pinned from OCI package metadata
# version: {kube_prometheus_stack_version}
"""


def render_loki_helmrelease(*, loki_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: loki
  namespace: observability
spec:
  interval: 30m
  dependsOn:
    - name: kube-prometheus-stack
      namespace: monitoring
  chartRef:
    kind: OCIRepository
    name: loki-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    deploymentMode: SingleBinary
    singleBinary:
      replicas: 1
      persistence:
        enabled: false
    monitoring:
      serviceMonitor:
        enabled: true
# upstream chart tag pinned from OCI package metadata
# version: {loki_version}
"""


def render_tempo_helmrelease(*, tempo_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: tempo
  namespace: observability
spec:
  interval: 30m
  dependsOn:
    - name: kube-prometheus-stack
      namespace: monitoring
  chartRef:
    kind: OCIRepository
    name: tempo-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    serviceMonitor:
      enabled: true
    persistence:
      enabled: false
# upstream chart tag pinned from OCI package metadata
# version: {tempo_version}
"""


def render_alloy_daemonset_helmrelease(*, alloy_chart_version: str, alloy_image_tag: str, loki_url: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: alloy-daemonset
  namespace: observability
spec:
  interval: 30m
  dependsOn:
    - name: kube-prometheus-stack
      namespace: monitoring
    - name: observability-backends
      namespace: flux-system
  chart:
    spec:
      chart: alloy
      version: "{alloy_chart_version}"
      sourceRef:
        kind: HelmRepository
        name: alloy-repository
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    crds:
      create: true
    serviceMonitor:
      enabled: true
    image:
      tag: "{alloy_image_tag}"
    alloy:
      enableReporting: false
      extraPorts: []
      mounts:
        varlog: true
        dockercontainers: true
      configMap:
        create: true
        content: |
          logging {{
            level  = "info"
            format = "logfmt"
          }}

          discovery.kubernetes "pods" {{
            role = "pod"
          }}

          loki.source.kubernetes "pods" {{
            targets    = discovery.kubernetes.pods.targets
            forward_to = [loki.process.enrich.receiver]
          }}

          loki.process "enrich" {{
            stage.static_labels {{
              values = {{
                job         = "alloy-kubernetes"
                environment = "nonprod"
                cluster     = "nonprod-hetzner-hel1-core"
              }}
            }}

            forward_to = [loki.write.default.receiver]
          }}

          loki.write "default" {{
            endpoint {{
              url = "{loki_url}"
            }}
          }}
    controller:
      type: daemonset
    configReloader:
      enabled: true
# upstream chart version pinned from grafana/alloy Helm chart metadata
# version: {alloy_chart_version}
"""


def render_alloy_otlp_gateway_helmrelease(*, alloy_chart_version: str, alloy_image_tag: str, loki_url: str, tempo_endpoint: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: alloy-otlp-gateway
  namespace: observability
spec:
  interval: 30m
  dependsOn:
    - name: kube-prometheus-stack
      namespace: monitoring
    - name: observability-backends
      namespace: flux-system
  chart:
    spec:
      chart: alloy
      version: "{alloy_chart_version}"
      sourceRef:
        kind: HelmRepository
        name: alloy-repository
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    crds:
      create: true
    image:
      tag: "{alloy_image_tag}"
    alloy:
      enableReporting: false
      extraPorts:
        - name: otlp-grpc
          port: 4317
          targetPort: 4317
          protocol: TCP
        - name: otlp-http
          port: 4318
          targetPort: 4318
          protocol: TCP
      configMap:
        create: true
        content: |
          logging {{
            level  = "info"
            format = "logfmt"
          }}

          otelcol.receiver.otlp "ingest" {{
            grpc {{
              endpoint = "0.0.0.0:4317"
            }}

            http {{
              endpoint = "0.0.0.0:4318"
            }}

            output {{
              traces = [otelcol.processor.batch.default.input]
            }}
          }}

          otelcol.processor.batch "default" {{
            output {{
              traces = [otelcol.exporter.otlp.tempo.input]
            }}
          }}

          otelcol.exporter.otlp "tempo" {{
            client {{
              endpoint = "{tempo_endpoint}"
              tls {{
                insecure = true
              }}
            }}
          }}

          loki.write "default" {{
            endpoint {{
              url = "{loki_url}"
            }}
          }}
    serviceMonitor:
      enabled: true
    controller:
      type: deployment
      replicas: 2
    configReloader:
      enabled: true
# upstream chart version pinned from grafana/alloy Helm chart metadata
# version: {alloy_chart_version}
"""


def render_versions_env(
    *,
    management_cluster_name: str,
    workload_cluster_name: str,
    openbao_server: str,
    cert_manager_version: str,
    trust_manager_version: str,
    external_secrets_version: str,
    kube_prometheus_stack_version: str,
    loki_version: str,
    tempo_version: str,
    alloy_chart_version: str,
    alloy_image_tag: str,
) -> str:
    return (
        f"MANAGEMENT_CLUSTER_ID={management_cluster_name}\n"
        f"WORKLOAD_CLUSTER_ID={workload_cluster_name}\n"
        f"OPENBAO_SERVER={openbao_server}\n"
        f"OPENBAO_NAMESPACE=platform\n"
        f"OPENBAO_JWT_MOUNT=jwt-k8s-{workload_cluster_name}\n"
        "OPENBAO_SHARED_STORE=openbao-shared\n"
        "OPENBAO_APPS_STORE=openbao-apps\n"
        "CERT_MANAGER_ISSUER=openbao-k8s-internal\n"
        f"CERT_MANAGER_CHART_TAG={cert_manager_version}\n"
        f"TRUST_MANAGER_CHART_TAG={trust_manager_version}\n"
        f"EXTERNAL_SECRETS_CHART_VERSION={external_secrets_version}\n"
        f"KUBE_PROMETHEUS_STACK_CHART_TAG={kube_prometheus_stack_version}\n"
        f"LOKI_CHART_TAG={loki_version}\n"
        f"TEMPO_CHART_TAG={tempo_version}\n"
        f"ALLOY_CHART_VERSION={alloy_chart_version}\n"
        f"ALLOY_IMAGE_TAG={alloy_image_tag}\n"
        "INGRESS_CONTROLLER=none-cilium-gateway-api-is-the-substrate\n"
    )


def render_check_script(*, workload_cluster_name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

flux get kustomizations -A
kubectl get helmreleases.helm.toolkit.fluxcd.io -A
kubectl get pods -n cert-manager
kubectl get pods -n external-secrets
kubectl get pods -n monitoring
kubectl get pods -n observability
kubectl get clustersecretstores.external-secrets.io
kubectl get externalsecrets.external-secrets.io -A
kubectl get clusterissuers.cert-manager.io
kubectl get bundles.trust.cert-manager.io

echo "P2.2 platform-services checks completed for {workload_cluster_name}."
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    cluster_dir = output_dir / "clusters" / args.workload_cluster_name
    platform_services_dir = output_dir / "infrastructure" / args.workload_cluster_name / "platform-services"

    write_text(
        output_dir / "README.md",
        render_root_readme(
            workload_cluster_name=args.workload_cluster_name,
            management_cluster_name=args.management_cluster_name,
            openbao_server=args.openbao_server,
        ),
        mode=0o644,
    )
    write_text(cluster_dir / "README.md", render_cluster_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(cluster_dir / "kustomization.yaml", render_cluster_kustomization(), mode=0o644)

    cluster_kustomizations = {
        "platform-sources.yaml": render_flux_kustomization(
            name="platform-sources",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/sources",
        ),
        "platform-namespaces.yaml": render_flux_kustomization(
            name="platform-namespaces",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/namespaces",
        ),
        "platform-cert-manager.yaml": render_flux_kustomization(
            name="platform-cert-manager",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/cert-manager",
            depends_on=["platform-sources", "platform-namespaces"],
        ),
        "platform-external-secrets.yaml": render_flux_kustomization(
            name="platform-external-secrets",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/external-secrets",
            depends_on=["platform-sources", "platform-namespaces"],
        ),
        "platform-openbao-integration.yaml": render_flux_kustomization(
            name="platform-openbao-integration",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/openbao-integration",
            depends_on=["platform-cert-manager", "platform-external-secrets"],
        ),
        "platform-trust-manager.yaml": render_flux_kustomization(
            name="platform-trust-manager",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/trust-manager",
            depends_on=["platform-sources", "platform-namespaces", "platform-cert-manager"],
        ),
        "platform-trust-bundles.yaml": render_flux_kustomization(
            name="platform-trust-bundles",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/trust-bundles",
            depends_on=["platform-trust-manager", "platform-openbao-integration"],
        ),
        "platform-kube-prometheus-stack.yaml": render_flux_kustomization(
            name="platform-kube-prometheus-stack",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/kube-prometheus-stack",
            depends_on=["platform-sources", "platform-namespaces"],
        ),
        "platform-observability-backends.yaml": render_flux_kustomization(
            name="platform-observability-backends",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/observability-backends",
            depends_on=["platform-kube-prometheus-stack", "platform-sources", "platform-namespaces"],
        ),
        "platform-alloy.yaml": render_flux_kustomization(
            name="platform-alloy",
            path=f"./infrastructure/{args.workload_cluster_name}/platform-services/alloy",
            depends_on=["platform-kube-prometheus-stack", "platform-observability-backends", "platform-sources", "platform-namespaces"],
        ),
    }

    for file_name, content in cluster_kustomizations.items():
        write_text(cluster_dir / file_name, content, mode=0o644)

    write_text(platform_services_dir / "README.md", render_platform_services_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(
        platform_services_dir / "versions.env",
        render_versions_env(
            management_cluster_name=args.management_cluster_name,
            workload_cluster_name=args.workload_cluster_name,
            openbao_server=args.openbao_server,
            cert_manager_version=args.cert_manager_version,
            trust_manager_version=args.trust_manager_version,
            external_secrets_version=args.external_secrets_version,
            kube_prometheus_stack_version=args.kube_prometheus_stack_version,
            loki_version=args.loki_version,
            tempo_version=args.tempo_version,
            alloy_chart_version=args.alloy_chart_version,
            alloy_image_tag=args.alloy_image_tag,
        ),
        mode=0o644,
    )
    write_text(output_dir / "scripts" / "check-platform-services.sh", render_check_script(workload_cluster_name=args.workload_cluster_name), mode=0o750)

    write_text(platform_services_dir / "sources" / "kustomization.yaml", render_sources_kustomization(), mode=0o644)
    write_text(
        platform_services_dir / "sources" / "cert-manager-chart.yaml",
        render_ocirepository(
            name="cert-manager-chart",
            url="oci://quay.io/jetstack/charts/cert-manager",
            tag=args.cert_manager_version,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "trust-manager-chart.yaml",
        render_ocirepository(
            name="trust-manager-chart",
            url="oci://quay.io/jetstack/charts/trust-manager",
            tag=args.trust_manager_version,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "external-secrets-repository.yaml",
        render_helmrepository(name="external-secrets", url="https://charts.external-secrets.io"),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "kube-prometheus-stack-chart.yaml",
        render_ocirepository(
            name="kube-prometheus-stack-chart",
            url="oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack",
            tag=args.kube_prometheus_stack_version,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "loki-chart.yaml",
        render_ocirepository(
            name="loki-chart",
            url="oci://ghcr.io/grafana/helm-charts/loki",
            tag=args.loki_version,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "tempo-chart.yaml",
        render_ocirepository(
            name="tempo-chart",
            url="oci://ghcr.io/grafana/helm-charts/tempo",
            tag=args.tempo_version,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "sources" / "alloy-repository.yaml",
        render_helmrepository(name="alloy-repository", url="https://grafana.github.io/helm-charts"),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "namespaces" / "kustomization.yaml",
        render_simple_kustomization(resources=["namespaces.yaml"]),
        mode=0o644,
    )
    write_text(platform_services_dir / "namespaces" / "namespaces.yaml", render_namespace_objects(), mode=0o644)

    write_text(
        platform_services_dir / "cert-manager" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "cert-manager" / "helmrelease.yaml",
        render_cert_manager_helmrelease(cert_manager_version=args.cert_manager_version),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "external-secrets" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "external-secrets" / "helmrelease.yaml",
        render_external_secrets_helmrelease(external_secrets_version=args.external_secrets_version),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "openbao-integration" / "kustomization.yaml",
        render_simple_kustomization(
            resources=[
                "eso-jwt-rbac.yaml",
                "cert-manager-jwt-rbac.yaml",
                "clustersecretstore-openbao-shared.yaml",
                "clustersecretstore-openbao-apps.yaml",
                "externalsecret-openbao-server-ca.yaml",
                "externalsecret-openbao-k8s-ca.yaml",
                "clusterissuer-openbao-internal.yaml",
            ]
        ),
        mode=0o644,
    )
    write_text(platform_services_dir / "openbao-integration" / "eso-jwt-rbac.yaml", render_eso_jwt_rbac(), mode=0o644)
    write_text(platform_services_dir / "openbao-integration" / "cert-manager-jwt-rbac.yaml", render_cert_manager_jwt_rbac(), mode=0o644)
    write_text(
        platform_services_dir / "openbao-integration" / "clustersecretstore-openbao-shared.yaml",
        render_clustersecretstore_openbao_shared(
            workload_cluster_name=args.workload_cluster_name,
            openbao_server=args.openbao_server,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "openbao-integration" / "clustersecretstore-openbao-apps.yaml",
        render_clustersecretstore_openbao_apps(
            workload_cluster_name=args.workload_cluster_name,
            openbao_server=args.openbao_server,
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "openbao-integration" / "externalsecret-openbao-server-ca.yaml",
        render_external_secret_openbao_server_ca(),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "openbao-integration" / "externalsecret-openbao-k8s-ca.yaml",
        render_external_secret_openbao_k8s_ca(),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "openbao-integration" / "clusterissuer-openbao-internal.yaml",
        render_clusterissuer_openbao_internal(
            workload_cluster_name=args.workload_cluster_name,
            openbao_server=args.openbao_server,
        ),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "trust-manager" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "trust-manager" / "helmrelease.yaml",
        render_trust_manager_helmrelease(trust_manager_version=args.trust_manager_version),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "trust-bundles" / "kustomization.yaml",
        render_simple_kustomization(resources=["bundle-openbao-k8s-ca.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "trust-bundles" / "bundle-openbao-k8s-ca.yaml",
        render_bundle_openbao_k8s_ca(),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "kube-prometheus-stack" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "kube-prometheus-stack" / "helmrelease.yaml",
        render_kube_prometheus_stack_helmrelease(kube_prometheus_stack_version=args.kube_prometheus_stack_version),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "observability-backends" / "kustomization.yaml",
        render_simple_kustomization(resources=["loki-helmrelease.yaml", "tempo-helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "observability-backends" / "loki-helmrelease.yaml",
        render_loki_helmrelease(loki_version=args.loki_version),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "observability-backends" / "tempo-helmrelease.yaml",
        render_tempo_helmrelease(tempo_version=args.tempo_version),
        mode=0o644,
    )

    write_text(
        platform_services_dir / "alloy" / "kustomization.yaml",
        render_simple_kustomization(resources=["daemonset-helmrelease.yaml", "otlp-gateway-helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "alloy" / "daemonset-helmrelease.yaml",
        render_alloy_daemonset_helmrelease(
            alloy_chart_version=args.alloy_chart_version,
            alloy_image_tag=args.alloy_image_tag,
            loki_url="http://loki.observability.svc.cluster.local:3100/loki/api/v1/push",
        ),
        mode=0o644,
    )
    write_text(
        platform_services_dir / "alloy" / "otlp-gateway-helmrelease.yaml",
        render_alloy_otlp_gateway_helmrelease(
            alloy_chart_version=args.alloy_chart_version,
            alloy_image_tag=args.alloy_image_tag,
            loki_url="http://loki.observability.svc.cluster.local:3100/loki/api/v1/push",
            tempo_endpoint="tempo.observability.svc.cluster.local:4317",
        ),
        mode=0o644,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the P2.2 platform-services scaffold.")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.add_argument("--management-cluster-name", default="nonprod-mgmt")
    render_scaffold.add_argument("--workload-cluster-name", default="nonprod-hetzner-hel1-core")
    render_scaffold.add_argument("--openbao-server", default="https://openbao-nonprod.example.internal:8200")
    render_scaffold.add_argument("--cert-manager-version", default="v1.20.2")
    render_scaffold.add_argument("--trust-manager-version", default="v0.15.0")
    render_scaffold.add_argument("--external-secrets-version", default="2.3.0")
    render_scaffold.add_argument("--kube-prometheus-stack-version", default="83.6.0")
    render_scaffold.add_argument("--loki-version", default="6.46.0")
    render_scaffold.add_argument("--tempo-version", default="1.24.4")
    render_scaffold.add_argument("--alloy-chart-version", default="1.7.0")
    render_scaffold.add_argument("--alloy-image-tag", default="v1.15.1")
    render_scaffold.set_defaults(func=command_render_scaffold)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
