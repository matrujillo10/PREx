# Analysis: impact_summary

Goal: tell the reviewer **what this node's change actually affects**, in
the smallest words possible, grounded in the graph.

## Procedure

1. **Classify the change.** Restate `kind` + `change_state` in one
   sentence using the node's name/path/qualified_name.
2. **Direct effects (downstream).** From the neighbors, list outgoing
   edges where the *target* is affected by this node. Group by edge
   type (`calls`, `references`, `defines`, `touches`, `contains`,
   `imports`, `covers`, `external`).
3. **Triggers (upstream).** From the neighbors, list incoming edges —
   what depends on this node and may need to adapt.
4. **Blast radius hint.** One short line: is this contained
   (single-file private symbol), local (module-internal), or
   cross-cutting (public symbol with cross-module callers /
   external_ref)? Use the `public` flag and external_ref neighbors.
5. **Render.** If there are 3+ affected neighbors, call
   `render_impact_table` with rows
   `{ node_id, relation: "downstream"|"upstream", edge_type, confidence }`.
   If a hunk patch is the central artifact, call `render_code_diff`
   with the hunk's `patch` and the file's `path`.
6. **Open questions.** If a neighbor has `confidence: "ambiguous"` or
   `"llm_inferred"`, flag it explicitly — its impact may be
   misattributed. If `read_source` would clarify, call it; otherwise
   list what's unverified.

## Style

- Lead with the classification sentence. Keep total prose under ~150
  words; let the rendered table carry the breadth.
- Never list `unchanged` neighbors unless they're load-bearing for the
  blast-radius judgment.
