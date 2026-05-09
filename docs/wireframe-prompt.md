# Wireframe brief — PREx PR-review surface (peer reviewer, low-fi)

> Paste this into Claude Design (or any wireframing tool that consumes a brief). It is fully self-contained: all schema, persona, layout, and concrete data details below are necessary to produce three deliberately constrained wireframes.

---

## 1. Project context

PREx ("PR Experience") is a tool that, for any GitHub pull request, produces two structured artifacts:

- `graph.json` — a directed multigraph of the PR (modules → files → symbols → hunks → external refs, plus typed edges: contains / defines / touches / calls / references / imports / covers / external).
- `brief.json` — a *briefing layer* designed to feed a generative-UI host (a2ui-style: the host is an LLM that emits component descriptions over a pre-approved catalog from the brief).

A reviewer never sees these JSON files. The host LLM reads `brief.json`, follows citations into `graph.json` when needed, and emits a UI in real time. **You are designing the wireframe of that UI**, given the data PREx now produces. The host LLM's job at runtime is to *route fields to components*, not to invent them — so every region of the wireframe must trace back to a named field or list in the brief.

The wider problem PREx solves: in 2026 most code is AI-written, and human review is the bottleneck. PREx turns the unified diff into a navigable, evidence-bearing briefing so a reviewer can read with priorities, see blast radius, and verify claims via citations.

## 2. Persona — peer reviewer (only)

**Who:** a senior engineer reviewing code authored by a teammate (often AI-assisted). They did *not* write the code, they have *zero* familiarity with the change, and they may have ~7 minutes for this PR before context-switching. Their failure modes are: rubber-stamping plausible code, missing blast-radius issues, and not noticing what's *not* changed (e.g. tests not updated, docs not updated).

**What they need:**
- A one-glance verdict: how risky is this PR, what type, what's the headline.
- A guided reading order rather than 12 files of unified diff.
- For each region: *what changed*, *why* (author intent), *how it impacts* the rest of the codebase.
- Visible *blast radius*: who else is affected.
- Visible *gaps*: tests not modified, docs not changed, hidden couplings.
- The ability to verify any claim by clicking through to evidence (a hunk, a node, a file:line).

**What they do NOT need (defer to other surfaces):**
- The author's pre-PR self-review chrome (different persona, different layout).
- A way to reply to comments. The wireframe shows the *reading* experience only.

## 3. The data you are wireframing

### 3.1 Top-level shape (the brief)

```
Brief
├── pr             — PRMetadata (title, body, author, base/head sha, additions/deletions)
├── review         — ReviewBrief (the hero block)
├── plan           — ReviewPlan (overview + ranked steps with What/Why/Impact)
├── hunks[]        — HunkInsight per hunk (one_liner, intent, risk_signals, cites)
├── checklist[]    — ChecklistBinding (one or more groups of ChecklistItem with auto_status)
├── graph_ref      — string path to the sibling graph.json
└── diagnostics[]  — non-fatal warnings; render only level >= warn
```

### 3.2 Key sub-models the wireframe must surface

