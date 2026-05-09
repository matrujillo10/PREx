"""Graph -> JSON / Mermaid emit + invariant validation."""
from __future__ import annotations

import json
from typing import Iterable, List, Set, Tuple

from prex.schemas.graph import (
    ChangeState,
    Confidence,
    Diagnostic,
    Edge,
    EdgeType,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkNode,
    ModuleNode,
    NodeKind,
    SymbolNode,
)


def validate_invariants(graph: Graph) -> List[Diagnostic]:
    """Check the schema-level invariants from the plan.

    Emits Diagnostic records (does not raise). Caller should append to graph.diagnostics.
    """
    out: List[Diagnostic] = []
    node_ids: Set[str] = set()
    nodes_by_id: dict[str, object] = {}

    for n in graph.nodes:
        if n.id in node_ids:
            out.append(
                Diagnostic(
                    level="error",
                    code="INVARIANT_DUPLICATE_NODE_ID",
                    message=f"Duplicate node id: {n.id}",
                    related_node_ids=[n.id],
                )
            )
        node_ids.add(n.id)
        nodes_by_id[n.id] = n

    # Edge endpoint resolution + symbol/hunk file_id resolution
    for n in graph.nodes:
        if isinstance(n, (SymbolNode, HunkNode)):
            if n.file_id not in node_ids:
                out.append(
                    Diagnostic(
                        level="error",
                        code="INVARIANT_ORPHAN_FILE_ID",
                        message=f"Node {n.id} references missing file_id={n.file_id}",
                        related_node_ids=[n.id],
                    )
                )

    for e in graph.edges:
        if e.source_id not in node_ids:
            out.append(
                Diagnostic(
                    level="error",
                    code="INVARIANT_ORPHAN_EDGE_SOURCE",
                    message=f"Edge {e.id} has unknown source_id={e.source_id}",
                    related_node_ids=[e.source_id],
                )
            )
        if e.target_id not in node_ids:
            out.append(
                Diagnostic(
                    level="error",
                    code="INVARIANT_ORPHAN_EDGE_TARGET",
                    message=f"Edge {e.id} has unknown target_id={e.target_id}",
                    related_node_ids=[e.target_id],
                )
            )

    # Each changed Symbol must have at least one defines/touches Hunk edge
    edges_by_target: dict[str, List[Edge]] = {}
    for e in graph.edges:
        edges_by_target.setdefault(e.target_id, []).append(e)
    for n in graph.nodes:
        if isinstance(n, SymbolNode) and n.change_state != ChangeState.UNCHANGED:
            ev = edges_by_target.get(n.id, [])
            if not any(e.type in (EdgeType.DEFINES, EdgeType.TOUCHES) for e in ev):
                out.append(
                    Diagnostic(
                        level="warn",
                        code="INVARIANT_CHANGED_SYMBOL_NO_HUNK",
                        message=(
                            f"Changed symbol {n.qualified_name} ({n.id}) has no defines/touches hunk edge."
                        ),
                        related_node_ids=[n.id],
                    )
                )

    return out


def to_json(graph: Graph) -> str:
    """Serialise the graph to indented JSON. Pydantic v2 handles enum + datetime."""
    return graph.model_dump_json(indent=2)


# ---------- Mermaid renderer ----------

_CLASS_DEFS = """
classDef changed fill:#fff7c2,stroke:#a37200,stroke-width:2px,color:#000
classDef newdep fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
classDef caller fill:#dcfce7,stroke:#15803d,stroke-width:2px,color:#14532d
classDef hidden fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#7c2d12
classDef testgap fill:#fecaca,stroke:#b91c1c,stroke-width:2px,stroke-dasharray:4 3,color:#7f1d1d
classDef gen fill:#eee,stroke:#999,stroke-dasharray:4 3,color:#555
classDef base fill:#fff,stroke:#666,color:#111
""".strip()


import hashlib


def _mermaid_id(s: str) -> str:
    """Stable, collision-free Mermaid id. Truncate prefix + append short hash of full id."""
    safe = "".join(c if (c.isalnum() or c == "_") else "_" for c in s)
    digest = hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]
    return f"n_{safe[:60]}_{digest}"


def _node_class(n) -> str:
    if isinstance(n, ExternalRefNode):
        return "newdep" if n.change_state == ChangeState.ADDED else "base"
    if isinstance(n, FileNode):
        if getattr(n, "generated", False):
            return "gen"
    if isinstance(n, SymbolNode):
        if n.change_state in (ChangeState.MODIFIED, ChangeState.ADDED):
            return "changed"
        if n.symbol_kind.value == "test" and n.change_state == ChangeState.UNCHANGED:
            return "testgap"
        return "caller" if n.change_state == ChangeState.UNCHANGED else "base"
    return "base"


def _node_label(n) -> str:
    if isinstance(n, SymbolNode):
        marker = ""
        if n.change_state == ChangeState.MODIFIED:
            marker = "✱ "
        if n.change_state == ChangeState.ADDED:
            marker = "+ "
        return f"{marker}{n.qualified_name}"
    if isinstance(n, FileNode):
        return n.path
    if isinstance(n, ModuleNode):
        return n.name
    if isinstance(n, ExternalRefNode):
        return f"{n.ref_kind.value}: {n.name}"
    if isinstance(n, HunkNode):
        return f"hunk L{n.line_range.start}-{n.line_range.end}"
    return n.id


def to_mermaid(graph: Graph, *, only_impact: bool = True) -> str:
    """Render an Impact-view Mermaid flowchart.

    `only_impact=True` keeps only Symbol/ExternalRef nodes and the edges that
    matter for blast-radius reading: calls / references / imports / external,
    plus any 1-hop callers of changed symbols. Skips contains/defines/touches
    edges (Tree view is a separate render).
    """
    lines: list[str] = ["flowchart LR"]

    # Pick relevant nodes
    keep_kinds = {NodeKind.SYMBOL, NodeKind.EXTERNAL_REF}
    rel_edges = [
        e for e in graph.edges
        if e.type in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS, EdgeType.EXTERNAL)
    ]
    rel_node_ids = {e.source_id for e in rel_edges} | {e.target_id for e in rel_edges}

    nodes_in: list = []
    for n in graph.nodes:
        kind = getattr(n, "kind", None)
        if kind in keep_kinds and (n.id in rel_node_ids or (isinstance(n, SymbolNode) and n.change_state != ChangeState.UNCHANGED)):
            nodes_in.append(n)

    # emit nodes
    for n in nodes_in:
        nid = _mermaid_id(n.id)
        label = _node_label(n).replace('"', "'").replace("\n", " ")
        cls = _node_class(n)
        lines.append(f'  {nid}["{label}"]:::{cls}')

    nid_set = {_mermaid_id(n.id) for n in nodes_in}

    # emit edges
    for e in rel_edges:
        a = _mermaid_id(e.source_id)
        b = _mermaid_id(e.target_id)
        if a not in nid_set or b not in nid_set:
            continue
        arrow = "-->"
        label = e.type.value
        if e.confidence == Confidence.LLM_INFERRED:
            arrow = "-.->"
            label = f"{e.type.value} (llm)"
        if e.confidence == Confidence.AMBIGUOUS:
            label = f"{e.type.value}?"
        lines.append(f'  {a} {arrow}|{label}| {b}')

    lines.append("")
    lines.append(_CLASS_DEFS)
    return "\n".join(lines)
