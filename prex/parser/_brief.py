"""Build a `Brief` (the briefing layer) from a fully-resolved `Graph`.

Deterministic in v1 — every field is computed from graph topology +
AST-derived risk signals. LLM prose calls (one_liner, headline, plan What/Why/Impact)
are wired in `_brief_llm.py` and gated by `--llm-summarise`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from prex.parser._signals import signals_for_hunk
from prex.schemas._shared import Citation, Derivation, Diagnostic
from prex.schemas.brief import (
    AdvisoryFlag,
    BlastRadius,
    Brief,
    ChecklistBinding,
    HunkInsight,
    Novelty,
    PRType,
    ReviewBrief,
    ReviewPlan,
    ReviewStep,
    RiskSignal,
    RiskTier,
)
from prex.schemas.graph import (
    CallerStub,
    EdgeType,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkNode,
    NodeKind,
    SymbolNode,
)


# ---------- helpers ----------


_TYPE_PREFIX_RE = re.compile(r"^\s*(?P<type>feat|fix|chore|refactor|perf|test|docs|deps|build|ci|style)\b", re.IGNORECASE)


def _detect_pr_type(graph: Graph) -> Tuple[PRType, float, List[Citation]]:
    """Classify pr_type from title prefix. v0.1 covers feat/fix/chore."""
    title = graph.pr.title or ""
    m = _TYPE_PREFIX_RE.match(title)
    cites: List[Citation] = []
    if m:
        prefix = m.group("type").lower()
        cites.append(
            Citation(
                kind="external_doc",
                ref=graph.pr.url,
                excerpt=f"title: {title[:100]}",
                derivation=Derivation.HEURISTIC,
                score=0.95,
            )
        )
        if prefix in ("feat", "fix", "chore"):
            return prefix, 0.95, cites  # type: ignore[return-value]
        # Map non-MVP types to chore for now (manifest layer is generic).
        return "chore", 0.6, cites
    return "unknown", 0.3, cites


def _public_changed_symbols(graph: Graph) -> List[SymbolNode]:
    return [
        n for n in graph.nodes
        if isinstance(n, SymbolNode) and n.public and n.change_state.value != "unchanged"
    ]


def _changed_external_refs(graph: Graph) -> List[ExternalRefNode]:
    return [
        n for n in graph.nodes
        if isinstance(n, ExternalRefNode) and n.change_state.value == "added"
    ]


def _compute_blast_radius(graph: Graph) -> BlastRadius:
    nodes_by_id = {n.id: n for n in graph.nodes}
    changed_sym_ids = {
        n.id for n in graph.nodes
        if isinstance(n, SymbolNode) and n.change_state.value != "unchanged"
    }
    caller_files: set[str] = set()
    modules_crossed: set[str] = set()
    for e in graph.edges:
        if e.type not in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS):
            continue
        if e.target_id not in changed_sym_ids:
            continue
        src = nodes_by_id.get(e.source_id)
        if isinstance(src, (SymbolNode, CallerStub)):
            file_node = nodes_by_id.get(src.file_id)
            if isinstance(file_node, FileNode):
                caller_files.add(file_node.path)
                modules_crossed.add(_module_of_path(file_node.path))
        elif isinstance(src, FileNode):
            caller_files.add(src.path)
            modules_crossed.add(_module_of_path(src.path))
    public = sum(
        1 for n in graph.nodes
        if isinstance(n, SymbolNode) and n.public and n.change_state.value != "unchanged"
    )
    externals_added = sum(
        1 for n in graph.nodes if isinstance(n, ExternalRefNode) and n.change_state.value == "added"
    )
    return BlastRadius(
        caller_files=len(caller_files),
        modules_crossed=len(modules_crossed),
        public_symbols_modified=public,
        external_refs_added=externals_added,
    )


def _module_of_path(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else "."


def _compute_novelty(graph: Graph) -> Novelty:
    return Novelty(
        new_files=sum(
            1 for n in graph.nodes if isinstance(n, FileNode) and n.change_state.value == "added"
        ),
        new_symbols=sum(
            1 for n in graph.nodes if isinstance(n, SymbolNode) and n.change_state.value == "added"
        ),
        new_external_refs=sum(
            1 for n in graph.nodes if isinstance(n, ExternalRefNode) and n.change_state.value == "added"
        ),
    )


def _scope_creep(graph: Graph) -> bool:
    """5+ distinct module roots touched by changed files."""
    roots: set[str] = set()
    for n in graph.nodes:
        if isinstance(n, FileNode) and n.change_state.value != "unchanged":
            top = n.path.split("/", 1)[0]
            roots.add(top)
    return len(roots) >= 5


def _has_any(graph: Graph, *symbol_kinds: str, change_states: Tuple[str, ...] = ("modified", "added", "removed")) -> bool:
    for n in graph.nodes:
        if isinstance(n, SymbolNode) and n.symbol_kind.value in symbol_kinds and n.change_state.value in change_states:
            return True
    return False


def _has_test_changes(graph: Graph) -> bool:
    for n in graph.nodes:
        if isinstance(n, SymbolNode) and n.symbol_kind.value == "test" and n.change_state.value != "unchanged":
            return True
    return False


def _all_changed_files_generated(graph: Graph) -> bool:
    changed = [n for n in graph.nodes if isinstance(n, FileNode) and n.change_state.value != "unchanged"]
    if not changed:
        return False
    return all(getattr(n, "generated", False) for n in changed)


# ---------- hunk insights ----------


def _build_hunk_insights(graph: Graph) -> List[HunkInsight]:
    nodes_by_id = {n.id: n for n in graph.nodes}
    insights: List[HunkInsight] = []

    # Pre-compute changed-symbol affects per hunk via defines/touches edges
    affects: Dict[str, List[str]] = {}
    for e in graph.edges:
        if e.type in (EdgeType.DEFINES, EdgeType.TOUCHES):
            tgt = nodes_by_id.get(e.target_id)
            if isinstance(tgt, SymbolNode) and tgt.public:
                affects.setdefault(e.source_id, []).append(tgt.id)

    for n in graph.nodes:
        if not isinstance(n, HunkNode):
            continue
        file_node = nodes_by_id.get(n.file_id)
        in_test = False
        if isinstance(file_node, FileNode):
            in_test = "/tests/" in f"/{file_node.path}/" or file_node.path.split("/")[-1].startswith("test_")
        sigs = signals_for_hunk(n.patch, in_test_file=in_test)
        risk_signals: List[RiskSignal] = [s for s, _ in sigs]
        # Cite the hunk node itself + the file-line range
        cites: List[Citation] = [
            Citation(
                kind="node",
                ref=n.id,
                derivation=Derivation.AST,
                score=1.0,
            ),
        ]
        if isinstance(file_node, FileNode):
            cites.append(
                Citation(
                    kind="file_line",
                    ref=f"{file_node.path}#L{n.line_range.start}-L{n.line_range.end}",
                    derivation=Derivation.DIFF,
                    score=1.0,
                )
            )
        for sig, excerpt in sigs:
            if isinstance(file_node, FileNode):
                cites.append(
                    Citation(
                        kind="file_line",
                        ref=f"{file_node.path}#L{n.line_range.start}-L{n.line_range.end}",
                        excerpt=excerpt,
                        derivation=Derivation.AST,
                        score=0.9,
                    )
                )
        insights.append(
            HunkInsight(
                hunk_id=n.id,
                intent="unknown",  # filled by LLM in Build 3
                risk_signals=risk_signals,
                affects_public_symbol_ids=affects.get(n.id, []),
                cites=cites,
                score=1.0,
            )
        )
    return insights


# ---------- review plan ranking (deterministic; prose later via LLM) ----------


def _rank_targets(graph: Graph, hunk_insights: List[HunkInsight]) -> List[ReviewStep]:
    nodes_by_id = {n.id: n for n in graph.nodes}
    in_degrees: Dict[str, int] = {}
    for e in graph.edges:
        if e.type in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS):
            in_degrees[e.target_id] = in_degrees.get(e.target_id, 0) + 1

    # Score each changed Symbol
    candidates: List[Tuple[float, str, str]] = []  # (score, node_id, kind)
    max_callers = max(in_degrees.values(), default=1)
    for n in graph.nodes:
        if isinstance(n, SymbolNode) and n.change_state.value != "unchanged":
            callers = in_degrees.get(n.id, 0)
            externals_added = sum(
                1 for e in graph.edges
                if e.type == EdgeType.EXTERNAL and e.source_id == n.id
            )
            hunk_size = (n.line_range.end - n.line_range.start + 1) / 200.0
            score = (
                0.4 * (1.0 if n.public else 0.0)
                + 0.3 * (callers / max_callers)
                + 0.2 * (1.0 if externals_added > 0 else 0.0)
                + 0.1 * min(hunk_size, 1.0)
            )
            candidates.append((score, n.id, "symbol"))

    # Add any Hunk with risk signals as a candidate
    insights_by_hunk = {h.hunk_id: h for h in hunk_insights}
    for hi in hunk_insights:
        if hi.risk_signals:
            score = 0.5 + 0.1 * len(hi.risk_signals)
            candidates.append((score, hi.hunk_id, "hunk"))

    # Sort descending and greedy-pack with diversity (no two from same Symbol's qualified_name)
    candidates.sort(key=lambda c: c[0], reverse=True)
    seen_anchors: set[str] = set()
    steps: List[ReviewStep] = []
    rank = 1
    for score, node_id, kind in candidates:
        n = nodes_by_id.get(node_id)
        anchor = node_id
        if isinstance(n, SymbolNode):
            anchor = n.qualified_name
        elif isinstance(n, HunkNode):
            file_node = nodes_by_id.get(n.file_id)
            anchor = f"{file_node.path}:{n.line_range.start}" if isinstance(file_node, FileNode) else node_id
        if anchor in seen_anchors:
            continue
        seen_anchors.add(anchor)

        risk_sigs: List[RiskSignal] = []
        if kind == "hunk" and node_id in insights_by_hunk:
            risk_sigs = list(insights_by_hunk[node_id].risk_signals)
        elif isinstance(n, SymbolNode):
            for e in graph.edges:
                if e.type in (EdgeType.DEFINES, EdgeType.TOUCHES) and e.target_id == n.id:
                    if e.source_id in insights_by_hunk:
                        risk_sigs.extend(insights_by_hunk[e.source_id].risk_signals)
            risk_sigs = list(set(risk_sigs))

        cites: List[Citation] = [
            Citation(
                kind="node",
                ref=node_id,
                derivation=Derivation.AST,
                score=min(1.0, score),
            )
        ]
        steps.append(
            ReviewStep(
                rank=rank,
                target=node_id,
                title=None,
                what=None,
                why=None,
                impact=None,
                estimated_minutes=2,
                risk_signals=risk_sigs,
                related_targets=[],
                cites=cites,
            )
        )
        rank += 1
        if rank > 7:
            break
    return steps


# ---------- top-level builder ----------


def _risk_tier(blast: BlastRadius, novelty: Novelty, advisory: List[AdvisoryFlag]) -> Tuple[RiskTier, float]:
    score = 0.0
    score += min(0.3, blast.public_symbols_modified * 0.1)
    score += min(0.2, blast.modules_crossed * 0.05)
    score += min(0.2, blast.external_refs_added * 0.1)
    score += 0.1 * len(advisory)
    score += min(0.2, novelty.new_files * 0.02)
    score = min(1.0, score)
    if score < 0.2:
        tier: RiskTier = "trivial"
    elif score < 0.55:
        tier = "standard"
    else:
        tier = "sensitive"
    return tier, score


def _advisory_flags(graph: Graph, blast: BlastRadius) -> List[AdvisoryFlag]:
    flags: List[AdvisoryFlag] = []
    if _scope_creep(graph):
        flags.append("scope_creep_5plus_areas")
    # test_lines_removed: any test symbol modified/removed
    for n in graph.nodes:
        if isinstance(n, SymbolNode) and n.symbol_kind.value == "test" and n.change_state.value in ("modified", "removed"):
            flags.append("test_lines_removed")
            break
    if _all_changed_files_generated(graph):
        flags.append("generated_files_only")
    if blast.public_symbols_modified > 0 and not _has_test_changes(graph):
        flags.append("no_test_coverage_changed")
    return flags


def build_brief(graph: Graph, *, graph_ref: str = "graph.json") -> Brief:
    """Compute the deterministic briefing layer from a built graph."""
    pr_type, pr_type_conf, pr_type_cites = _detect_pr_type(graph)
    blast = _compute_blast_radius(graph)
    novelty = _compute_novelty(graph)
    hunk_insights = _build_hunk_insights(graph)
    advisory = _advisory_flags(graph, blast)
    tier, risk_score = _risk_tier(blast, novelty, advisory)

    review = ReviewBrief(
        pr_type=pr_type,
        pr_type_confidence=pr_type_conf,
        pr_type_evidence=pr_type_cites,
        risk_tier=tier,
        risk_score=risk_score,
        blast_radius=blast,
        novelty=novelty,
        headline=None,  # filled by LLM in Build 3
        advisory_flags=advisory,
        cites=pr_type_cites,
    )

    plan = ReviewPlan(
        overview=None,
        steps=_rank_targets(graph, hunk_insights),
        cites=[],
    )

    return Brief(
        generated_at=datetime.now(timezone.utc),
        generator="prex 0.2.0",
        pr=graph.pr,
        review=review,
        plan=plan,
        hunks=hunk_insights,
        checklist=[],  # populated in Build 2
        graph_ref=graph_ref,
        diagnostics=[],
        llm_used=False,
    )