```
ReviewBrief
├── pr_type             "feat" | "fix" | "chore" | "unknown"
├── pr_type_confidence  0..1
├── risk_tier           "trivial" | "standard" | "sensitive"
├── risk_score          0..1
├── blast_radius        { caller_files, modules_crossed, public_symbols_modified, external_refs_added }
├── novelty             { new_files, new_symbols, new_external_refs }
├── headline            ≤140 chars (LLM-filled when available, else null)
├── advisory_flags[]    e.g. "no_test_coverage_changed", "no_docs_for_public_api",
                              "secret_like_string_added", "broad_except_added",
                              "scope_creep_5plus_areas", "test_lines_removed",
                              "generated_files_only", "removes_assertion"
└── cites[]             at least one Citation per prose field

ReviewStep (one of N≤7 items in plan.steps)
├── rank                1-indexed; lower = read first
├── target              graph node id (Symbol or Hunk)
├── title               ≤60 chars
├── what                ≤2 sentences. Objective change in plain language.
├── why                 ≤2 sentences. Tied to PR title/body or pr_type.
├── impact              ≤2 sentences. Quotes blast_radius numbers or names a downstream caller.
├── estimated_minutes   1..15
├── risk_signals[]      AST-derived markers (see §3.3)
├── related_targets[]   secondary node ids the reviewer should glance at
└── cites[]             at least one per prose field

HunkInsight (one per Hunk node)
├── hunk_id
├── one_liner           ≤80 chars; LLM-filled
├── intent              "adds_capability" | "fixes_bug" | "renames" | "extracts" | "inlines" |
                        "reorders" | "tightens_types" | "weakens_test" | "adds_test" |
                        "removes_dead" | "comments_only" | "style_only" | "unknown"
├── risk_signals[]
├── affects_public_symbol_ids[]
└── cites[]

ChecklistItem
├── id, text, required
├── targets[]           hunk_ids or symbol_ids the item applies to
├── auto_status         "pass" | "fail" | "unknown"
└── auto_evidence       Citation

Citation
├── kind        "node" | "edge" | "file_line" | "external_doc"
├── ref         e.g. "symbol:pkg.mod.Foo" / "calls:src->-tgt" /
                "path/to/file.py#L12-L18" / a URL
├── derivation  "ast" | "diff" | "crossref_text" | "llm" | "manifest" | "heuristic"
├── score       0..1
└── excerpt     ≤120 chars literal quote (optional)
```

### 3.3 Risk signals (closed list; render as a chip per signal)

`auth_or_authz_touched`, `sql_in_changed_lines`, `external_io`,
`removes_assertion`, `weakens_validation`, `raises_swallowed`,
`broad_except`, `feature_flag_added`, `feature_flag_removed`,
`secret_like_string`, `numeric_constant_changed_in_hot_loop`.

Each chip has a short label ("SQL", "broad except", "feature flag added") and links to whatever hunk(s) it fired on.

## 4. Concrete anchor data — PR #19858 (CSAT filtering)

The wireframes must use this exact data. It is not illustrative; it is the canonical example.

### 4.1 PR metadata
- **Title:** `feat(agent-evaluation): add CSAT score filtering and mapping to evaluated sessions`
- **Author:** `theguriev` (Eugen Guriev)
- **Branch:** `eugen/pl-3019-improve-admin-conversation-review-workflow` → `main`
- **+121 / −15** across 8 files (4 are proto/generated, collapsed; 4 real Python files: `models.py`, `mappers.py`, `controller.py`, `repository.py`).

### 4.2 ReviewBrief
- `pr_type = "feat"` (confidence 0.95)
- `risk_tier = "sensitive"`, `risk_score = 0.75`
- `blast_radius = { caller_files: 3, modules_crossed: 3, public_symbols_modified: 5, external_refs_added: 2 }`
- `novelty = { new_files: 0, new_symbols: 0, new_external_refs: 2 }`
- `advisory_flags = ["no_test_coverage_changed", "no_docs_for_public_api"]`
- `headline = "Adds CSAT score filtering and mapping to agent evaluation, modifying 5 public symbols in a sensitive change without new tests or docs."`

### 4.3 Plan steps (target + risk_signals; titles/prose left blank when LLM call fails — design must handle both states)

| rank | target | risk_signals |
|---|---|---|
| 1 | `models.EvaluatedSessionsFilter` (class) | — |
| 2 | `repository.AgentEvaluationRepository.query_evaluated_sessions` (method) | `sql_in_changed_lines` |
| 3 | hunk in `repository/repository.py` line ~655 | `sql_in_changed_lines` |
| 4 | hunk in `repository/repository.py` line ~706 | `sql_in_changed_lines` |
| 5 | hunk in `repository/repository.py` line ~770 | `sql_in_changed_lines` |
| 6 | `controller.AgentEvaluationController.query_evaluated_sessions` (method) | — |
| 7 | `mappers.map_query_evaluated_sessions_response` (function) | — |

