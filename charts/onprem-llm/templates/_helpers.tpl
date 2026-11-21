{{- define "onprem-llm.fullname" -}}{{ .Release.Name }}{{- end -}}

{{- define "onprem-llm.labels" -}}
app.kubernetes.io/part-of: onprem-llm
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "onprem-llm.selector" -}}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "onprem-llm.pgSecret" -}}
{{- default (printf "%s-pgvector" .Release.Name) .Values.pgvector.existingSecret -}}
{{- end -}}

{{/* initContainer that downloads a model file into /models once (skips when present, verifies sha256 if set) */}}
{{- define "onprem-llm.downloader" -}}
- name: fetch-model
  image: {{ .root.Values.modelDownloader.image }}
  command: ["sh", "-c"]
  args:
    - |
      set -e
      f=/models/{{ .model.file }}
      if [ ! -s "$f" ]; then
        echo "downloading {{ .model.file }}"
        curl -fsSL --retry 5 -o "$f.part" "{{ .model.url }}" && mv "$f.part" "$f"
      fi
      {{- if .model.sha256 }}
      echo "{{ .model.sha256 }}  $f" | sha256sum -c -
      {{- end }}
      ls -l "$f"
  volumeMounts:
    - {name: models, mountPath: /models}
  securityContext: {runAsUser: 100, runAsGroup: 101, allowPrivilegeEscalation: false}
{{- end -}}
