"""Briefing layer — what the generative-UI host LLM consumes.

`Brief` is the primary input. It rides on top of `Graph` (sibling artifact);
every claim it makes carries Citation refs into the graph or to specific
file:line ranges.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from prex.schemas._shared import Citation, Diagnostic
from prex.schemas.graph import PRMetadata


# ---------- enums (brief-specific) ----------

# Risk signals that risk_signal queries can produce. AST-derived; no LLM.
RiskSignal = Literal[
    "auth_or_authz_touched",
    "sql_in_changed_lines",
    "external_io",
    "removes_assertion",
    "weakens_validation",
    "raises_swallowed",
    "broad_except",
    "feature_flag_added",
    "feature_flag_removed",
    "secret_like_string",
    "numeric_constant_changed_in_hot_loop",
]

# High-level intent classification of a single hunk.
HunkIntent = Literal[
    "adds_capability",
    "fixes_bug",
    "renames",
    "extracts",
    "inlines",
    "reorders",
    "tightens_types",
    "weakens_test",
    "adds_test",
    "removes_dead",
    "comments_only",
    "style_only",
    "unknown",
]

# PR-level type spine. v0.1 covers feat/fix/chore (per decisions.md). Future
# versions may add perf, deps, security, migration, config, prompt.
PRType = Literal["feat", "fix", "chore", "unknown"]

# Risk tier for the whole PR. Drives default review depth.
RiskTier = Literal["trivial", "standard", "sensitive"]

# Advisory flags raised at the PR level. Each one is renderable as a chip.
AdvisoryFlag = Literal[
    "scope_creep_5plus_areas",
    "test_lines_removed",
    "generated_files_only",
    "secret_like_string_added",
    "no_test_coverage_changed",
    "ai_authorship_undisclosed",
    "no_docs_for_public_api",
    "removes_assertion",
    "broad_except_added",
]


# ---------- per-hunk insight ----------


class HunkInsight(BaseModel):
    """Per-hunk semantic anchor.

    `risk_signals` is AST-derived (deterministic). `one_liner` and `intent`
    are filled by the LLM only when --llm-summarise is set.
    """

    model_config = ConfigDict(extra="forbid")

    hunk_id: str = Field(description="ID of the HunkNode this insight describes.")
    one_liner: Optional[str] = Field(
        default=None,
        max_length=200,
        description="≤80-char human description. LLM-filled iff --llm-summarise.",
    )
    intent: HunkIntent = Field(
        default="unknown",
        description="High-level intent classification.",
    )
    risk_signals: List[RiskSignal] = Field(
        default_factory=list,
        description="AST-derived risk markers found in the hunk's added/removed lines.",
    )
    affects_public_symbol_ids: List[str] = Field(
        default_factory=list,
        description="Symbol node ids the hunk modifies/defines that are marked public.",
    )
    cites: List[Citation] = Field(
        default_factory=list,
        description="Citations grounding the insight. At least one required when one_liner is set.",
    )
    score: float = Field(default=1.0, ge=0.0, le=1.0)


# ---------- review brief (PR-level hero block) ----------


class BlastRadius(BaseModel):
    """Counters that quantify outward impact of the PR."""

    model_config = ConfigDict(extra="forbid")

    caller_files: int = Field(ge=0, description="Distinct files calling/referencing changed symbols.")
    modules_crossed: int = Field(ge=0, description="Distinct modules containing any caller.")
    public_symbols_modified: int = Field(ge=0, description="# of public-flagged Symbols touched.")
    external_refs_added: int = Field(ge=0, description="# of newly-added ExternalRef nodes.")


class Novelty(BaseModel):
    """Counters that quantify what's new vs touched."""

    model_config = ConfigDict(extra="forbid")

    new_files: int = Field(ge=0)
    new_symbols: int = Field(ge=0)
    new_external_refs: int = Field(ge=0)


class ReviewBrief(BaseModel):
    """PR-level hero block. One block, one component group."""

    model_config = ConfigDict(extra="forbid")

    pr_type: PRType
    pr_type_confidence: float = Field(ge=0.0, le=1.0)
    pr_type_evidence: List[Citation] = Field(
        default_factory=list,
        description="Evidence supporting `pr_type`: title prefix, glob match, etc.",
    )
    risk_tier: RiskTier
    risk_score: float = Field(ge=0.0, le=1.0)
    blast_radius: BlastRadius
    novelty: Novelty
    headline: Optional[str] = Field(
        default=None,
        max_length=200,
        description="≤140-char human-readable summary. LLM-filled iff --llm-summarise.",
    )
    advisory_flags: List[AdvisoryFlag] = Field(default_factory=list)
    cites: List[Citation] = Field(default_factory=list)