### 4.4 Per-hunk one_liners (sample)
- *"Adds `min_csat_score` field to `EvaluatedSessionsFilter` proto message."* (intent=adds_capability)
- *"Adds `failed_eval_names` and `csat_score` to the evaluated sessions query."* (intent=adds_capability, risk_signals=[`sql_in_changed_lines`])
- *"Maps `csat_score` from internal model to DTO."* (intent=adds_capability)

### 4.5 Checklist (8 items; 3 fail, 3 pass, 2 unknown)
- ✗ **public_symbol_modified_without_test** — 5 targets — required `false`
- ✗ **external_ref_added** — 2 targets (`ticket_associations`, `ticket_metrics`) — required `false`
- ✓ assertion_removed
- ✓ broad_except_added
- ✓ secret_like_string_added
- ✗ **no_doc_change_for_public_api** — 5 targets — required `false`
- ? feature_flag_added
- ? feature_flag_removed

### 4.6 The hidden coupling that must be visible somewhere
Top-ranked plan step `EvaluatedSessionsFilter` is *also* used by an unrelated Export endpoint (`service_pb2_grpc.AgentEvaluationServiceServicer.ExportEvaluatedSessions`) declared in `service.proto`. Adding `min_csat_score` to the filter implicitly adds CSAT filtering to Export. This is the single most consequential reviewer signal in this PR; it must appear in either the Step 1 `impact` field or the blast-radius region.

## 5. Surfaces to wireframe

### Surface A — PR review screen (default landing)
The first thing the reviewer sees after opening the PR.

**Required regions, in roughly this layout priority:**
1. **Hero band** — `headline`, `pr_type` chip, `risk_tier` badge (color-coded *only* by tier), `risk_score` as a slim 0..1 bar, `blast_radius` as 4 mini-stats, `advisory_flags` as a row of chips. Generated-files indicator if all changed files are generated.
2. **Suggested reading plan** — `plan.overview` as a sentence + a scrollable column of 7 step cards (rank, title, ~6 lines per card showing What/Why/Impact, risk_signal chips, estimated_minutes). One step is "selected" by default — the rank=1 step. Selecting a step changes Surface B (focus mode) below.
3. **Diff column** — placeholder for the unified diff with HunkInsight overlays: a compact one_liner + intent label appears above each hunk; risk_signal chips render to the right. The current step's hunk is auto-scrolled into view. Diff itself is the standard +/- columns; do not redesign it.
4. **Checklist sidebar** — 8 items grouped by status (failed first), each row showing icon + text + targets count + an "evidence" link that opens the citation drawer (Surface C).
5. **Persistent footer** — small status: *"PREx 0.2.0 · graph at <head_sha> · 7 plan steps · 226 graph nodes · LLM enrichment: on"*.

The host LLM (a2ui consumer) maps each region to its native component group. Your wireframe's only job is to show region positions, what fields drive each region, and which interactions move data between them. **No real styling.**

### Surface B — Per-step focus mode
Triggered when the reviewer selects a `ReviewStep` from Surface A. Replaces the diff column area (or slides over it).

**Required regions:**
1. **Step header** — rank, title, target's qualified_name, risk_signal chips, estimated_minutes.
2. **What / Why / Impact** — three labeled text blocks (≤2 sentences each). Each block has an evidence affordance opening the citation drawer.
3. **Hunk(s) under this step** — the actual diff for the step's `target` (if target is a Symbol, all defines/touches hunks for it; if target is a Hunk, that hunk).
4. **1-hop callers** — list of caller stubs from `graph.json` (qualified name + file:line). Each caller is clickable to peek at the calling line.
5. **Related targets** — small list referencing `step.related_targets` ids.
6. **Step navigation** — prev/next + "back to plan" button.

