#!/usr/bin/env python3
"""Render the P2.5 workload-delivery scaffold for monorepo release and platform-gitops app delivery."""

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


def render_root_readme(
    *,
    source_repo_name: str,
    source_repository_slug: str,
    gitops_repo_name: str,
    workload_cluster_name: str,
) -> str:
    return f"""# P2.5 workload-delivery scaffold

This scaffold freezes the first GitHub Actions -> OCI Helm -> GitOps PR -> Flux delivery baseline for CyberVPN.

Frozen repositories and cluster:

- source monorepo: `{source_repo_name}`
- source repository slug: `{source_repository_slug}`
- desired-state repository: `{gitops_repo_name}`
- first workload cluster: `{workload_cluster_name}`

Canonical decisions frozen here:

- first Kubernetes-managed first-party platform workloads are:
  - `backend`
  - `task-worker`
- `helix-adapter` is intentionally excluded from the first pair because it remains coupled to external fleet and runtime-adapter transition work;
- first-party workloads are packaged as OCI Helm charts and stored in `GHCR`;
- Flux consumes those charts through `OCIRepository` plus `HelmRelease`, not through GitRepository-packaged charts;
- release promotion mutates the GitOps repository by pull request, not by editing Ansible inventory manifests;
- the GitOps mutation updates both:
  - chart version pin
  - workload image digest pin
- workload runtime configuration continues to arrive through `ExternalSecret` plus `ClusterSecretStore`, not through `.env` files in Git.

Important boundaries:

- this scaffold does not claim a live registry, a live GitOps repository, or live workload-cluster access already exists;
- this scaffold does not publish charts or open real pull requests;
- secret values and registry credentials are intentionally out of scope for the repository slice.
"""


def render_source_repo_readme() -> str:
    return """# source-repo

This directory models the changes that belong in the application monorepo during `P2.5`.

It freezes:

- OCI Helm chart structure for the first application workloads;
- GitHub Actions workflow shape for:
  - image build and push
  - chart package and push
  - GitOps repository mutation by pull request;
- the rule that Ansible release-manifest mutation is no longer the target promotion model.

This scaffold is intentionally repo-only:

- no workflow secrets are embedded;
- no live registry or GitHub repo mutation occurs from this scaffold alone;
- the workflow remains a contract until real credentials and repositories exist.
"""


def render_gitops_repo_readme(*, workload_cluster_name: str) -> str:
    return f"""# platform-gitops

This directory models the changes that belong in the standalone GitOps repository during `P2.5`.

Frozen target:

- cluster: `{workload_cluster_name}`
- app-delivery path: `apps/{workload_cluster_name}/platform-workloads`
- workloads:
  - `backend`
  - `task-worker`

Source-of-truth boundary:

- this repository holds the pinned chart version and pinned image digest for first-party workloads;
- Flux remains the reconciler, not the source of truth;
- charts are fetched from `GHCR` through `OCIRepository`;
- workload runtime secrets are not committed here and are instead referenced through `ExternalSecret` resources created by the charts.
"""


def render_chart_readme() -> str:
    return """# charts

These charts are the first canonical OCI Helm chart contracts for Kubernetes-managed platform workloads.

Rules:

- chart version and workload image digest are promoted independently;
- chart defaults stay environment-agnostic where possible;
- environment-specific release values belong in the GitOps repository, not in these source charts;
- the charts must remain compatible with `External Secrets Operator` and the `OpenBao -> Kubernetes Secret` flow frozen in `P2.2`.
"""


def render_chart_yaml(*, chart_name: str, description: str) -> str:
    return f"""apiVersion: v2
name: {chart_name}
description: {description}
type: application
version: 0.1.0
appVersion: "0.1.0"
"""


