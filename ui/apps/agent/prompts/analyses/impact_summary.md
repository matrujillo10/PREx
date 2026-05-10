# Analysis: impact_summary

Tell the reviewer what this node's change actually affects. Compact.

## Required response shape

**Call exactly one render tool per response.** Pick the single best
fit by this ladder (top-to-bottom; first match wins):

1. **Ungrounded / ambiguous** — neighbors with `confidence` of
   `ambiguous` or `llm_inferred`, or you couldn't ground the answer
   from context + at most one `read_source` call →
   `render_open_questions`.
2. **Hunk node, patch is the story** → `render_code_diff` with the
   node's `path` and `patch`.
3. **≥3 meaningful neighbors AND edge_type / confidence matters** →
   `render_impact_table`.
4. **1–6 neighbors, just need to name them** → `render_neighbors`
   (split by upstream/downstream).
5. **Otherwise (clean / contained / no neighbors of note)** →
   `render_verdict` only.

Filter out `unchanged` neighbors unless load-bearing for the
blast-radius judgment.

## Prose

**≤ 25 words**, one sentence framing the rendered tool. No tables,
bullets, fenced code, or markdown headers in prose. If you'd need
more words, you picked the wrong tool — re-pick.

## Backend tool

Call `read_source` at most once per turn, and only when the patch +
neighbors are insufficient to answer.