### Surface C — Citation drawer
Slides in from the right (or a modal) when the reviewer clicks any cited prose anywhere on Surfaces A or B.

**Required regions:**
1. **Drawer header** — the prose snippet they clicked, in italics, plus the prose source ("plan step 1 / impact").
2. **Citation list** — for each Citation object: `kind` icon, `ref` (rendered as the right kind of link), `derivation` chip ("ast" / "diff" / "llm" / "manifest" / "heuristic"), `score` as a tiny bar, optional `excerpt` quoted underneath.
3. **Targeted preview** — the currently-selected citation rendered in place: file:line excerpt, node tile (qualified name + file_id), or external link.
4. **Trust footer** — "Open node in graph viewer" link, a copy-ref-id button.

The drawer must visibly distinguish `derivation = "llm"` citations from deterministic ones; the user should never confuse an inferred claim for a static fact.

## 6. Style spec — low-fi greyscale

- Greyscale only. The single permitted colour deviation is one accent (any single hue) used solely for *risk* indicators (the `risk_tier` badge, failed checklist items, and added external-ref chips). Everything else: white, four shades of grey, black.
- Boxes and labels. No real typography decisions. Use placeholder text like `[headline ≤140 chars]` where field-driven, not real prose.
- Components should be schematic boxes with clear field annotations: e.g.
  ```
  ┌────────────────────────────────────────┐
  │ HERO  [risk:sensitive] [type:feat]     │
  │ {brief.review.headline}                │
  │ blast: caller_files=3  modules=3 …     │
  └────────────────────────────────────────┘
  ```
- Annotate every box with the field path that populates it, e.g. `← brief.plan.steps[i].what`. The host LLM at runtime needs an unambiguous mapping.
- Show two states for fields the LLM may or may not have filled: with prose vs. without prose (an empty-state placeholder like `(LLM prose not generated)`).
- Show one *citation-clicked* state so the drawer is shown active.

## 7. Citation + faithfulness rules (non-negotiable)

- Every prose field on the wireframe must have a small `↳` icon or affordance indicating its citations are clickable.
- Any region whose data has `derivation == "llm"` must wear a small "AI inferred" tag. Same for any caller edge from the graph that is `derivation == "llm"`.
- Diagnostics with `level == "info"` are plumbing — never render them.

## 8. a2ui-aware constraints

a2ui-style hosts emit component descriptions over a pre-approved catalog. Bias the wireframe toward:

- **Flat, named regions** that map to a component group (Hero, Plan, Step, Diff, Checklist, Drawer). Do not use deep nested layouts.
- **Streaming friendliness:** the layout must remain readable when only the first few blocks have arrived. Show one wireframe variant where only `Hero` + `plan.overview` are present and the rest is a skeleton state.

## 9. Deliverables

For each of the three surfaces (A: PR review, B: Step focus, C: Citation drawer):

1. One desktop wireframe (target ~1280px wide) in low-fi greyscale.
2. A short legend mapping every box to the brief field that drives it.
3. For Surface A: an additional skeleton variant showing the "first paint" state (Hero + overview only).
4. A single side-note paragraph per surface explaining one design decision you made and why (e.g. "I placed the checklist on the right rather than the left because failed items must remain visible when the reviewer scrolls the diff").

That is the entire scope. Use only the data shapes above; do not invent new fields.

## 10. Source files (reference)

- `examples/outputs/pr-19858/brief.json` — the actual brief for the anchor PR.
- `examples/outputs/pr-19858/graph.json` — the sibling graph the citations resolve into.
- `prex/schemas/dist/brief.schema.json` and `graph.schema.json` — formal JSON Schemas.
- `examples/outputs/pr-19858/CONTRACT.md` — the auto-generated consumer contract; section 5 there describes the citation discipline you must honour in the UI.
