"""Shared primitives used by both graph and brief schemas.

Held separate so cross-module imports stay clean and so that downstream
consumers can pull just the citation/diagnostic types without dragging in
the whole graph or brief surface.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Derivation(str, Enum):
    """How a fact in the output was produced.

    Maps directly to a render tag the host LLM can show next to any claim.
    """

    AST = "ast"  # tree-sitter / structural parse of head_sha source.
    DIFF = "diff"  # unified-diff hunk overlap or line-mode comparison.
    CROSSREF_TEXT = "crossref_text"  # native word-boundary text search across the repo.
    LLM = "llm"  # produced by an enrichment LLM call (must be visibly badged in UI).
    MANIFEST = "manifest"  # configured rule from .review/types.yaml; deterministic.
    HEURISTIC = "heuristic"  # path/regex/string heuristic with no AST grounding.


class ChangeState(str, Enum):
    """Diff overlay state of a graph node or edge.

    Computed by overlaying the unified diff on the symbol's line range;
    'added' means present at head_sha but not base_sha (or only on `+` lines).
    """

    UNCHANGED = "unchanged"
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


class LineRange(BaseModel):
    """Inclusive 1-indexed line range in a file at a given SHA."""

    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=1, description="1-indexed start line.")
    end: int = Field(ge=1, description="1-indexed end line, inclusive of `start`.")


class Citation(BaseModel):
    """Universal provenance primitive.

    Every prose field in PREx output (headlines, one-liners, plan rationales)
    carries one or more `Citation` items. The host LLM is expected to render
    a fact only via its citation; an unsourced claim is a validation error.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["node", "edge", "file_line", "external_doc"] = Field(
        description=(
            "Resolution mode for `ref`: 'node' or 'edge' = id in graph.json; "
            "'file_line' = '<path>#L<start>-L<end>' at pr.head_sha; "
            "'external_doc' = absolute URL."
        )
    )
    ref: str = Field(
        description="Reference identifier. Format depends on `kind`.",
    )
    excerpt: Optional[str] = Field(
        default=None,
        max_length=240,
        description="Optional ≤120-char literal quote of the cited evidence.",
    )
    derivation: Derivation = Field(
        description="How the claim being cited was produced.",
    )
    score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional 0..1 trust score for the claim. Use for visual weighting.",
    )


class Diagnostic(BaseModel):
    """Non-fatal warning emitted during graph or brief construction.

    Used to surface static-analysis misses, ambiguity, schema invariant
    violations, and LLM enrichment failures. Reviewer-visible at `level`
    >= 'warn'; `info` is plumbing.
    """

    model_config = ConfigDict(extra="forbid")

    level: Literal["info", "warn", "error"] = Field(description="Severity.")
    code: str = Field(description="Stable identifier (e.g. 'INVARIANT_ORPHAN_EDGE').")
    message: str
    related_node_ids: List[str] = Field(
        default_factory=list,
        description="Node IDs this diagnostic refers to. Empty for global diagnostics.",
    )


__all__ = [
    "ChangeState",
    "Citation",
    "Derivation",
    "Diagnostic",
    "LineRange",
]
