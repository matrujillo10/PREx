# PREx — PR Experience

PR review reimagined for the AI-heavy code era. One CLI command parses any GitHub pull request, builds a typed code graph + a generative-UI briefing, and opens an inline-Copilot review surface in your browser.

```
$ prex review https://github.com/connectlyai/connectly-backend/pull/19858
PR: connectlyai/connectly-backend#19858 — feat(agent-evaluation): add CSAT score filtering …
Wrote output/pr-19858/graph.json and output/pr-19858/brief.json
  changed symbols: 6  caller edges: 5  external refs: 2  risk signals: 3  plan steps: 7
  pr_type: feat  risk_tier: sensitive  risk_score: 0.75

  ↗ open http://127.0.0.1:54123/  (Ctrl+C to stop)
```

Browser opens. You see:

- **Hero** — risk badge, blast radius, advisory flags, change-density treemap.
- **Plan** — ranked reading order with What / Why / Impact per step.
- **Diff** — file tabs + hunks with intent + risk-signal overlays.
- **Checklist** — manifest-driven items grouped by status (failed first).
- **Citation drawer** — every prose claim is clickable; resolves to a graph node, edge, or `file:line`.
- **Copilot** — inline chat (Anthropic Claude). Streams diagrams (treemap / coupling map / class diff / blast radius / data flow chain / sequence) instead of walls of text.

## Install

```bash
git clone git@github.com:matrujillo10/PREx.git
cd PREx

# Python toolchain (parser, server, agent)
python3 -m venv .venv
.venv/bin/pip install -e .

# Anthropic key for the chat agent + brief LLM enrichment
cp .env.example .env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
```

The UI bundle is **pre-built and committed** under `prex/_ui_dist/`. You don't need Node/npm to run PREx — only to develop the UI.

GitHub access uses the `gh` CLI; sign in once with `gh auth login`.

## Usage

```bash
# Parse + serve UI + open browser
prex review <PR-URL>

# Without auto-open + pinned port
prex review <PR-URL> --no-open --port 8765

# Fill prose fields (headline, plan W/W/I, hunk one-liners) via Anthropic
prex review <PR-URL> --llm-summarise

# Disambiguate ambiguous cross-ref edges (Vertex AI, optional)
prex review <PR-URL> --llm-enrich

# Skip the server entirely; just write artifacts
prex review <PR-URL> --no-serve

# Run via module if `prex` isn't on PATH
.venv/bin/python -m prex.cli review <PR-URL>
```

Per-run output lives at `output/pr-<number>/`:

| File | Purpose | Schema |
|---|---|---|
| `brief.json` | Briefing for the host LLM (read this first) | `prex/schemas/dist/brief.schema.json` |
| `graph.json` | Full impact graph (deep store for citations) | `prex/schemas/dist/graph.schema.json` |
| `manifest.snapshot.yaml` | Resolved `.review/types.yaml` used | (YAML) |
| `CONTRACT.md` | Auto-rendered consumer contract | (Markdown) |

## Architecture

```
                          ┌──────────────────────────┐
   GitHub PR (gh CLI) ──> │  parse_pr (Python)       │
                          │   tree-sitter symbols    │
                          │   diff overlay           │
                          │   cross-ref resolver     │
                          │   manifest predicates    │
                          │   optional LLM enrich    │
                          └────────┬─────────────────┘
                                   │
                                   ▼
                         output/pr-<n>/{graph,brief}.json
                                   │
            ┌──────────────────────┼──────────────────────────┐
            ▼                      ▼                          ▼
   GET /api/graph         GET /api/brief             POST /api/chat (SSE)
                                                              │
                                                              ▼
                                                   prex/agent.py
                                                   Anthropic Messages API
                                                   (text deltas + tool_use)
                                                              │
                                                              ▼
                                                  UI renders six A2GUI
                                                  diagrams inline
```

### Python package (`prex/`)

| Module | Job |
|---|---|
| `prex/cli.py` | `prex review` — parse → write artifacts → start server → open browser |
| `prex/server.py` | stdlib `http.server`; serves the SPA + `/api/{brief,graph,chat}` |
| `prex/agent.py` | Anthropic streaming + 6 A2GUI tool definitions |
| `prex/parser/` | PR resolution, tree-sitter, diff overlay, cross-refs, brief builder |
| `prex/manifest/` | `.review/types.yaml` reader + 8 generic predicates + auto-renders `CONTRACT.md` |
| `prex/schemas/` | Pydantic v2 source of truth (`_shared`, `graph`, `brief`) + derived JSON Schemas in `dist/` |