def render_helpers_tpl() -> str:
    return """{{- define "cybervpn-workload.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "cybervpn-workload.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "cybervpn-workload.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-workload.labels" -}}
app.kubernetes.io/name: {{ include "cybervpn-workload.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "cybervpn-workload.secretName" -}}
{{- if .Values.externalSecret.targetName -}}
{{- .Values.externalSecret.targetName -}}
{{- else -}}
{{- printf "%s-runtime" (include "cybervpn-workload.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-workload.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "cybervpn-workload.fullname" . -}}
{{- end -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
"""


def render_serviceaccount_tpl() -> str:
    return """{{- if .Values.serviceAccount.create }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "cybervpn-workload.serviceAccountName" . }}
  labels:
    {{- include "cybervpn-workload.labels" . | nindent 4 }}
{{- end }}
"""


def render_externalsecret_tpl() -> str:
    return """{{- if .Values.externalSecret.enabled }}
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {{ include "cybervpn-workload.secretName" . }}
  labels:
    {{- include "cybervpn-workload.labels" . | nindent 4 }}
spec:
  refreshInterval: {{ .Values.externalSecret.refreshInterval | quote }}
  secretStoreRef:
    kind: {{ .Values.externalSecret.secretStoreRef.kind | quote }}
    name: {{ .Values.externalSecret.secretStoreRef.name | quote }}
  target:
    name: {{ include "cybervpn-workload.secretName" . }}
    creationPolicy: Owner
  dataFrom:
    - extract:
        key: {{ .Values.externalSecret.extractKey | quote }}
{{- end }}
"""


def render_backend_values(*, image_repository: str) -> str:
    return f"""replicaCount: 2

image:
  repository: {image_repository}
  tag: ""
  digest: sha256:REPLACE_ME_BACKEND_IMAGE_DIGEST
  pullPolicy: IfNotPresent

imagePullSecrets:
  - name: ghcr-platform-workloads

serviceAccount:
  create: true
  name: ""

externalSecret:
  enabled: true
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: openbao-apps
  targetName: backend-runtime
  extractKey: kv-apps/data/nonprod/platform/backend

service:
  enabled: true
  type: ClusterIP
  port: 8000
  targetPort: 8000

resources: {{}}
"""


def render_task_worker_values(*, image_repository: str) -> str:
    return f"""replicaCount: 1

image:
  repository: {image_repository}
  tag: ""
  digest: sha256:REPLACE_ME_TASK_WORKER_IMAGE_DIGEST
  pullPolicy: IfNotPresent

imagePullSecrets:
  - name: ghcr-platform-workloads

serviceAccount:
  create: true
  name: ""

externalSecret:
  enabled: true
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: openbao-apps
  targetName: task-worker-runtime
  extractKey: kv-apps/data/nonprod/platform/task-worker

resources: {{}}
"""


