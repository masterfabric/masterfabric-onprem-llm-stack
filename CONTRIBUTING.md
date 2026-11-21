# Contributing

This is a lab repository. Changes are welcome when they keep it runnable on a laptop and keep every
number in the README reproducible.

## Ground rules

- **Measured numbers only.** If a change affects results, re-run `make eval` and `make load`, regenerate
  the images, and commit the new `docs/results/*.json` with them. Never edit a results file by hand.
- **Do not tune on the evaluation set silently.** If a prompt or threshold change is motivated by an
  evaluation run, keep the earlier result file and say so in the commit body (see `eval_quality_prompt_v1.json`).
- **Guardrail changes need tests.** Add a case to `rag/tests/` and, for new attack classes, to
  `eval/attacks.jsonl`, including evasions you expect to miss.
- **Chart changes must lint for both backends**: `make lint`.
- One logical change per commit, Conventional Commit subject, and a body that explains why.
- No secrets. The pgvector password is generated in-cluster; nothing in git is a credential.

## Development loop

```bash
make cluster image deploy
make test && make lint
make eval && make load
```

## License of contributions

By contributing you agree that your contribution is licensed under the AGPL-3.0, as described in
[LICENSE](LICENSE) and [NOTICE](NOTICE).
