"""LLM enrichment hook.

Off unless the orchestrator passes `enabled=True` (driven by `--llm-enrich` CLI flag).

Backend: litellm → Vertex AI (Gemini). Default model `vertex_ai/gemini-2.5-flash`.
Auth: GCP Application Default Credentials (run `gcloud auth application-default login`).
Project + region from env: `VERTEXAI_PROJECT`, `VERTEXAI_LOCATION` (default `us-central1`).

Triggers implemented in v0.1:
    - `disambiguate_method_callers`: for AMBIGUOUS cross-ref edges produced by
      text search, ask the LLM to read 8 lines around each call site and
      decide whether the call resolves to the changed target or to a same-named
      symbol elsewhere (e.g. boto3 `s3.get_object()` colliding with a new
      `MyClass.get_object` method). Output drives edge filtering: keep + mark
      LLM_INFERRED, drop, or keep as AMBIGUOUS.

Stubs (deferred):
    - zero-caller public symbol → framework wiring? (returns Diagnostic only)
    - generated-file detection beyond path heuristics
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from prex.schemas.graph import Confidence, Diagnostic, Edge, EdgeType


_LOG = logging.getLogger("prex.enrich")

DEFAULT_MODEL = os.environ.get("PREX_LLM_MODEL", "vertex_ai/gemini-2.5-flash")
DEFAULT_PROJECT = os.environ.get("VERTEXAI_PROJECT", "prex-hackathon")
DEFAULT_LOCATION = os.environ.get("VERTEXAI_LOCATION", "us-central1")
CONTEXT_LINES = 8  # number of surrounding lines to include per call site
MAX_BATCH = 20  # max call sites per LLM batch


@dataclass
class EnrichmentInput:
    """Bundle of repo-level context the enricher receives once per run."""
    repo: str
    framework_hints: str = ""


@dataclass
class _CallSite:
    edge_index: int  # index into the edges list, used to apply the verdict
    target_qn: str
    target_signature: Optional[str]
    other_def_sites: List[str]  # other repo def-sites for the bare name
    source_file: str
    line: int
    surrounding: str  # 8 lines around the call line


def is_available() -> bool:
    """LLM enrichment available when ADC is configured + litellm importable."""
    try:
        import litellm  # noqa: F401
    except Exception:
        return False
    return True


def _read_surrounding(repo_path: Path, rel_path: str, line: int) -> str:
    """Return ±CONTEXT_LINES lines around `line` (1-indexed) with line numbers."""
    abs_path = repo_path / rel_path
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    lines = text.splitlines()
    start = max(1, line - CONTEXT_LINES)
    end = min(len(lines), line + CONTEXT_LINES)
    out = []
    for i in range(start, end + 1):
        marker = ">>" if i == line else "  "
        out.append(f"{marker} {i:5d}  {lines[i - 1]}")
    return "\n".join(out)


def _build_prompt(target_qn: str, target_signature: Optional[str], other_sites: List[str], call_sites: List[_CallSite]) -> str:
    parts = [
        "You are reviewing static-analysis output from a code review tool.",
        "Goal: decide which call sites in a Python repo actually resolve to a specific target symbol.",
        "Text-search alone cannot disambiguate methods because two unrelated classes can share a method name (e.g. `s3.get_object` from boto3 vs a new method named `get_object`).",
        "",
        f"TARGET (the symbol whose blast radius we are mapping):",
        f"  qualified_name: {target_qn}",
        f"  signature:      {target_signature or '(unknown)'}",
        "",
    ]
    if other_sites:
        parts.append("OTHER REPO DEFINITIONS of the same bare name (any of these may be the actual receiver):")
        for s in other_sites[:10]:
            parts.append(f"  - {s}")
        if len(other_sites) > 10:
            parts.append(f"  - ... ({len(other_sites) - 10} more)")
        parts.append("")
    parts.append("CALL SITES — for each, decide if the call/reference resolves to TARGET:")
    parts.append("  T = resolves to TARGET")
    parts.append("  O = resolves to one of the other repo definitions (or stdlib/SDK like boto3/sqlalchemy)")
    parts.append("  U = unclear from this context")
    parts.append("")
    for i, cs in enumerate(call_sites, start=1):
        parts.append(f"[{i}] file: {cs.source_file}  line: {cs.line}")
        parts.append("```python")
        parts.append(cs.surrounding)
        parts.append("```")
        parts.append("")
    parts.append('Respond with ONE JSON object: {"verdicts": [{"i": 1, "v": "T", "why": "..."}, ...]}.')
    parts.append("Keep `why` to one short sentence per verdict. No prose outside JSON.")
    return "\n".join(parts)


def _extract_json(content: str) -> Optional[dict]:
    """LLMs sometimes wrap JSON in fences or prose. Pull the first {...} blob."""
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        # Strip common trailing-comma issues, retry
        cleaned = re.sub(r",\s*([\}\]])", r"\1", m.group(0))
        try:
            return json.loads(cleaned)
        except Exception:
            return None


def _call_llm(prompt: str, *, model: str, project: str, location: str) -> Optional[str]:
    """One litellm call. Returns response text or None on failure."""
    try:
        import litellm
    except Exception as e:
        _LOG.warning("litellm not available: %s", e)
        return None
    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            vertex_project=project,
            vertex_location=location,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content  # type: ignore[union-attr]
    except Exception as e:
        _LOG.warning("LLM call failed: %s", e)
        return None


def disambiguate_method_callers(
    *,
    enrichment_input: EnrichmentInput,
    repo_path: Path,
    edges: List[Edge],
    nodes_by_id: Dict[str, Any],
    target_signatures_by_id: Dict[str, str],
    same_name_other_def_sites: Dict[str, List[str]],  # bare name -> list of qualified other def names
    diagnostics: List[Diagnostic],
    model: str = DEFAULT_MODEL,
    project: str = DEFAULT_PROJECT,
    location: str = DEFAULT_LOCATION,
) -> Tuple[List[Edge], int, int, int]:
    """Filter ambiguous cross-ref edges by asking the LLM to read each call site.

    Returns (new_edges_list, kept_count, dropped_count, unsure_count).

    Edges with confidence != AMBIGUOUS pass through unchanged.
    Ambiguous edges get bucketed by target qualified_name and one batch call per
    target. Each batch resolves up to MAX_BATCH call sites.
    """
    if not is_available():
        diagnostics.append(
            Diagnostic(
                level="info",
                code="LLM_ENRICH_UNAVAILABLE",
                message="litellm not installed; skipping ambiguous-edge disambiguation.",
            )
        )
        return edges, 0, 0, 0

    # Bucket ambiguous edges by target_id (which is the changed-target node id)
    ambiguous_by_target: Dict[str, List[int]] = {}
    for idx, e in enumerate(edges):
        if e.confidence != Confidence.AMBIGUOUS:
            continue
        if e.type not in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS):
            continue
        ambiguous_by_target.setdefault(e.target_id, []).append(idx)

    if not ambiguous_by_target:
        return edges, 0, 0, 0

    new_edges: List[Edge] = list(edges)
    kept = dropped = unsure = 0

    for target_id, edge_indices in ambiguous_by_target.items():
        target_node = nodes_by_id.get(target_id)
        if target_node is None or getattr(target_node, "kind", None) != "symbol":
            continue
        target_qn = target_node.qualified_name
        target_sig = target_signatures_by_id.get(target_id)
        bare_name = target_qn.rsplit(".", 1)[-1]
        other_sites = same_name_other_def_sites.get(bare_name, [])

        # Build call sites from the edge file/line note (we lost the line info — gather from notes/source)
        # Source line wasn't carried into Edge; we need to recompute from the source_id.
        # In v0 each Edge.source_id is the enclosing symbol; the actual call line was used to make the edge id.
        # We extract `:line` from the edge id suffix when present.
        call_sites: List[_CallSite] = []
        for ei in edge_indices:
            e = new_edges[ei]
            file_path, line = _extract_file_line_from_edge(e, nodes_by_id)
            if not file_path:
                continue
            surrounding = _read_surrounding(repo_path, file_path, line)
            call_sites.append(
                _CallSite(
                    edge_index=ei,
                    target_qn=target_qn,
                    target_signature=target_sig,
                    other_def_sites=other_sites,
                    source_file=file_path,
                    line=line,
                    surrounding=surrounding,
                )
            )

        if not call_sites:
            continue

        # Batch in groups of MAX_BATCH
        for batch_start in range(0, len(call_sites), MAX_BATCH):
            batch = call_sites[batch_start: batch_start + MAX_BATCH]
            prompt = _build_prompt(target_qn, target_sig, other_sites, batch)
            content = _call_llm(prompt, model=model, project=project, location=location)
            if content is None:
                diagnostics.append(
                    Diagnostic(
                        level="warn",
                        code="LLM_ENRICH_BATCH_FAILED",
                        message=f"LLM call failed for target {target_qn}; leaving edges as AMBIGUOUS.",
                        related_node_ids=[target_id],
                    )
                )
                continue
            data = _extract_json(content)
            if not data or "verdicts" not in data:
                diagnostics.append(
                    Diagnostic(
                        level="warn",
                        code="LLM_ENRICH_PARSE_FAILED",
                        message=f"Could not parse LLM response for {target_qn}.",
                        related_node_ids=[target_id],
                    )
                )
                continue

            verdicts_by_idx: Dict[int, dict] = {v["i"]: v for v in data["verdicts"] if "i" in v and "v" in v}
            for offset, cs in enumerate(batch, start=1):
                verdict = verdicts_by_idx.get(offset)
                if not verdict:
                    continue
                v = verdict.get("v", "U").upper()[:1]
                why = (verdict.get("why") or "").strip()[:240]
                e = new_edges[cs.edge_index]
                if v == "T":
                    new_edges[cs.edge_index] = e.model_copy(update={
                        "confidence": Confidence.LLM_INFERRED,
                        "note": f"LLM resolved to TARGET. {why}",
                    })
                    kept += 1
                elif v == "O":
                    # Drop: replace with a sentinel that we filter post-pass
                    new_edges[cs.edge_index] = e.model_copy(update={
                        "confidence": Confidence.LLM_INFERRED,
                        "note": f"LLM-DROPPED: not target. {why}",
                    })
                    dropped += 1
                else:
                    new_edges[cs.edge_index] = e.model_copy(update={
                        "note": f"LLM unsure. {why}",
                    })
                    unsure += 1

    # Final filter: remove edges flagged LLM-DROPPED in note
    filtered = [e for e in new_edges if not (e.note or "").startswith("LLM-DROPPED")]
    return filtered, kept, dropped, unsure


_AT_RE = re.compile(r"\[at ([^\]]+):(\d+)\]")


def _extract_file_line_from_edge(edge: Edge, nodes_by_id: Dict[str, Any]) -> Tuple[Optional[str], int]:
    """Cross-ref edges store file:line in `note` as '[at <path>:<lineno>]'."""
    if edge.note:
        m = _AT_RE.search(edge.note)
        if m:
            try:
                return m.group(1), int(m.group(2))
            except ValueError:
                pass
    src = nodes_by_id.get(edge.source_id)
    if src is None:
        return None, 0
    if getattr(src, "kind", None) == "symbol":
        file_id = src.file_id
        f = nodes_by_id.get(file_id)
        if f is not None and getattr(f, "kind", None) == "file":
            return f.path, src.line_range.start
    if getattr(src, "kind", None) == "file":
        return src.path, 1
    return None, 0


# ---------- legacy stubs for orchestrator compatibility ----------


def enrich_zero_caller_public_symbols(
    *,
    enrichment_input: EnrichmentInput,
    public_symbols_with_no_callers: list[dict],
    diagnostics: List[Diagnostic],
) -> List[Edge]:
    """Pending: framework-wiring detection for symbols with zero static callers."""
    edges: List[Edge] = []
    if not public_symbols_with_no_callers:
        return edges
    for entry in public_symbols_with_no_callers:
        diagnostics.append(
            Diagnostic(
                level="info",
                code="LLM_ENRICH_ZERO_CALLERS_PENDING",
                message=(
                    f"Public symbol {entry['qualified_name']} has zero resolved callers. "
                    "LLM check for framework wiring deferred."
                ),
                related_node_ids=[entry["symbol_id"]],
            )
        )
    return edges


def detect_generated_file_via_llm(*, enrichment_input: EnrichmentInput, file_path: str, head_excerpt: str, diagnostics: List[Diagnostic]) -> Optional[bool]:
    """Pending."""
    return None
