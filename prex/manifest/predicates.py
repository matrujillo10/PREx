"""Library of graph/brief predicates the manifest can reference.

Every predicate has the same signature:
    fn(graph, brief) -> PredicateResult
where PredicateResult bundles the auto-status, the targets it applies to,
and an optional Citation grounding the verdict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from prex.schemas._shared import Citation, Derivation
from prex.schemas.brief import Brief, ChecklistStatus
from prex.schemas.graph import (
    EdgeType,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkNode,
    SymbolNode,
)


@dataclass
class PredicateResult:
    status: ChecklistStatus  # 'pass' | 'fail' | 'unknown'
    targets: List[str] = field(default_factory=list)
    evidence: Optional[Citation] = None


PredicateFn = Callable[[Graph, Brief], PredicateResult]


# ---------- helpers ----------


def _changed_public_symbols(graph: Graph) -> List[SymbolNode]:
    return [
        n for n in graph.nodes
        if isinstance(n, SymbolNode) and n.public and n.change_state.value != "unchanged"
    ]


def _added_external_refs(graph: Graph) -> List[ExternalRefNode]:
    return [
        n for n in graph.nodes
        if isinstance(n, ExternalRefNode) and n.change_state.value == "added"
    ]


def _changed_test_symbols(graph: Graph) -> List[SymbolNode]:
    return [
        n for n in graph.nodes
        if isinstance(n, SymbolNode)
        and n.symbol_kind.value == "test"
        and n.change_state.value != "unchanged"
    ]


def _hunks_with_signal(brief: Brief, signal: str) -> List[str]:
    return [h.hunk_id for h in brief.hunks if signal in h.risk_signals]


def _files_changed(graph: Graph) -> List[FileNode]:
    return [n for n in graph.nodes if isinstance(n, FileNode) and n.change_state.value != "unchanged"]


# ---------- predicates ----------


def public_symbol_modified_without_test(graph: Graph, brief: Brief) -> PredicateResult:
    """Fail when ≥1 public symbol was modified/added but no test symbol was changed."""
    public_changed = _changed_public_symbols(graph)
    if not public_changed:
        return PredicateResult(status="unknown")
    if _changed_test_symbols(graph):
        return PredicateResult(
            status="pass",
            targets=[s.id for s in public_changed],
        )
    targets = [s.id for s in public_changed]
    citation = Citation(
        kind="node",
        ref=public_changed[0].id,
        excerpt=f"{len(public_changed)} public symbol(s) changed, no test symbol modified.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


def external_ref_added(graph: Graph, brief: Brief) -> PredicateResult:
    """Fire when this PR introduces a new ExternalRef (DB table, HTTP route, ...)."""
    added = _added_external_refs(graph)
    if not added:
        return PredicateResult(status="pass")
    citation = Citation(
        kind="node",
        ref=added[0].id,
        excerpt=", ".join(n.name for n in added[:5]),
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(
        status="fail",  # 'fail' = needs reviewer attention; UI may render as warning, not red
        targets=[n.id for n in added],
        evidence=citation,
    )


def assertion_removed(graph: Graph, brief: Brief) -> PredicateResult:
    """Fail when any test hunk has the `removes_assertion` risk signal."""
    targets = _hunks_with_signal(brief, "removes_assertion")
    if not targets:
        return PredicateResult(status="pass")
    citation = Citation(
        kind="node",
        ref=targets[0],
        excerpt="At least one test hunk removes an `assert` line.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


def broad_except_added(graph: Graph, brief: Brief) -> PredicateResult:
    targets = _hunks_with_signal(brief, "broad_except")
    if not targets:
        return PredicateResult(status="pass")
    citation = Citation(
        kind="node",
        ref=targets[0],
        excerpt="Bare `except:` or `except Exception` introduced.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


def secret_like_string_added(graph: Graph, brief: Brief) -> PredicateResult:
    targets = _hunks_with_signal(brief, "secret_like_string")
    if not targets:
        return PredicateResult(status="pass")
    citation = Citation(
        kind="node",
        ref=targets[0],
        excerpt="A high-entropy / SDK-token-shaped literal was added.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


_DOC_PATH_RE = re.compile(r"\.(md|rst|adoc|txt)$|/docs?/", re.IGNORECASE)


def no_doc_change_for_public_api(graph: Graph, brief: Brief) -> PredicateResult:
    """Fail when public symbols are added/modified but no documentation file changed."""
    public_changed = _changed_public_symbols(graph)
    if not public_changed:
        return PredicateResult(status="unknown")
    has_doc_change = any(
        _DOC_PATH_RE.search(f.path) for f in _files_changed(graph)
    )
    if has_doc_change:
        return PredicateResult(status="pass", targets=[s.id for s in public_changed])
    citation = Citation(
        kind="node",
        ref=public_changed[0].id,
        excerpt="No file under /docs/ or *.md was changed alongside this public-API PR.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=[s.id for s in public_changed], evidence=citation)


def feature_flag_added(graph: Graph, brief: Brief) -> PredicateResult:
    targets = _hunks_with_signal(brief, "feature_flag_added")
    if not targets:
        return PredicateResult(status="unknown")
    citation = Citation(
        kind="node",
        ref=targets[0],
        excerpt="A feature flag check was introduced.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


def feature_flag_removed(graph: Graph, brief: Brief) -> PredicateResult:
    targets = _hunks_with_signal(brief, "feature_flag_removed")
    if not targets:
        return PredicateResult(status="unknown")
    citation = Citation(
        kind="node",
        ref=targets[0],
        excerpt="A feature flag check was removed.",
        derivation=Derivation.MANIFEST,
        score=1.0,
    )
    return PredicateResult(status="fail", targets=targets, evidence=citation)


# ---------- registry ----------


PREDICATES: Dict[str, PredicateFn] = {
    "public_symbol_modified_without_test": public_symbol_modified_without_test,
    "external_ref_added": external_ref_added,
    "assertion_removed": assertion_removed,
    "broad_except_added": broad_except_added,
    "secret_like_string_added": secret_like_string_added,
    "no_doc_change_for_public_api": no_doc_change_for_public_api,
    "feature_flag_added": feature_flag_added,
    "feature_flag_removed": feature_flag_removed,
}


def evaluate(predicate_name: str, graph: Graph, brief: Brief) -> PredicateResult:
    fn = PREDICATES.get(predicate_name)
    if fn is None:
        return PredicateResult(status="unknown")
    return fn(graph, brief)


__all__ = ["PREDICATES", "PredicateFn", "PredicateResult", "evaluate"]
