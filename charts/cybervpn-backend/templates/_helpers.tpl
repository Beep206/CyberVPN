{{- define "cybervpn-backend.name" -}}
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
