#!/usr/bin/env python3
"""Render the P2.8 initial control-plane workload migration scaffold."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


WORKLOAD_CLUSTER_NAME = "nonprod-hetzner-hel1-core"
APP_NAMESPACE = "platform-apps"
SOURCE_REPOSITORY_SLUG = "beep/vpnbussiness"
BACKEND_SECRET_KEY = "kv-apps/data/nonprod/platform/backend"
TASK_WORKER_SECRET_KEY = "kv-apps/data/nonprod/platform/task-worker"
BACKEND_CHART_NAME = "cybervpn-backend"
TASK_WORKER_CHART_NAME = "cybervpn-task-worker"

REQUIRED_ANCHORS: dict[str, tuple[str, ...]] = {
    "backend/Dockerfile": ('CMD ["python", "-m", "src.serve"]', "EXPOSE 9091"),
    "backend/alembic.ini": ("[alembic]",),
    "backend/src/serve.py": ("start_http_server",),
    "backend/src/main.py": ('@app.get("/health")', '@app.get("/readiness")'),
    "backend/src/config/settings.py": ("metrics_port: int = 9091", "remnawave_token: SecretStr"),
    "services/task-worker/Dockerfile": ('CMD ["taskiq", "worker", "src.broker:broker"',),
    "services/task-worker/src/broker.py": ("TaskiqScheduler", "PROMETHEUS_MULTIPROC_DIR"),
    "services/task-worker/src/config.py": ("metrics_port: int = 9091", "worker_concurrency: int = 2"),
    "infra/docker-compose.yml": ('cybervpn-worker:', 'cybervpn-scheduler:', '"taskiq", "scheduler", "src.broker:scheduler"', "PROMETHEUS_MULTIPROC_DIR"),
    "infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml": (
        "control_plane_stack_backend_env",
        "control_plane_stack_worker_env",
        "control_plane_stack_scheduler_env",
    ),
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme() -> str:
    return f"""# P2.8 initial control-plane workload migration scaffold

This scaffold freezes the first Kubernetes runtime contract for CyberVPN control-plane
workloads after the P2.2 platform-services baseline, the P2.5 OCI Helm delivery
contract, and the P2.6 event-backbone contract.

Frozen initial migration set:

- `backend`
- `task-worker`
- `task-scheduler`

Frozen exclusions:

- `helix-adapter`
- `telegram-bot`

Canonical decisions frozen here:

- `task-scheduler` is a second release of the `{TASK_WORKER_CHART_NAME}` chart, not a new image family;
- both worker releases consume OpenBao-backed runtime material through `ExternalSecret`;
- `task-worker` and `task-scheduler` intentionally share the same OpenBao extract key:
  - `{TASK_WORKER_SECRET_KEY}`
- `backend` carries a pre-install and pre-upgrade database migration hook:
  - `alembic upgrade head`
- rollout order is:
  - namespace
  - backend
  - task-worker
  - task-scheduler
- public ingress cutover is intentionally out of scope for this packet; `P2.8` freezes
  runtime migration shape, not final external traffic cutover.

Important boundaries:

- this scaffold does not claim a live cluster, live Flux reconciliation, or live OpenBao
  secret materialization already exists;
- this scaffold does not pull secrets into git;
- this scaffold does not declare `helix-adapter` or `telegram-bot` Kubernetes-ready.
"""


def render_source_repo_readme() -> str:
    return """# source-repo

This directory models the source-repo changes needed for `P2.8`.

It extends the `P2.5` delivery contract into a real runtime contract for the first
control-plane workloads:

- backend chart now carries:
  - separate HTTP and metrics ports
  - OpenBao-backed `ExternalSecret`
  - `ServiceMonitor`
  - `PodDisruptionBudget`
  - pre-install and pre-upgrade database migration `Job`
- task-worker chart now carries:
  - worker and scheduler runtime modes
  - separate metrics service surface
  - optional Prometheus multiprocess volume
  - OpenBao-backed `ExternalSecret`
  - `ServiceMonitor`
  - `PodDisruptionBudget`

