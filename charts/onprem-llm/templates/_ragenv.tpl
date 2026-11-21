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
- {name: GUARD_ENABLED, value: {{ .Values.guard.enabled | quote }}}
- {name: GUARD_URL, value: "http://{{ .Release.Name }}-guard:8080"}
- {name: GUARD_THRESHOLD, value: {{ .Values.guard.threshold | quote }}}
- {name: GUARD_FAIL_MODE, value: {{ .Values.guard.failMode | quote }}}
- {name: GUARD_DEBUG, value: {{ .Values.guard.debugEndpoint | quote }}}
- {name: RERANK_ENABLED, value: {{ .Values.rerank.enabled | quote }}}
- {name: RERANK_DEFAULT, value: {{ .Values.rerank.default | quote }}}
- {name: RERANK_URL, value: "http://{{ .Release.Name }}-rerank:8080/v1"}
- {name: RERANK_MODEL, value: {{ .Values.rerank.servedName | quote }}}
- {name: RERANK_CANDIDATES, value: {{ .Values.rerank.candidates | quote }}}
{{- end -}}
