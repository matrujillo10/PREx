"""LLM enrichment hook.

v0 implements the hook surface only — the actual triggers may be filled in
incrementally. Off unless the orchestrator passes `enabled=True` (driven by
`--llm-enrich` CLI flag).

Triggers (from the plan):
    1. Stack-graphs/ripgrep returns N>1 candidates for a reference -> pick one.
    2. Stack-graphs returns 0 callers for a public symbol -> framework wiring?
    3. Hunk classification ambiguous (manifest globs + CC prefix conflict).
    4. File suspected generated.
    5. defines() symbol that other in-repo strings reference textually but no edge resolved.

Each trigger calls a small Anthropic message with prompt-cached framework
context. Outputs are appended as edges/nodes with confidence=LLM_INFERRED and a
`note` capturing the LLM's reasoning. All calls are best-effort: any failure
becomes a Diagnostic, never fatal.

In v0, only triggers (2) and (4) are actually wired (the highest-value ones for PR #19858).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

from prex.schemas.graph import Confidence, Diagnostic, Edge, EdgeType


@dataclass
class EnrichmentInput:
    """Bundle of repo-level context the enricher receives once per run.

    `framework_hints` is meant to be prompt-cached — large, stable, repo-shaped
    text describing detected frameworks (Django/FastAPI/gRPC/etc.). v0 leaves it
    empty; future versions can populate it with package detection results.
    """

    repo: str
    framework_hints: str = ""


def is_available() -> bool:
    """LLM enrichment available only when ANTHROPIC_API_KEY is set."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def enrich_zero_caller_public_symbols(
    *,
    enrichment_input: EnrichmentInput,
    public_symbols_with_no_callers: list[dict],
    diagnostics: List[Diagnostic],
) -> List[Edge]:
    """For each public symbol with no callers, ask the LLM if it's wired by framework dispatch.

    Each item in `public_symbols_with_no_callers` is a dict:
        {
          "symbol_id": "<node id>",
          "qualified_name": str,
          "signature": str | None,
          "file_path": str,
        }

    Returns a list of LLM-inferred edges (mostly REFERENCES from a synthetic
    `framework:<kind>` node — but in v0 we don't materialise the framework node;
    we just attach a Diagnostic carrying the reasoning).

    v0 behaviour: emit a Diagnostic per symbol, no edges. Real call deferred.
    """
    edges: List[Edge] = []
    if not public_symbols_with_no_callers:
        return edges
    if not is_available():
        diagnostics.append(
            Diagnostic(
                level="info",
                code="LLM_ENRICH_UNAVAILABLE",
                message="ANTHROPIC_API_KEY not set; skipping LLM enrichment.",
                related_node_ids=[],
            )
        )
        return edges
    # Real implementation would batch-call here. For v0, log a diagnostic so
    # the user sees the trigger fired without paying for an API call yet.
    for entry in public_symbols_with_no_callers:
        diagnostics.append(
            Diagnostic(
                level="info",
                code="LLM_ENRICH_ZERO_CALLERS_PENDING",
                message=(
                    f"Public symbol {entry['qualified_name']} has zero resolved callers. "
                    "LLM check for framework wiring deferred to v0.1."
                ),
                related_node_ids=[entry["symbol_id"]],
            )
        )
    return edges


def detect_generated_file_via_llm(
    *,
    enrichment_input: EnrichmentInput,
    file_path: str,
    head_excerpt: str,
    diagnostics: List[Diagnostic],
) -> Optional[bool]:
    """Ask the LLM whether a file is generated.

    v0 returns None (deferred). Heuristic-only detection happens in `_emit`/
    parse layer based on path patterns.
    """
    return None