The scaffold is still repo-only:

- no live registry or chart publication occurs here;
- no live secrets or cluster credentials are embedded here;
- rollout proof remains a later live-closure step.
"""


def render_gitops_repo_readme() -> str:
    return f"""# platform-gitops

This directory models the GitOps-repo side of `P2.8`.

Cluster:

- `{WORKLOAD_CLUSTER_NAME}`

Namespace:

- `{APP_NAMESPACE}`

Frozen releases:

- `cybervpn-backend`
- `cybervpn-task-worker`
- `cybervpn-task-scheduler`

Rollout sequencing is intentionally explicit:

1. namespace exists;
2. backend release reconciles first;
3. task-worker reconciles second;
4. task-scheduler reconciles last.

The scheduler release intentionally reuses the task-worker chart and the same OpenBao
extract key as the worker release while applying different runtime command values.
"""


def render_backend_chart_yaml() -> str:
    return """apiVersion: v2
name: cybervpn-backend
description: CyberVPN backend runtime chart for the first Kubernetes control-plane migration set
type: application
version: 0.2.0
appVersion: "0.2.0"
"""


def render_task_worker_chart_yaml() -> str:
    return """apiVersion: v2
name: cybervpn-task-worker
description: CyberVPN task-worker runtime chart for worker and scheduler releases
type: application
version: 0.2.0
appVersion: "0.2.0"
"""


def render_backend_values() -> str:
    return f"""replicaCount: 2

image:
  repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend
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
  extractKey: {BACKEND_SECRET_KEY}

service:
  enabled: true
  type: ClusterIP
  port: 8000
  targetPort: 8000

metrics:
  enabled: true
  servicePort: 9091
  containerPort: 9091
  serviceMonitor:
    enabled: true
    interval: 30s

pdb:
  enabled: true
  minAvailable: 1

migrationJob:
  enabled: true
  command:
    - alembic
    - upgrade
    - head

resources: {{}}
"""


def render_task_worker_values() -> str:
    return f"""replicaCount: 2

image:
  repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker
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
  extractKey: {TASK_WORKER_SECRET_KEY}

