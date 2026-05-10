# Example outputs

Real `prex review` artifacts for the canonical demo PR
[connectlyai/connectly-backend#19858](https://github.com/connectlyai/connectly-backend/pull/19858),
captured for downstream consumers (generative-UI hosts, dashboards, automated
reviewers) to inspect without running the tool first.

The run used `--llm-summarise` so every prose field is filled. Without
`--llm-summarise`, the deterministic fields are identical and prose fields
(`headline`, `one_liner`, `what`/`why`/`impact`, `overview`) are `null`.

| Directory | PR | Title | risk_tier | risk_score | flags |
|---|---|---|---|---|---|
| `pr-19858/` | [#19858](https://github.com/connectlyai/connectly-backend/pull/19858) | feat(agent-evaluation): CSAT score filtering | sensitive | 0.75 | no_test, no_docs |

Inside each PR directory:

- `brief.json` — the briefing document (read this first)
- `graph.json` — full impact graph (the deep store for citations)
- `manifest.snapshot.yaml` — copy of the `.review/types.yaml` used
- `CONTRACT.md` — auto-rendered consumer contract (regenerated per run)

Schemas live at `prex/schemas/dist/`:
- `brief.schema.json`, `graph.schema.json`, `shared.schema.json`, `combined.schema.json`

## Highlight

**#19858 — CSAT filtering.** Top-ranked plan step explicitly identifies the
hidden coupling: `EvaluatedSessionsFilter` is silently reused by the Export
endpoint via `service_pb2_grpc.AgentEvaluationServiceServicer.ExportEvaluatedSessions`.
The `impact` field for that step quotes the actual blast-radius numbers.

## Reproducing

```bash
.venv/bin/python -m prex.cli review \
  https://github.com/connectlyai/connectly-backend/pull/19858 \
  --out-dir examples/outputs/pr-19858 \
  --llm-summarise \
  --no-serve
```