### Frontend (`prex-ui/`)

| Path | Job |
|---|---|
| `src/App.tsx` | Hash router — Surface A `/`, Surface B `/step/:rank` |
| `src/api/{client,types}.ts` | Fetch brief/graph; mirror Pydantic types |
| `src/state/store.ts` | Zustand: selected step, drawer, active hunk, chat scope |
| `src/layout/{AppFrame,CitationDrawer}.tsx` | Frame chrome + Surface C drawer |
| `src/surfaces/{Review,Step}Surface.tsx` | The two main pages |
| `src/components/{Hero,PlanColumn,DiffColumn,ChecklistColumn,HunkBlock,CitationLink,ChatShell}.tsx` | Region components |
| `src/a2gui/` | 6 diagram components + Zod schemas + (`registerTools.tsx` for future CopilotKit handoff) |

Tokens (`src/tokens.css`) are copied verbatim from the design handoff. The single terracotta accent is reserved for risk indicators only.

## Outputs the chat agent can emit

Six diagrams, each a typed React component bound to a Claude tool definition:

| Tool | Use case |
|---|---|
| `render_treemap` | "where is the change densest" |
| `render_coupling_map` | "anything sneaky" / "hidden coupling" |
| `render_class_diff` | "what changed in this class" |
| `render_blast_radius` | "who is affected" |
| `render_data_flow_chain` | "how does X flow through" |
| `render_sequence` | "show the SQL path" |

The agent system prompt biases toward diagrams over prose; replies are typically a 1–3-sentence caption plus one or more diagrams.

## Layout of the repo

```
PREx/
├── prex/                # Python: parser, schemas, manifest, server, agent, CLI
│   ├── _ui_dist/        # Pre-built UI bundle (committed; ships in pip wheel)
│   ├── schemas/dist/    # Generated JSON Schemas
│   └── ...
├── prex-ui/             # Vite + React + TS source
├── examples/
│   ├── .review/types.yaml         # Bundled fallback manifest
│   └── outputs/pr-19{654,701,858,872}/   # Real outputs from 4 validation PRs
├── docs/wireframe-prompt.md       # Brief that drove the design handoff
├── context.md / decisions.md / research.md  # Project memory
├── pyproject.toml / .env.example
└── README.md            # this file
```

## Validation PRs

Run any of these to see the full pipeline against real code:

| PR | Title | Why interesting |
|---|---|---|
| [#19858](https://github.com/connectlyai/connectly-backend/pull/19858) | feat(agent-evaluation): CSAT filtering | Smallest; surfaces hidden Export-endpoint coupling |
| [#19872](https://github.com/connectlyai/connectly-backend/pull/19872) | feat[talk]: per-persona RPCs | Generated-stub forest; tests how the LLM disambiguator handles it |
| [#19654](https://github.com/connectlyai/connectly-backend/pull/19654) | feat[team-agents]: OTEL metrics | Real blast radius — one symbol affects 7 lambdas |
| [#19701](https://github.com/connectlyai/connectly-backend/pull/19701) | feat(knowledge): QA engine v2 (9k+ lines) | Stress test; 91 changed symbols, boto3 collisions |

## Developing the UI

```bash
cd prex-ui
npm install
npm run dev        # Vite on :5173, proxies /api to :8765 (run `prex review --port 8765 --no-open` in another terminal)
npm run build      # writes ../prex/_ui_dist/ — commit alongside source changes
```

`prex/_ui_dist/` is committed deliberately so `pip install -e .` is enough to run the UI without any Node tooling.

## What ships next

- Wire CopilotKit's runtime so `useFrontendTool` registrations in `prex-ui/src/a2gui/registerTools.tsx` become the call path (today the chat goes direct from `ChatShell.tsx` to `/api/chat`).
- Stream brief.json incrementally so first paint shows the hero before plan steps land.
- Type-conditional checklists (`feat`/`fix`/`chore` predicate sets) on top of today's generic ones.
- Cross-repo edges so a backend PR can flag dependent frontend repos.

## License

Hackathon code; no license declared yet. Don't ship to prod without sorting that.
