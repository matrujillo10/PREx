# Example outputs

Real `prex review` artifacts for four PRs in `connectlyai/connectly-backend`,
captured for downstream consumers (generative-UI hosts, dashboards, automated
reviewers) to inspect without running the tool first.

All four runs used `--llm-summarise` (Vertex AI Gemini 2.5 Flash) so every
prose field is filled. Without `--llm-summarise`, all the deterministic
fields below are identical and prose fields (`headline`, `one_liner`,
`what`/`why`/`impact`, `overview`) are `null`.

| Directory | PR | Title | risk_tier | risk_score | flags |
|---|---|---|---|---|---|
| `pr-19858/` | [#19858](https://github.com/connectlyai/connectly-backend/pull/19858) | feat(agent-evaluation): CSAT score filtering | sensitive | 0.75 | no_test, no_docs |
| `pr-19872/` | [#19872](https://github.com/connectlyai/connectly-backend/pull/19872) | feat[talk]: per-persona RPCs with copy-on-write | standard | 0.50 | no_test, secret_like, no_docs |
| `pr-19654/` | [#19654](https://github.com/connectlyai/connectly-backend/pull/19654) | feat[team-agents]: OTEL metrics for ingestion | sensitive | 0.60 | no_test, broad_except, no_docs |
| `pr-19701/` | [#19701](https://github.com/connectlyai/connectly-backend/pull/19701) | feat(knowledge): QuestionAnswerEngine v2 (9k+ lines) | sensitive | 1.00 | no_test, broad_except, secret_like, no_docs |

Each directory contains:

- `brief.json` — the briefing document (read this first)
- `graph.json` — full impact graph (the deep store for citations)
- `manifest.snapshot.yaml` — copy of the `.review/types.yaml` used
- `CONTRACT.md` — auto-rendered consumer contract (regenerated per run)

Schemas live at `prex/schemas/dist/`:
- `brief.schema.json`, `graph.schema.json`, `shared.schema.json`, `combined.schema.json`

## Highlights from the four PRs

**#19858 — CSAT filtering.** Top-ranked plan step explicitly identifies the
hidden coupling: `EvaluatedSessionsFilter` is silently reused by the Export
endpoint via `service_pb2_grpc.AgentEvaluationServiceServicer.ExportEvaluatedSessions`.
The `impact` field for that step quotes the actual blast-radius numbers.

**#19872 — per-persona RPCs.** 14 risk signals across 10 changed symbols.
LLM prose labels each new RPC method with `adds_capability`. The
`secret_like_string_added` advisory fires on a long opaque token in the
generated stub — likely a false positive worth tightening.

**#19654 — OTEL instrumentation.** `aws_lambda_instrumentor` resolves to
seven distinct lambda apps as callers — pure blast-radius signal. `broad_except_added`
correctly flags new error handlers.

**#19701 — QA engine v2 (9,752 lines).** Risk score caps at 1.0. 91 changed
symbols; the LLM disambiguator drops 15 boto3 method-name collisions before
the brief is built. Plan capped at 7 steps with diversity (no two from the
same Symbol).

## Reproducing

```bash
prex review https://github.com/connectlyai/connectly-backend/pull/19858 \
  --out-dir examples/outputs/pr-19858 \
  --llm-summarise
```

Set `VERTEXAI_PROJECT` and `VERTEXAI_LOCATION` (defaults: `prex-hackathon`,
`us-central1`) and run `gcloud auth application-default login` once.