def render_backend_deployment_tpl() -> str:
    return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "cybervpn-workload.fullname" . }}
  labels:
    {{- include "cybervpn-workload.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-workload.name" . }}
  template:
    metadata:
      labels:
        {{- include "cybervpn-workload.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "cybervpn-workload.serviceAccountName" . }}
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ .name }}
        {{- end }}
      containers:
        - name: backend
          {{- if .Values.image.digest }}
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          {{- else }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          {{- end }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
          envFrom:
            - secretRef:
                name: {{ include "cybervpn-workload.secretName" . }}
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""


def render_backend_service_tpl() -> str:
    return """{{- if .Values.service.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "cybervpn-workload.fullname" . }}
  labels:
    {{- include "cybervpn-workload.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    app.kubernetes.io/name: {{ include "cybervpn-workload.name" . }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
{{- end }}
"""


def render_task_worker_deployment_tpl() -> str:
    return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "cybervpn-workload.fullname" . }}
  labels:
    {{- include "cybervpn-workload.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-workload.name" . }}
  template:
    metadata:
      labels:
        {{- include "cybervpn-workload.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "cybervpn-workload.serviceAccountName" . }}
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ .name }}
        {{- end }}
      containers:
        - name: task-worker
          {{- if .Values.image.digest }}
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          {{- else }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          {{- end }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          envFrom:
            - secretRef:
                name: {{ include "cybervpn-workload.secretName" . }}
          livenessProbe:
            exec:
              command:
                - python
                - healthcheck.py
            initialDelaySeconds: 20
            periodSeconds: 30
          readinessProbe:
            exec:
              command:
                - python
                - healthcheck.py
            initialDelaySeconds: 10
            periodSeconds: 30
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""


def render_workflow() -> str:
    return """name: Platform Workload Delivery

on:
  push:
    branches:
      - main
      - develop
    paths:
      - 'backend/**'
      - 'services/task-worker/**'
      - 'charts/**'
      - '.github/workflows/platform-workload-delivery.yml'
  workflow_dispatch:
    inputs:
      target_cluster:
        description: 'Target workload cluster path in platform-gitops'
        required: true
        default: nonprod-hetzner-hel1-core
        type: string
      gitops_repository:
        description: 'owner/name of the platform-gitops repository'
        required: true
        default: REPLACE_ME_OWNER/platform-gitops
        type: string
      gitops_base_ref:
        description: 'Base branch for the GitOps promotion PR'
        required: true
        default: main
        type: string

concurrency:
  group: platform-workload-delivery-${{ github.ref }}
  cancel-in-progress: false

permissions:
  contents: read
  packages: write

jobs:
  build-and-package:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        component:
          - name: backend
            image_name: backend
            context: backend
            dockerfile: backend/Dockerfile
            chart_dir: charts/cybervpn-backend
            chart_name: cybervpn-backend
            gitops_dir: backend
          - name: task-worker
            image_name: task-worker
            context: services/task-worker
            dockerfile: services/task-worker/Dockerfile
            chart_dir: charts/cybervpn-task-worker
            chart_name: cybervpn-task-worker
            gitops_dir: task-worker

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Normalize image repository path
        run: |
          echo "IMAGE_REPOSITORY=$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_ENV"

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: ${{ matrix.component.context }}
          file: ${{ matrix.component.dockerfile }}
          push: true
          provenance: mode=max
          sbom: true
          tags: |
            ghcr.io/${{ env.IMAGE_REPOSITORY }}/${{ matrix.component.image_name }}:sha-${{ github.sha }}
          cache-from: type=gha,scope=${{ matrix.component.image_name }}
          cache-to: type=gha,mode=max,scope=${{ matrix.component.image_name }}

      - name: Package and push OCI chart
        env:
          CHART_DIR: ${{ matrix.component.chart_dir }}
          CHART_NAME: ${{ matrix.component.chart_name }}
        run: |
          CHART_VERSION="0.1.0-git.${GITHUB_RUN_NUMBER}.${GITHUB_SHA::7}"
          mkdir -p out
          helm package "$CHART_DIR" \
            --destination out \
            --version "$CHART_VERSION" \
            --app-version "sha-${GITHUB_SHA}"
          helm push "out/${CHART_NAME}-${CHART_VERSION}.tgz" "oci://ghcr.io/${IMAGE_REPOSITORY}/charts"
          echo "CHART_VERSION=${CHART_VERSION}" >> "$GITHUB_ENV"

      - name: Write release manifest
        env:
          COMPONENT_NAME: ${{ matrix.component.name }}
          IMAGE_NAME: ${{ matrix.component.image_name }}
          DIGEST: ${{ steps.build.outputs.digest }}
          CHART_NAME: ${{ matrix.component.chart_name }}
          CHART_VERSION: ${{ env.CHART_VERSION }}
          GITOPS_DIR: ${{ matrix.component.gitops_dir }}
        run: |
          mkdir -p out
          python - <<'PY'
          import json
          import os
          from pathlib import Path

          payload = {
              "component": os.environ["COMPONENT_NAME"],
              "image_name": os.environ["IMAGE_NAME"],
              "image_repository": f"ghcr.io/{os.environ['GITHUB_REPOSITORY'].lower()}/{os.environ['IMAGE_NAME']}",
              "image_digest": os.environ["DIGEST"],
              "chart_name": os.environ["CHART_NAME"],
              "chart_version": os.environ["CHART_VERSION"],
              "chart_url": f"oci://ghcr.io/{os.environ['GITHUB_REPOSITORY'].lower()}/charts/{os.environ['CHART_NAME']}",
              "gitops_dir": os.environ["GITOPS_DIR"],
              "source_commit": os.environ["GITHUB_SHA"],
              "source_run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
          }
          Path("out").mkdir(parents=True, exist_ok=True)
          Path(f"out/{payload['component']}.json").write_text(
              json.dumps(payload, indent=2, sort_keys=True),
              encoding="utf-8",
          )
          PY

      - name: Upload release manifest
        uses: actions/upload-artifact@v4
        with:
          name: platform-workload-release-${{ matrix.component.name }}
          path: out/${{ matrix.component.name }}.json
          retention-days: 14

  promote-gitops:
    runs-on: ubuntu-latest
    needs: [build-and-package]
    env:
      GH_TOKEN: ${{ secrets.PLATFORM_GITOPS_TOKEN }}
      TARGET_CLUSTER: ${{ github.event.inputs.target_cluster }}
      GITOPS_REPOSITORY: ${{ github.event.inputs.gitops_repository }}
      GITOPS_BASE_REF: ${{ github.event.inputs.gitops_base_ref }}
    steps:
      - name: Download release manifests
        uses: actions/download-artifact@v4
        with:
          path: artifacts/releases

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install script dependency
        run: pip install pyyaml

      - name: Clone platform-gitops repository
        run: |
          TARGET_CLUSTER="${TARGET_CLUSTER:-nonprod-hetzner-hel1-core}"
          GITOPS_REPOSITORY="${GITOPS_REPOSITORY:-REPLACE_ME_OWNER/platform-gitops}"
          GITOPS_BASE_REF="${GITOPS_BASE_REF:-main}"
          echo "TARGET_CLUSTER=${TARGET_CLUSTER}" >> "$GITHUB_ENV"
          echo "GITOPS_REPOSITORY=${GITOPS_REPOSITORY}" >> "$GITHUB_ENV"
          echo "GITOPS_BASE_REF=${GITOPS_BASE_REF}" >> "$GITHUB_ENV"
          git clone "https://x-access-token:${GH_TOKEN}@github.com/${GITOPS_REPOSITORY}.git" platform-gitops
          cd platform-gitops
          git checkout "$GITOPS_BASE_REF"

      - name: Update platform-gitops release pins
        run: |
          python - <<'PY'
          import json
          from pathlib import Path
          import yaml

          manifests = sorted(Path("artifacts/releases").glob("**/*.json"))
          target_cluster = __import__("os").environ["TARGET_CLUSTER"]
          gitops_root = Path("platform-gitops") / "apps" / target_cluster / "platform-workloads"

          for manifest_path in manifests:
              payload = json.loads(manifest_path.read_text(encoding="utf-8"))
              component_dir = gitops_root / payload["gitops_dir"]
              oci_repo_path = component_dir / "ocirepository.yaml"
              helmrelease_path = component_dir / "helmrelease.yaml"

              oci_doc = yaml.safe_load(oci_repo_path.read_text(encoding="utf-8"))
              oci_doc["spec"]["ref"] = {"tag": payload["chart_version"]}
              oci_repo_path.write_text(yaml.safe_dump(oci_doc, sort_keys=False), encoding="utf-8")

              release_doc = yaml.safe_load(helmrelease_path.read_text(encoding="utf-8"))
              release_doc["spec"]["values"]["image"]["repository"] = payload["image_repository"]
              release_doc["spec"]["values"]["image"]["digest"] = payload["image_digest"]
              annotations = release_doc.setdefault("metadata", {}).setdefault("annotations", {})
              annotations["cybervpn.io/source-commit"] = payload["source_commit"]
              annotations["cybervpn.io/source-run-url"] = payload["source_run_url"]
              helmrelease_path.write_text(yaml.safe_dump(release_doc, sort_keys=False), encoding="utf-8")
          PY

      - name: Commit and push promotion branch
        run: |
          cd platform-gitops
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git checkout -b "automation/platform-workloads-${GITHUB_RUN_ID}"
          git add .
          if git diff --cached --quiet; then
            echo "PROMOTION_HAS_CHANGES=false" >> "$GITHUB_ENV"
            exit 0
          fi
          git commit -m "chore(platform-gitops): promote platform workloads from ${GITHUB_SHA}"
          git push origin HEAD
          echo "PROMOTION_HAS_CHANGES=true" >> "$GITHUB_ENV"

      - name: Open pull request
        if: env.PROMOTION_HAS_CHANGES == 'true'
        run: |
          cd platform-gitops
          gh pr create \
            --repo "$GITOPS_REPOSITORY" \
            --base "$GITOPS_BASE_REF" \
            --head "automation/platform-workloads-${GITHUB_RUN_ID}" \
            --title "chore(platform-gitops): promote platform workloads from ${GITHUB_SHA}" \
            --body "Promotes OCI Helm chart and image digest pins for the first platform workloads."
"""


def render_cluster_flux_kustomization(*, workload_cluster_name: str) -> str:
    return f"""apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: platform-workloads
  namespace: flux-system
spec:
  interval: 10m
  prune: true
  wait: true
  timeout: 10m
  dependsOn:
    - name: platform-openbao-integration
    - name: platform-alloy
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/{workload_cluster_name}/platform-workloads
"""


def render_apps_readme(*, workload_cluster_name: str) -> str:
    return f"""# platform-workloads/{workload_cluster_name}

This path freezes the first app-delivery scaffold for Kubernetes-managed first-party platform workloads on `{workload_cluster_name}`.

Initial workload set:

- `backend`
- `task-worker`

Rules:

- workloads consume OCI Helm charts from `GHCR` through `OCIRepository`;
- `HelmRelease` objects pin both chart version and workload image digest;
- namespace-local image pull and runtime secret wiring are explicit and remain out of git;
- later workloads may reuse this pattern, but must not bypass the chart and promotion contract frozen here.
"""


def render_apps_kustomization() -> str:
    return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - backend
  - task-worker
"""


def render_platform_apps_namespace() -> str:
    return """apiVersion: v1
kind: Namespace
metadata:
  name: platform-apps
  labels:
    cybervpn.io/app-surface: platform-workloads
    cybervpn.io/trust-bundle: "enabled"
"""


def render_workload_kustomization() -> str:
    return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ocirepository.yaml
  - helmrelease.yaml
"""


def render_workload_ocirepository(*, chart_repo_name: str, chart_name: str, source_repository_slug: str) -> str:
    return f"""apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: {chart_repo_name}
  namespace: flux-system
spec:
  interval: 15m
  url: oci://ghcr.io/{source_repository_slug.lower()}/charts/{chart_name}
  layerSelector:
    mediaType: application/vnd.cncf.helm.chart.content.v1.tar+gzip
    operation: copy
  secretRef:
    name: ghcr-platform-workloads
  ref:
    tag: REPLACE_ME_CHART_VERSION
"""


def render_backend_helmrelease(*, chart_repo_name: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cybervpn-backend
  namespace: platform-apps
  annotations:
    cybervpn.io/source-commit: REPLACE_ME_SOURCE_COMMIT
    cybervpn.io/source-run-url: REPLACE_ME_SOURCE_RUN_URL
spec:
  interval: 10m
  chartRef:
    kind: OCIRepository
    name: {chart_repo_name}
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: 2
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend
      digest: sha256:REPLACE_ME_BACKEND_IMAGE_DIGEST
      tag: ""
      pullPolicy: IfNotPresent
    imagePullSecrets:
      - name: ghcr-platform-workloads
    externalSecret:
      enabled: true
      refreshInterval: 1h
      secretStoreRef:
        kind: ClusterSecretStore
        name: openbao-apps
      targetName: backend-runtime
      extractKey: kv-apps/data/nonprod/platform/backend
    service:
      enabled: true
      type: ClusterIP
      port: 8000
      targetPort: 8000
"""


def render_task_worker_helmrelease(*, chart_repo_name: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cybervpn-task-worker
  namespace: platform-apps
  annotations:
    cybervpn.io/source-commit: REPLACE_ME_SOURCE_COMMIT
    cybervpn.io/source-run-url: REPLACE_ME_SOURCE_RUN_URL
spec:
  interval: 10m
  chartRef:
    kind: OCIRepository
    name: {chart_repo_name}
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: 1
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker
      digest: sha256:REPLACE_ME_TASK_WORKER_IMAGE_DIGEST
      tag: ""
      pullPolicy: IfNotPresent
    imagePullSecrets:
      - name: ghcr-platform-workloads
    externalSecret:
      enabled: true
      refreshInterval: 1h
      secretStoreRef:
        kind: ClusterSecretStore
        name: openbao-apps
      targetName: task-worker-runtime
      extractKey: kv-apps/data/nonprod/platform/task-worker
"""


def render_versions_env(
    *,
    source_repo_name: str,
    source_repository_slug: str,
    gitops_repo_name: str,
    workload_cluster_name: str,
) -> str:
    return (
        f"SOURCE_REPOSITORY={source_repo_name}\n"
        f"SOURCE_REPOSITORY_SLUG={source_repository_slug}\n"
        f"GITOPS_REPOSITORY={gitops_repo_name}\n"
        f"TARGET_WORKLOAD_CLUSTER={workload_cluster_name}\n"
        "HELM_SETUP_ACTION=azure/setup-helm@v4\n"
        "GHCR_IMAGE_PULL_SECRET=ghcr-platform-workloads\n"
        "GHCR_CHART_NAMESPACE=ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/charts\n"
        "BACKEND_CHART_NAME=cybervpn-backend\n"
        "TASK_WORKER_CHART_NAME=cybervpn-task-worker\n"
        "PLATFORM_GITOPS_TOKEN_SECRET=PLATFORM_GITOPS_TOKEN\n"
    )


def render_check_script(*, workload_cluster_name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

flux get kustomizations -A
flux get sources oci -A
kubectl get helmreleases.helm.toolkit.fluxcd.io -n platform-apps
kubectl get deployments -n platform-apps
kubectl get externalsecrets.external-secrets.io -n platform-apps

echo "P2.5 workload-delivery checks completed for {workload_cluster_name}."
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    source_repo_dir = output_dir / "source-repo"
    gitops_repo_dir = output_dir / "platform-gitops"
    workload_cluster_dir = gitops_repo_dir / "clusters" / args.workload_cluster_name
    apps_dir = gitops_repo_dir / "apps" / args.workload_cluster_name / "platform-workloads"

    write_text(
        output_dir / "README.md",
        render_root_readme(
            source_repo_name=args.source_repo_name,
            source_repository_slug=args.source_repository_slug,
            gitops_repo_name=args.gitops_repo_name,
            workload_cluster_name=args.workload_cluster_name,
        ),
        mode=0o644,
    )
    write_text(source_repo_dir / "README.md", render_source_repo_readme(), mode=0o644)
    write_text(gitops_repo_dir / "README.md", render_gitops_repo_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(
        output_dir / "versions.env",
        render_versions_env(
            source_repo_name=args.source_repo_name,
            source_repository_slug=args.source_repository_slug,
            gitops_repo_name=args.gitops_repo_name,
            workload_cluster_name=args.workload_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        output_dir / "scripts" / "check-workload-delivery.sh",
        render_check_script(workload_cluster_name=args.workload_cluster_name),
        mode=0o750,
    )

    write_text(source_repo_dir / "charts" / "README.md", render_chart_readme(), mode=0o644)
    write_text(
        source_repo_dir / ".github" / "workflows" / "platform-workload-delivery.yml",
        render_workflow(),
        mode=0o644,
    )

    backend_chart_dir = source_repo_dir / "charts" / "cybervpn-backend"
    task_worker_chart_dir = source_repo_dir / "charts" / "cybervpn-task-worker"

    for chart_dir, chart_name, description, values_content, deployment_content, service_content in (
        (
            backend_chart_dir,
            "cybervpn-backend",
            "CyberVPN backend workload chart",
            render_backend_values(image_repository="ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend"),
            render_backend_deployment_tpl(),
            render_backend_service_tpl(),
        ),
        (
            task_worker_chart_dir,
            "cybervpn-task-worker",
            "CyberVPN task-worker workload chart",
            render_task_worker_values(image_repository="ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker"),
            render_task_worker_deployment_tpl(),
            "",
        ),
    ):
        write_text(chart_dir / "Chart.yaml", render_chart_yaml(chart_name=chart_name, description=description), mode=0o644)
        write_text(chart_dir / "values.yaml", values_content, mode=0o644)
        write_text(chart_dir / "templates" / "_helpers.tpl", render_helpers_tpl(), mode=0o644)
        write_text(chart_dir / "templates" / "serviceaccount.yaml", render_serviceaccount_tpl(), mode=0o644)
        write_text(chart_dir / "templates" / "externalsecret.yaml", render_externalsecret_tpl(), mode=0o644)
        write_text(chart_dir / "templates" / "deployment.yaml", deployment_content, mode=0o644)
        if service_content:
            write_text(chart_dir / "templates" / "service.yaml", service_content, mode=0o644)

    write_text(
        workload_cluster_dir / "platform-workloads.yaml",
        render_cluster_flux_kustomization(workload_cluster_name=args.workload_cluster_name),
        mode=0o644,
    )
    write_text(
        apps_dir / "README.md",
        render_apps_readme(workload_cluster_name=args.workload_cluster_name),
        mode=0o644,
    )
    write_text(apps_dir / "kustomization.yaml", render_apps_kustomization(), mode=0o644)
    write_text(apps_dir / "namespace.yaml", render_platform_apps_namespace(), mode=0o644)

    workload_entries = (
        (
            "backend",
            "cybervpn-backend-chart",
            "cybervpn-backend",
            render_backend_helmrelease(chart_repo_name="cybervpn-backend-chart"),
        ),
        (
            "task-worker",
            "cybervpn-task-worker-chart",
            "cybervpn-task-worker",
            render_task_worker_helmrelease(chart_repo_name="cybervpn-task-worker-chart"),
        ),
    )

    for workload_name, chart_repo_name, chart_name, helmrelease in workload_entries:
        workload_dir = apps_dir / workload_name
        write_text(workload_dir / "kustomization.yaml", render_workload_kustomization(), mode=0o644)
        write_text(
            workload_dir / "ocirepository.yaml",
            render_workload_ocirepository(
                chart_repo_name=chart_repo_name,
                chart_name=chart_name,
                source_repository_slug=args.source_repository_slug,
            ),
            mode=0o644,
        )
        write_text(workload_dir / "helmrelease.yaml", helmrelease, mode=0o644)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the P2.5 workload-delivery scaffold.")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.add_argument("--source-repo-name", default="VPNBussiness")
    render_scaffold.add_argument("--source-repository-slug", default="REPLACE_ME_OWNER/vpnbussiness")
    render_scaffold.add_argument("--gitops-repo-name", default="platform-gitops")
    render_scaffold.add_argument("--workload-cluster-name", default="nonprod-hetzner-hel1-core")
    render_scaffold.set_defaults(func=command_render_scaffold)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
