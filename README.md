# PREx — PR review reimagined for the AI-heavy code era

> One CLI. One PR URL. A live, evidence-bearing review surface — with an inline Copilot that draws diagrams instead of typing walls of text.

```bash
prex review https://github.com/connectlyai/connectly-backend/pull/19858
```

That's it. Browser opens. You see the diff with semantic overlays, and a chat that emits **typed visualisations** — coupling maps, blast-radius graphs, class diffs, sequence diagrams — drawn in real time as you ask questions.

---

## Why this exists

In 2026 most code is AI-written. Review didn't scale to match. The numbers from DORA / CodeRabbit / Anthropic internal data:

- **Review time +441%.** Per-PR human review burden quadrupled.
- **31% of PRs merge with zero review.** Rubber-stamping is the new default.
- **Incidents per PR +242%.** Defect cost tripled.
- **AI PRs ship 75% more logic errors and 2.74× more security issues** than human-written ones.

Reviewers are the bottleneck and they're drowning. PREx is a reviewer-side product: it turns "12 files of unified diff" into a guided, citable, visual reading experience anchored in the actual code graph.

---

## What you get when you run it

A localhost web app with two halves:

### 1. The diff column — but with semantics
Every hunk carries:
- **Intent label** (`adds_capability`, `weakens_test`, `removes_dead`, …) decided by an LLM that read the patch.
- **Risk-signal chips** (`sql_in_changed_lines`, `removes_assertion`, `broad_except`, `secret_like_string`, …) detected deterministically from AST + diff.
- **One-liner** ("Adds `min_csat_score` field to `EvaluatedSessionsFilter` proto message") so you don't re-derive what changed on every read.
- **Cite-back affordances** that resolve to graph node ids, edge ids, or file:line ranges.

### 2. The Copilot — diagrams, not paragraphs
Ask it anything. It picks the right *shape* and fills it with real graph data. Eight diagram types, all typed, all bound to live data:

| Tool | When the agent picks it |
|---|---|
| `render_review_brief` | "give me the brief" / "what is this PR" |
| `render_review_plan` | "where do I start" / "show the plan" |
| `render_checklist` | "anything failed" / "what's missing" |
| `render_treemap` | "where is the change densest" |
| `render_coupling_map` | "anything sneaky" / "hidden coupling" |
| `render_class_diff` | "what changed in this class" |
| `render_blast_radius` | "who is affected by this" |
| `render_data_flow_chain` | "how does X flow through" |
| `render_sequence` | "show the SQL path" / "trace the calls" |

The system prompt biases hard toward diagrams and ≤30-word captions. No "let me walk you through this in three paragraphs" replies.

---

## The unfair advantages

