"""PREx impact-graph schema.

Topology of the PR: nodes (modules / files / symbols / hunks / external refs)
and typed directed edges between them with diff-overlay state.

This is the **deep store** that supports the briefing layer (`brief.py`).
Citations from the briefing layer reach into this graph by node/edge id.

Schema version 0.2.0 — confidence enum dropped in favour of `derivation` +
`score`; unchanged callers materialised as lightweight `CallerStub` rather
than full `SymbolNode`s.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from prex.schemas._shared import (
    ChangeState,
    Citation,
    Derivation,
    Diagnostic,
    LineRange,
)


# ---------- enums (graph-specific) ----------


class NodeKind(str, Enum):
    """Top-level node category. Discriminator for the polymorphic Node union."""

    MODULE = "module"
    FILE = "file"
    SYMBOL = "symbol"
    CALLER_STUB = "caller_stub"  # lightweight unchanged caller (qualified_name + file_id only)
    HUNK = "hunk"
    EXTERNAL_REF = "external_ref"


class SymbolKind(str, Enum):
    """Sub-kind of a Symbol node."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    TYPE = "type"
    CONST = "const"
    TEST = "test"


class ExternalRefKind(str, Enum):
    """Category of an external (out-of-repo) reference."""

    DB_TABLE = "db_table"
    HTTP_ROUTE = "http_route"
    GRPC_METHOD = "grpc_method"
    PACKAGE = "package"
    OTHER = "other"


class HunkChangeType(str, Enum):
    """Hunk-level diff direction."""

    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


class EdgeType(str, Enum):
    """Typed, directed edge.

    Allowed source/target kinds per type:
        contains:    Module->File, File->Symbol, File->Hunk, File->CallerStub
        defines:     Hunk->Symbol  (signature-affecting change)
        touches:     Hunk->Symbol  (body-only change)
        calls:       (Symbol|CallerStub)->Symbol
        references:  (Symbol|CallerStub)->Symbol  (non-call: type usage / read)
        imports:     File->(Symbol|Module|CallerStub)
        covers:      Symbol(symbol_kind=test)->Symbol
        external:    Symbol->ExternalRef
    """

    CONTAINS = "contains"
    DEFINES = "defines"
    TOUCHES = "touches"
    CALLS = "calls"
    REFERENCES = "references"
    IMPORTS = "imports"
    COVERS = "covers"
    EXTERNAL = "external"


# ---------- supporting structs (graph-only) ----------


class PRMetadata(BaseModel):
    """Identifying info for the PR the graph was built from.

    Captures everything needed to reproduce the parse: repo, base/head SHAs,
    branch names, plus surface metadata for UI display. The full PR `body`
    is preserved here so the briefing layer can extract author intent.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="Canonical PR URL.")
    repo: str = Field(description="Owner/name slug.")
    number: int = Field(ge=1)
    title: str
    body: Optional[str] = Field(
        default=None,
        description="Full PR body / description as fetched from the host. Used for intent extraction.",
    )
    author: str
    base_ref: str
    head_ref: str
    base_sha: str = Field(min_length=7)
    head_sha: str = Field(min_length=7)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changed_files: int = Field(ge=0)


# ---------- nodes (discriminated union by `kind`) ----------


class _NodeBase(BaseModel):
    """Common fields for all node kinds. Not instantiated directly.

    `id` is stable and globally-unique within one graph document.
    Recommended id format: `<kind>:<stable-key>` (e.g. `symbol:foo.bar.baz`).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Globally unique within this graph. Format: '<kind>:<stable-key>'.")
    derivation: Derivation = Field(
        default=Derivation.AST,
        description="How the resolver derived this node's existence.",
    )
    score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="0..1 trust score. AST/diff sources default to 1.0; LLM-inferred is lower.",
    )
    change_state: ChangeState = Field(
        default=ChangeState.UNCHANGED,
        description="Diff overlay state of this node.",
    )
    cites: List[Citation] = Field(
        default_factory=list,
        description="Optional citations supporting this node's existence/identity.",
    )


class ModuleNode(_NodeBase):
    """A logical module — a directory containing source files belonging to one unit."""

    kind: Literal[NodeKind.MODULE] = Field(default=NodeKind.MODULE)
    name: str = Field(description="Dotted/path-shaped module identifier.")
    path: str = Field(description="Repo-relative directory path.")