# ---------- review plan (the guided What/Why/Impact navigation) ----------


class ReviewStep(BaseModel):
    """One step in the suggested review path.

    `what` / `why` / `impact` are LLM-filled iff --llm-summarise. The
    deterministic fields (rank, target, risk_signals, cites) are always
    populated by the ranking algorithm.
    """

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1, description="1-indexed; lower = read first.")
    target: str = Field(description="Primary node id (hunk or symbol) anchoring this step.")
    title: Optional[str] = Field(
        default=None,
        max_length=120,
        description="≤60-char label of what the step covers.",
    )
    what: Optional[str] = Field(
        default=None,
        max_length=600,
        description="≤2 sentences. The objective change in plain language.",
    )
    why: Optional[str] = Field(
        default=None,
        max_length=600,
        description="≤2 sentences. Ties to author intent (PR title/body) + pr_type.",
    )
    impact: Optional[str] = Field(
        default=None,
        max_length=600,
        description="≤2 sentences. Quotes blast_radius numbers + downstream callers.",
    )
    estimated_minutes: int = Field(default=2, ge=1, le=60)
    risk_signals: List[RiskSignal] = Field(default_factory=list)
    related_targets: List[str] = Field(
        default_factory=list,
        description="Secondary node ids the reviewer should glance at while on this step.",
    )
    cites: List[Citation] = Field(
        default_factory=list,
        description="Citations grounding the step. Each prose field must cite at least one node/edge/file_line.",
    )


class ReviewPlan(BaseModel):
    """The guided navigation through the PR.

    One block, one component group on the host. Triple-framed (What/Why/Impact)
    so the host LLM can map each part to a distinct UI affordance.
    """

    model_config = ConfigDict(extra="forbid")

    overview: Optional[str] = Field(
        default=None,
        max_length=600,
        description="≤3 sentences tying the steps together as a navigation through-line.",
    )
    steps: List[ReviewStep] = Field(default_factory=list)
    cites: List[Citation] = Field(default_factory=list)


# ---------- checklist (manifest binding) ----------


ChecklistStatus = Literal["pass", "fail", "unknown"]


class ChecklistItem(BaseModel):
    """One review check, bound to specific targets in the graph."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable id (e.g. 'public_symbol_modified_without_test').")
    text: str = Field(description="Human-readable text rendered in the UI.")
    required: bool = Field(default=False)
    targets: List[str] = Field(
        default_factory=list,
        description="Hunk or symbol node ids this item applies to.",
    )
    auto_status: Optional[ChecklistStatus] = Field(
        default=None,
        description="Auto-evaluated status when the predicate runs deterministically.",
    )
    auto_evidence: Optional[Citation] = None


class ChecklistBinding(BaseModel):
    """A grouping of checklist items, optionally scoped to a PR type."""

    model_config = ConfigDict(extra="forbid")

    type: Optional[PRType] = Field(
        default=None,
        description="When set, items apply only to PRs of this type. None = generic.",
    )
    checklist_items: List[ChecklistItem] = Field(default_factory=list)


# ---------- root ----------


class Brief(BaseModel):
    """Briefing for the generative-UI host LLM.

    Sibling of `Graph`. Host LLM consumes `brief.json` first; reaches into
    `graph.json` only when following a citation.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1.0"] = Field(default="0.1.0")
    generated_at: datetime
    generator: str
    pr: PRMetadata
    review: ReviewBrief
    plan: ReviewPlan
    hunks: List[HunkInsight] = Field(default_factory=list)
    checklist: List[ChecklistBinding] = Field(default_factory=list)
    graph_ref: str = Field(
        description="Relative path to the sibling graph.json artifact.",
    )
    diagnostics: List[Diagnostic] = Field(default_factory=list)
    llm_used: bool = Field(
        default=False,
        description="True iff at least one prose field was filled by an LLM call.",
    )


__all__ = [
    "AdvisoryFlag",
    "BlastRadius",
    "Brief",
    "ChecklistBinding",
    "ChecklistItem",
    "ChecklistStatus",
    "HunkInsight",
    "HunkIntent",
    "Novelty",
    "PRType",
    "ReviewBrief",
    "ReviewPlan",
    "ReviewStep",
    "RiskSignal",
    "RiskTier",
]