workload:
  mode: worker
  command:
    - sh
    - -c
  args:
    - mkdir -p "$PROMETHEUS_MULTIPROC_DIR" && rm -f "$PROMETHEUS_MULTIPROC_DIR"/* && exec taskiq worker src.broker:broker --workers "${{WORKER_CONCURRENCY:-2}}" --fs-discover

metrics:
  enabled: true
  servicePort: 9091
  containerPort: 9091
  serviceMonitor:
    enabled: true
    interval: 30s

prometheusMultiproc:
  enabled: true
  dir: /tmp/prometheus-multiproc

pdb:
  enabled: true
  minAvailable: 1

resources: {{}}
"""


def render_task_scheduler_values() -> str:
    return f"""replicaCount: 1

image:
  repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker
  digest: sha256:REPLACE_ME_TASK_SCHEDULER_IMAGE_DIGEST
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
  targetName: task-scheduler-runtime
  extractKey: {TASK_WORKER_SECRET_KEY}

workload:
  mode: scheduler
  command:
    - taskiq
    - scheduler
    - src.broker:scheduler
  args: []

metrics:
  enabled: true
  servicePort: 9091
  containerPort: 9091
  serviceMonitor:
    enabled: true
    interval: 30s

prometheusMultiproc:
  enabled: false
  dir: /tmp/prometheus-multiproc

pdb:
  enabled: false
  minAvailable: 1

resources: {{}}
"""


def render_backend_helpers_tpl() -> str:
    return """{{- define "cybervpn-backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "cybervpn-backend.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "cybervpn-backend.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-backend.labels" -}}
app.kubernetes.io/name: {{ include "cybervpn-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: api
app.kubernetes.io/part-of: cybervpn-control-plane
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "cybervpn-backend.secretName" -}}
{{- if .Values.externalSecret.targetName -}}
{{- .Values.externalSecret.targetName -}}
{{- else -}}
{{- printf "%s-runtime" (include "cybervpn-backend.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-backend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "cybervpn-backend.fullname" . -}}
{{- end -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
"""


def render_task_worker_helpers_tpl() -> str:
    return """{{- define "cybervpn-task-worker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "cybervpn-task-worker.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" (include "cybervpn-task-worker.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-task-worker.labels" -}}
app.kubernetes.io/name: {{ include "cybervpn-task-worker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: {{ .Values.workload.mode | default "worker" }}
app.kubernetes.io/part-of: cybervpn-control-plane
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "cybervpn-task-worker.secretName" -}}
{{- if .Values.externalSecret.targetName -}}
{{- .Values.externalSecret.targetName -}}
{{- else -}}
{{- printf "%s-runtime" (include "cybervpn-task-worker.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "cybervpn-task-worker.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "cybervpn-task-worker.fullname" . -}}
{{- end -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
"""


def render_serviceaccount_tpl(helper_prefix: str) -> str:
    return f"""{{{{- if .Values.serviceAccount.create }}}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{{{ include "{helper_prefix}.serviceAccountName" . }}}}
  labels:
    {{{{- include "{helper_prefix}.labels" . | nindent 4 }}}}
{{{{- end }}}}
"""


def render_externalsecret_tpl(helper_prefix: str) -> str:
    return f"""{{{{- if .Values.externalSecret.enabled }}}}
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {{{{ include "{helper_prefix}.secretName" . }}}}
  labels:
    {{{{- include "{helper_prefix}.labels" . | nindent 4 }}}}
spec:
  refreshInterval: {{{{ .Values.externalSecret.refreshInterval | quote }}}}
  secretStoreRef:
    kind: {{{{ .Values.externalSecret.secretStoreRef.kind | quote }}}}
    name: {{{{ .Values.externalSecret.secretStoreRef.name | quote }}}}
  target:
    name: {{{{ include "{helper_prefix}.secretName" . }}}}
    creationPolicy: Owner
  dataFrom:
    - extract:
        key: {{{{ .Values.externalSecret.extractKey | quote }}}}
{{{{- end }}}}
"""


def render_backend_deployment_tpl() -> str:
    return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "cybervpn-backend.fullname" . }}
  labels:
    {{- include "cybervpn-backend.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-backend.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        {{- include "cybervpn-backend.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "cybervpn-backend.serviceAccountName" . }}
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ .name }}
        {{- end }}
      containers:
        - name: backend
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
            - name: metrics
              containerPort: {{ .Values.metrics.containerPort }}
          envFrom:
            - secretRef:
                name: {{ include "cybervpn-backend.secretName" . }}
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /readiness
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
  name: {{ include "cybervpn-backend.fullname" . }}
  labels:
    {{- include "cybervpn-backend.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    app.kubernetes.io/name: {{ include "cybervpn-backend.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
    - name: metrics
      port: {{ .Values.metrics.servicePort }}
      targetPort: metrics
{{- end }}
"""


def render_backend_servicemonitor_tpl() -> str:
    return """{{- if and .Values.metrics.enabled .Values.metrics.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "cybervpn-backend.fullname" . }}
  labels:
    {{- include "cybervpn-backend.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-backend.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  endpoints:
    - port: metrics
      interval: {{ .Values.metrics.serviceMonitor.interval }}
{{- end }}
"""


def render_backend_pdb_tpl() -> str:
    return """{{- if .Values.pdb.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "cybervpn-backend.fullname" . }}
  labels:
    {{- include "cybervpn-backend.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.pdb.minAvailable }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-backend.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
"""


def render_backend_migration_job_tpl() -> str:
    return """{{- if .Values.migrationJob.enabled }}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "cybervpn-backend.fullname" . }}-db-migrate
  labels:
    {{- include "cybervpn-backend.labels" . | nindent 4 }}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  backoffLimit: 2
  template:
    metadata:
      labels:
        {{- include "cybervpn-backend.labels" . | nindent 8 }}
    spec:
      restartPolicy: OnFailure
      serviceAccountName: {{ include "cybervpn-backend.serviceAccountName" . }}
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ .name }}
        {{- end }}
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          command:
            {{- toYaml .Values.migrationJob.command | nindent 12 }}
          envFrom:
            - secretRef:
                name: {{ include "cybervpn-backend.secretName" . }}
{{- end }}
"""


def render_task_worker_deployment_tpl() -> str:
    return """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "cybervpn-task-worker.fullname" . }}
  labels:
    {{- include "cybervpn-task-worker.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-task-worker.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        {{- include "cybervpn-task-worker.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "cybervpn-task-worker.serviceAccountName" . }}
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ .name }}
        {{- end }}
      {{- if .Values.prometheusMultiproc.enabled }}
      volumes:
        - name: prometheus-multiproc
          emptyDir: {{}}
      {{- end }}
      containers:
        - name: {{ .Values.workload.mode | default "worker" }}
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: metrics
              containerPort: {{ .Values.metrics.containerPort }}
          envFrom:
            - secretRef:
                name: {{ include "cybervpn-task-worker.secretName" . }}
          {{- if .Values.prometheusMultiproc.enabled }}
          env:
            - name: PROMETHEUS_MULTIPROC_DIR
              value: {{ .Values.prometheusMultiproc.dir | quote }}
          volumeMounts:
            - name: prometheus-multiproc
              mountPath: {{ .Values.prometheusMultiproc.dir | quote }}
          {{- end }}
          command:
            {{- toYaml .Values.workload.command | nindent 12 }}
          {{- if .Values.workload.args }}
          args:
            {{- toYaml .Values.workload.args | nindent 12 }}
          {{- end }}
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


def render_task_worker_service_tpl() -> str:
    return """{{- if .Values.metrics.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "cybervpn-task-worker.fullname" . }}
  labels:
    {{- include "cybervpn-task-worker.labels" . | nindent 4 }}
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: {{ include "cybervpn-task-worker.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - name: metrics
      port: {{ .Values.metrics.servicePort }}
      targetPort: metrics
{{- end }}
"""


def render_task_worker_servicemonitor_tpl() -> str:
    return """{{- if and .Values.metrics.enabled .Values.metrics.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "cybervpn-task-worker.fullname" . }}
  labels:
    {{- include "cybervpn-task-worker.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-task-worker.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  endpoints:
    - port: metrics
      interval: {{ .Values.metrics.serviceMonitor.interval }}
{{- end }}
"""


def render_task_worker_pdb_tpl() -> str:
    return """{{- if .Values.pdb.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "cybervpn-task-worker.fullname" . }}
  labels:
    {{- include "cybervpn-task-worker.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.pdb.minAvailable }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cybervpn-task-worker.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
"""


def render_cluster_flux_kustomization(*, name: str, path: str, depends_on: list[str]) -> str:
    depends_block = "\n".join(f"    - name: {item}" for item in depends_on)
    return (
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 10m\n"
        "  prune: true\n"
        "  wait: true\n"
        "  timeout: 10m\n"
        "  dependsOn:\n"
        f"{depends_block}\n"
        "  sourceRef:\n"
        "    kind: GitRepository\n"
        "    name: flux-system\n"
        f"  path: {path}\n"
    )


def render_simple_kustomization(*, resources: list[str]) -> str:
    rendered = "\n".join(f"  - {item}" for item in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
{rendered}
"""


def render_namespace_yaml() -> str:
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {APP_NAMESPACE}
  labels:
    cybervpn.io/runtime-surface: platform-control-plane
    cybervpn.io/openbao-secret-delivery: "required"
"""


def render_ocirepository(*, name: str, chart_name: str) -> str:
    return f"""apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: {name}
  namespace: flux-system
spec:
  interval: 30m
  layerSelector:
    mediaType: application/vnd.cncf.helm.chart.content.v1.tar+gzip
    operation: copy
  secretRef:
    name: ghcr-platform-workloads
  url: oci://ghcr.io/{SOURCE_REPOSITORY_SLUG}/charts/{chart_name}
  ref:
    tag: REPLACE_ME_CHART_VERSION
"""


def render_backend_helmrelease() -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cybervpn-backend
  namespace: {APP_NAMESPACE}
spec:
  interval: 15m
  chartRef:
    kind: OCIRepository
    name: cybervpn-backend-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend
      digest: sha256:REPLACE_ME_BACKEND_IMAGE_DIGEST
    externalSecret:
      targetName: backend-runtime
      extractKey: {BACKEND_SECRET_KEY}
    service:
      enabled: true
      type: ClusterIP
      port: 8000
      targetPort: 8000
    metrics:
      enabled: true
      servicePort: 9091
      containerPort: 9091
      serviceMonitor:
        enabled: true
        interval: 30s
    pdb:
      enabled: true
      minAvailable: 1
    migrationJob:
      enabled: true
      command:
        - alembic
        - upgrade
        - head
"""


def render_task_worker_helmrelease(*, release_name: str, digest_placeholder: str, target_name: str, mode: str, command: list[str], args: list[str], multiproc_enabled: bool, replica_count: int, pdb_enabled: bool) -> str:
    command_block = "\n".join(f"        - {item}" for item in command)
    args_block = "\n".join(f"        - {item}" for item in args) if args else "        []"
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: {release_name}
  namespace: {APP_NAMESPACE}
spec:
  interval: 15m
  chartRef:
    kind: OCIRepository
    name: cybervpn-task-worker-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: {replica_count}
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker
      digest: {digest_placeholder}
    externalSecret:
      targetName: {target_name}
      extractKey: {TASK_WORKER_SECRET_KEY}
    workload:
      mode: {mode}
      command:
{command_block}
      args:
{args_block}
    metrics:
      enabled: true
      servicePort: 9091
      containerPort: 9091
      serviceMonitor:
        enabled: true
        interval: 30s
    prometheusMultiproc:
      enabled: {"true" if multiproc_enabled else "false"}
      dir: /tmp/prometheus-multiproc
    pdb:
      enabled: {"true" if pdb_enabled else "false"}
      minAvailable: 1
"""


def render_versions_env() -> str:
    return f"""WORKLOAD_CLUSTER_NAME={WORKLOAD_CLUSTER_NAME}
APP_NAMESPACE={APP_NAMESPACE}
SOURCE_REPOSITORY_SLUG={SOURCE_REPOSITORY_SLUG}
BACKEND_SECRET_KEY={BACKEND_SECRET_KEY}
TASK_WORKER_SECRET_KEY={TASK_WORKER_SECRET_KEY}
INITIAL_WORKLOADS=backend,task-worker,task-scheduler
EXCLUDED_WORKLOADS=helix-adapter,telegram-bot
"""


def render_spec_manifest() -> str:
    return f"""packet: P2.8
cluster: {WORKLOAD_CLUSTER_NAME}
namespace: {APP_NAMESPACE}
initialWorkloads:
  - backend
  - task-worker
  - task-scheduler
excludedWorkloads:
  - helix-adapter
  - telegram-bot
secretContracts:
  backend: {BACKEND_SECRET_KEY}
  task-worker: {TASK_WORKER_SECRET_KEY}
  task-scheduler: {TASK_WORKER_SECRET_KEY}
rolloutOrder:
  - namespace
  - backend
  - task-worker
  - task-scheduler
"""


def render_check_script() -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "P2.8 initial control-plane workload migration scaffold"
echo "  cluster: {WORKLOAD_CLUSTER_NAME}"
echo "  namespace: {APP_NAMESPACE}"
echo "  initial workloads: backend, task-worker, task-scheduler"
echo "  excluded workloads: helix-adapter, telegram-bot"
echo "  backend secret key: {BACKEND_SECRET_KEY}"
echo "  task-worker secret key: {TASK_WORKER_SECRET_KEY}"
"""


def validate_repo_root(repo_root: Path) -> list[str]:
    issues: list[str] = []
    for relative_path, required_tokens in REQUIRED_ANCHORS.items():
        path = repo_root / relative_path
        if not path.exists():
            issues.append(f"missing:{relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for token in required_tokens:
            if token not in content:
                issues.append(f"missing-token:{relative_path}:{token}")
    return issues


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()

    write_text(output_dir / "README.md", render_root_readme())
    write_text(output_dir / "versions.env", render_versions_env())
    write_text(output_dir / "spec-manifest.yaml", render_spec_manifest())
    write_text(output_dir / "scripts" / "check-control-plane-workloads.sh", render_check_script(), mode=0o750)

    source_repo_dir = output_dir / "source-repo"
    gitops_repo_dir = output_dir / "platform-gitops"

    write_text(source_repo_dir / "README.md", render_source_repo_readme())
    write_text(gitops_repo_dir / "README.md", render_gitops_repo_readme())

    backend_chart_dir = source_repo_dir / "charts" / BACKEND_CHART_NAME
    write_text(backend_chart_dir / "Chart.yaml", render_backend_chart_yaml())
    write_text(backend_chart_dir / "values.yaml", render_backend_values())
    write_text(backend_chart_dir / "templates" / "_helpers.tpl", render_backend_helpers_tpl())
    write_text(backend_chart_dir / "templates" / "serviceaccount.yaml", render_serviceaccount_tpl("cybervpn-backend"))
    write_text(backend_chart_dir / "templates" / "externalsecret.yaml", render_externalsecret_tpl("cybervpn-backend"))
    write_text(backend_chart_dir / "templates" / "deployment.yaml", render_backend_deployment_tpl())
    write_text(backend_chart_dir / "templates" / "service.yaml", render_backend_service_tpl())
    write_text(backend_chart_dir / "templates" / "servicemonitor.yaml", render_backend_servicemonitor_tpl())
    write_text(backend_chart_dir / "templates" / "poddisruptionbudget.yaml", render_backend_pdb_tpl())
    write_text(backend_chart_dir / "templates" / "migration-job.yaml", render_backend_migration_job_tpl())

    task_worker_chart_dir = source_repo_dir / "charts" / TASK_WORKER_CHART_NAME
    write_text(task_worker_chart_dir / "Chart.yaml", render_task_worker_chart_yaml())
    write_text(task_worker_chart_dir / "values.yaml", render_task_worker_values())
    write_text(task_worker_chart_dir / "values-scheduler.yaml", render_task_scheduler_values())
    write_text(task_worker_chart_dir / "templates" / "_helpers.tpl", render_task_worker_helpers_tpl())
    write_text(task_worker_chart_dir / "templates" / "serviceaccount.yaml", render_serviceaccount_tpl("cybervpn-task-worker"))
    write_text(task_worker_chart_dir / "templates" / "externalsecret.yaml", render_externalsecret_tpl("cybervpn-task-worker"))
    write_text(task_worker_chart_dir / "templates" / "deployment.yaml", render_task_worker_deployment_tpl())
    write_text(task_worker_chart_dir / "templates" / "service.yaml", render_task_worker_service_tpl())
    write_text(task_worker_chart_dir / "templates" / "servicemonitor.yaml", render_task_worker_servicemonitor_tpl())
    write_text(task_worker_chart_dir / "templates" / "poddisruptionbudget.yaml", render_task_worker_pdb_tpl())

    apps_root = gitops_repo_dir / "apps" / WORKLOAD_CLUSTER_NAME / "platform-workloads"
    clusters_root = gitops_repo_dir / "clusters" / WORKLOAD_CLUSTER_NAME

    write_text(apps_root / "README.md", render_gitops_repo_readme())
    write_text(apps_root / "namespace" / "kustomization.yaml", render_simple_kustomization(resources=["namespace.yaml"]))
    write_text(apps_root / "namespace" / "namespace.yaml", render_namespace_yaml())
    write_text(apps_root / "backend" / "kustomization.yaml", render_simple_kustomization(resources=["ocirepository.yaml", "helmrelease.yaml"]))
    write_text(apps_root / "backend" / "ocirepository.yaml", render_ocirepository(name="cybervpn-backend-chart", chart_name=BACKEND_CHART_NAME))
    write_text(apps_root / "backend" / "helmrelease.yaml", render_backend_helmrelease())
    write_text(apps_root / "task-worker" / "kustomization.yaml", render_simple_kustomization(resources=["ocirepository.yaml", "helmrelease.yaml"]))
    write_text(apps_root / "task-worker" / "ocirepository.yaml", render_ocirepository(name="cybervpn-task-worker-chart", chart_name=TASK_WORKER_CHART_NAME))
    write_text(
        apps_root / "task-worker" / "helmrelease.yaml",
        render_task_worker_helmrelease(
            release_name="cybervpn-task-worker",
            digest_placeholder="sha256:REPLACE_ME_TASK_WORKER_IMAGE_DIGEST",
            target_name="task-worker-runtime",
            mode="worker",
            command=["sh", "-c"],
            args=['mkdir -p "$PROMETHEUS_MULTIPROC_DIR" && rm -f "$PROMETHEUS_MULTIPROC_DIR"/* && exec taskiq worker src.broker:broker --workers "${WORKER_CONCURRENCY:-2}" --fs-discover'],
            multiproc_enabled=True,
            replica_count=2,
            pdb_enabled=True,
        ),
    )
    write_text(apps_root / "task-scheduler" / "kustomization.yaml", render_simple_kustomization(resources=["helmrelease.yaml"]))
    write_text(
        apps_root / "task-scheduler" / "helmrelease.yaml",
        render_task_worker_helmrelease(
            release_name="cybervpn-task-scheduler",
            digest_placeholder="sha256:REPLACE_ME_TASK_SCHEDULER_IMAGE_DIGEST",
            target_name="task-scheduler-runtime",
            mode="scheduler",
            command=["taskiq", "scheduler", "src.broker:scheduler"],
            args=[],
            multiproc_enabled=False,
            replica_count=1,
            pdb_enabled=False,
        ),
    )

    write_text(
        clusters_root / "platform-workloads-namespace.yaml",
        render_cluster_flux_kustomization(
            name="platform-workloads-namespace",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/namespace",
            depends_on=["platform-openbao-integration"],
        ),
    )
    write_text(
        clusters_root / "platform-control-plane-backend.yaml",
        render_cluster_flux_kustomization(
            name="platform-control-plane-backend",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/backend",
            depends_on=["platform-workloads-namespace", "platform-kube-prometheus-stack"],
        ),
    )
    write_text(
        clusters_root / "platform-control-plane-task-worker.yaml",
        render_cluster_flux_kustomization(
            name="platform-control-plane-task-worker",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/task-worker",
            depends_on=["platform-control-plane-backend"],
        ),
    )
    write_text(
        clusters_root / "platform-control-plane-task-scheduler.yaml",
        render_cluster_flux_kustomization(
            name="platform-control-plane-task-scheduler",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/task-scheduler",
            depends_on=["platform-control-plane-task-worker"],
        ),
    )

    return 0


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    issues = validate_repo_root(repo_root)
    if issues:
        for issue in issues:
            print(issue)
        return 1

    print("initial_workloads=backend,task-worker,task-scheduler")
    print("excluded_workloads=helix-adapter,telegram-bot")
    print(f"backend_secret_key={BACKEND_SECRET_KEY}")
    print(f"task_worker_secret_key={TASK_WORKER_SECRET_KEY}")
    print(f"task_scheduler_secret_key={TASK_WORKER_SECRET_KEY}")
    print("backend_migration_job=alembic upgrade head")
    print("backend_metrics_port=9091")
    print("task_worker_metrics_port=9091")
    print("scheduler_command=taskiq scheduler src.broker:scheduler")
    print("rollout_order=namespace,backend,task-worker,task-scheduler")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render-scaffold", help="Render the P2.8 migration scaffold.")
    render_parser.add_argument("--output-dir", required=True, help="Output directory for the rendered scaffold.")
    render_parser.set_defaults(func=command_render_scaffold)

    validate_parser = subparsers.add_parser("validate", help="Validate the current repository baseline for P2.8.")
    validate_parser.add_argument("--repo-root", default=".", help="Repository root to validate.")
    validate_parser.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
