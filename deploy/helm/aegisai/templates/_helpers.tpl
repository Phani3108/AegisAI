{{- define "aegisai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "aegisai.fullname" -}}
{{- printf "%s" (include "aegisai.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end }}
