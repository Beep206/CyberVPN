{{- define "cybervpn-task-worker.name" -}}
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