class FileNode(_NodeBase):
    """A source file at head_sha (or base_sha if removed)."""

    kind: Literal[NodeKind.FILE] = Field(default=NodeKind.FILE)
    path: str
    language: str = Field(description="tree-sitter grammar name (e.g. 'python').")
    generated: bool = Field(
        default=False,
        description="True if classified as generated/codegen. Collapse by default in UIs.",
    )


class SymbolNode(_NodeBase):
    """A named, addressable definition: function, method, class, type, const, or test."""

    kind: Literal[NodeKind.SYMBOL] = Field(default=NodeKind.SYMBOL)
    symbol_kind: SymbolKind
    name: str
    qualified_name: str = Field(
        description="Module-rooted dotted name (e.g. 'pkg.mod.Class.method').",
    )
    file_id: str
    line_range: LineRange
    signature: Optional[str] = Field(default=None, description="One-line signature if extractable.")
    public: bool = Field(
        default=False,
        description="Heuristic: not '_'-prefixed, in __all__, or referenced cross-module.",
    )


class CallerStub(_NodeBase):
    """Lightweight reference to an unchanged symbol that calls/imports a changed one.

    Materialised in place of a full `SymbolNode` for symbols outside the changed
    file set. Saves bytes; the host LLM can still attach an edge label without
    rendering the stub as if it were a peer of changed symbols.
    """

    kind: Literal[NodeKind.CALLER_STUB] = Field(default=NodeKind.CALLER_STUB)
    qualified_name: str
    file_id: str = Field(description="ID of the FileNode containing this caller.")
    symbol_kind: Optional[SymbolKind] = None


class HunkNode(_NodeBase):
    """A contiguous diff region within one file. The atomic unit of change."""

    kind: Literal[NodeKind.HUNK] = Field(default=NodeKind.HUNK)
    file_id: str
    line_range: LineRange = Field(description="Lines at head_sha (or base_sha if removed-only).")
    change_type: HunkChangeType
    patch: str = Field(description="Unified-diff fragment ('@@' header + body).")


class ExternalRefNode(_NodeBase):
    """A reference to a resource outside the codebase (DB table, HTTP route, etc.)."""

    kind: Literal[NodeKind.EXTERNAL_REF] = Field(default=NodeKind.EXTERNAL_REF)
    ref_kind: ExternalRefKind
    name: str
    detail: Optional[str] = None


Node = Annotated[
    Union[ModuleNode, FileNode, SymbolNode, CallerStub, HunkNode, ExternalRefNode],
    Field(discriminator="kind"),
]


# ---------- edges ----------


class Edge(BaseModel):
    """Typed directed edge between two nodes.

    Each cross-file caller edge MUST carry at least one `Citation` (typically
    a `file_line` reference to the call site). Other edges may carry zero.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Globally unique edge id.")
    type: EdgeType
    source_id: str
    target_id: str
    derivation: Derivation = Field(default=Derivation.AST, description="How this edge was derived.")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="0..1 trust.")
    change_state: ChangeState = Field(
        default=ChangeState.UNCHANGED,
        description="Edge-level diff overlay (added/removed/modified/unchanged).",
    )
    cites: List[Citation] = Field(
        default_factory=list,
        description="Citations grounding this edge — usually file_line references to a call site.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Free-text annotation. Especially used for llm-derived reasoning.",
    )


# ---------- root ----------


class Graph(BaseModel):
    """Complete impact graph for one PR. Versioned root document."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.2.0"] = Field(
        default="0.2.0",
        description="Semantic version. v0.2 dropped Confidence enum + added CallerStub.",
    )
    generated_at: datetime
    generator: str
    pr: PRMetadata
    nodes: List[Node]
    edges: List[Edge]
    diagnostics: List[Diagnostic] = Field(default_factory=list)


__all__ = [
    "CallerStub",
    "Edge",
    "EdgeType",
    "ExternalRefKind",
    "ExternalRefNode",
    "FileNode",
    "Graph",
    "HunkChangeType",
    "HunkNode",
    "ModuleNode",
    "Node",
    "NodeKind",
    "PRMetadata",
    "SymbolKind",
    "SymbolNode",
]