### Hidden couplings nobody else surfaces
PREx parses the whole repo, not just the diff. On the canonical demo PR ([connectlyai/connectly-backend#19858](https://github.com/connectlyai/connectly-backend/pull/19858)) it instantly catches that `EvaluatedSessionsFilter` is silently reused by an unrelated `ExportEvaluatedSessions` endpoint — adding a CSAT filter to one extends the other invisibly. The PR description never mentions it. Click "anything sneaky?" and the chat draws a coupling map with the implicit edge marked dashed-terracotta and labelled `LLM-inferred`.

### Real blast radius, not vibes
The graph counts callers. "This change touches 47 callers across 3 modules including the public RPC surface" is a number the UI shows on the hero card and the agent quotes when relevant. PR [#19654](https://github.com/connectlyai/connectly-backend/pull/19654) has 7 distinct lambdas downstream of one telemetry function — the blast-radius diagram makes it obvious in one glance.

### Faithful by construction
Every prose claim PREx renders carries a `cites` list. Click any sentence → a side drawer opens with the underlying evidence (a graph node, an edge, a `file:line` range, an external URL). LLM-derived facts get a visibly distinct chip. The reviewer never has to take an AI claim on faith.

### Generative UI, real components
The chat doesn't paste markdown. The agent emits *typed tool calls* — Anthropic Claude with structured tool-use, mapped 1:1 to React components. Every diagram is a real component bound to data, not a screenshot. Inputs are validated with Zod schemas; bad shapes can't render.

### Pre-flight risk signals (no LLM)
11 AST-derived risk signals fire deterministically per hunk:
`auth_or_authz_touched · sql_in_changed_lines · external_io · removes_assertion · weakens_validation · raises_swallowed · broad_except · feature_flag_added · feature_flag_removed · secret_like_string · numeric_constant_changed_in_hot_loop`

Plus 8 generic checklist predicates (`public_symbol_modified_without_test`, `external_ref_added`, `assertion_removed`, `broad_except_added`, `secret_like_string_added`, `no_doc_change_for_public_api`, `feature_flag_added`/`removed`) auto-evaluated against the manifest at `.review/types.yaml`.

---

## Try it on a real PR

Four canonical validation PRs ship with the repo. Pick any:

| PR | Why interesting |
|---|---|
| [#19858](https://github.com/connectlyai/connectly-backend/pull/19858) | **Smallest demo.** Surfaces the hidden Export-endpoint coupling. |
| [#19872](https://github.com/connectlyai/connectly-backend/pull/19872) | Generated-stub forest; LLM disambiguator earns its keep. |
| [#19654](https://github.com/connectlyai/connectly-backend/pull/19654) | Real blast radius — one symbol affects 7 lambdas. |
| [#19701](https://github.com/connectlyai/connectly-backend/pull/19701) | 9,752-line stress test. 91 changed symbols, boto3 collisions auto-resolved. |

Pre-built outputs for all four live in `examples/outputs/` so you can browse `brief.json` / `graph.json` / `CONTRACT.md` without running anything.

---

## Install

```bash
git clone git@github.com:matrujillo10/PREx.git
cd PREx
python3 -m venv .venv
.venv/bin/pip install -e .

# anthropic key for the chat agent + optional --llm-summarise
cp .env.example .env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env

# GitHub access uses the gh CLI
gh auth login
```

The UI bundle is **pre-built and committed** under `prex/_ui_dist/`. You don't need Node or npm to run PREx — only to develop the UI.

## Use

```bash
# parse + serve UI + open browser
.venv/bin/python -m prex.cli review <PR-URL>

# fill prose fields (headline, plan What/Why/Impact, hunk one-liners) before the UI loads
.venv/bin/python -m prex.cli review <PR-URL> --llm-summarise

# pin port / skip auto-open
.venv/bin/python -m prex.cli review <PR-URL> --port 8765 --no-open

# write artifacts only, don't start the server
.venv/bin/python -m prex.cli review <PR-URL> --no-serve
```

Each run drops four artifacts under `output/pr-<num>/`:

| File | Read it as |
|---|---|
| `brief.json` | The briefing for the host LLM. Read this first. |
| `graph.json` | The full code graph (deep store for citations). |
| `manifest.snapshot.yaml` | The `.review/types.yaml` rules used. |
| `CONTRACT.md` | Auto-rendered consumer contract (regenerated every run). |

JSON Schemas for both top-level docs live at `prex/schemas/dist/{brief,graph,combined}.schema.json`.

---

## Architecture, briefly

```
gh pr view ──┐
             │   ┌──────────────────────────┐
             ├──▶│  parse_pr   (Python)     │
             │   │   tree-sitter symbols    │
             │   │   diff overlay           │
             │   │   cross-ref resolver     │
             │   │   manifest predicates    │
             │   │   optional LLM enrich    │
             │   └────────┬─────────────────┘
             │            │
             ▼            ▼
        graph.json    brief.json
                          │
        ┌─────────────────┼──────────────────────┐
        ▼                 ▼                      ▼
   GET /api/graph    GET /api/brief       POST /api/chat (SSE)
                                                   │
                                                   ▼
                                          prex/agent.py
                                          Anthropic Messages API
                                          text deltas + tool_use
                                                   │
                                                   ▼
                                          UI renders typed
                                          A2GUI components
```

- **Python package** (`prex/`) — parser + schemas + manifest + server + agent + CLI. Everything ships in the pip wheel including the pre-built UI bundle.
- **Server** is **stdlib `http.server`**. Three routes: `GET /api/{brief,graph}`, `POST /api/chat` (SSE).
- **Agent** uses the Anthropic Python SDK directly — Messages API with streaming + tool use. 9 tools defined; system prompt biases toward visual replies.
- **Frontend** (`prex-ui/`) — Vite + React + TypeScript + Zustand. CSS Modules + a single `tokens.css` from the design system. The terracotta accent is reserved exclusively for risk indicators.
- **Diagrams** (`prex-ui/src/a2gui/`) — typed React components, raw SVG, Zod input schemas. Tool definitions on the agent side mirror the Zod schemas exactly so structured output can never mis-render.

---

## Layout of the repo

```
PREx/
├── prex/                # Python: parser, schemas, manifest, server, agent, CLI
│   ├── _ui_dist/        # Pre-built UI bundle (committed; ships in wheel)
│   ├── schemas/dist/    # Generated JSON Schemas
│   └── ...
├── prex-ui/             # Vite + React + TS source
├── examples/
│   ├── .review/types.yaml         # Bundled fallback manifest
│   └── outputs/pr-19{654,701,858,872}/   # Real outputs from 4 validation PRs
├── docs/wireframe-prompt.md       # Brief that drove the design handoff
├── context.md / decisions.md / research.md  # Project memory
└── README.md            # this file
```

---

## What ships next

- Streaming `brief.json` so the UI paints the hero before the plan lands.
- Type-conditional checklists (`feat`/`fix`/`chore`-specific predicate sets) on top of today's generic ones.
- Cross-repo edges so a backend PR can flag dependent frontend repos.
- CopilotKit runtime swap so the registered `useFrontendTool` definitions take over the chat path (today PREx talks to Anthropic directly via SSE).

---

## Credits

Designed against four real PRs in `connectlyai/connectly-backend` (with permission). Hi-fi design handoff in `docs/wireframe-prompt.md`. Built in a hackathon.

## License

MIT — see [LICENSE](LICENSE).
