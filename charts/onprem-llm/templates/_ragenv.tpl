{{- define "onprem-llm.ragEnv" -}}
- {name: LLM_URL, value: "http://{{ .Release.Name }}-llm:8080/v1"}
- {name: LLM_MODEL, value: {{ .Values.llm.servedName | quote }}}
- {name: EMBED_URL, value: "http://{{ .Release.Name }}-embed:8080/v1"}
- {name: EMBED_MODEL, value: {{ .Values.embed.servedName | quote }}}
- {name: EMBED_DIM, value: {{ .Values.embed.dim | quote }}}
- {name: DATABASE_URL, value: "postgresql://{{ .Values.pgvector.user }}@{{ .Release.Name }}-pgvector:5432/{{ .Values.pgvector.database }}"}
- name: PGPASSWORD
  valueFrom: {secretKeyRef: {name: {{ include "onprem-llm.pgSecret" . }}, key: password}}
- {name: TOP_K, value: {{ .Values.rag.topK | quote }}}
- {name: MIN_SCORE, value: {{ .Values.rag.minScore | quote }}}
- {name: MAX_TOKENS, value: {{ .Values.rag.maxTokens | quote }}}
{{- end -}}
