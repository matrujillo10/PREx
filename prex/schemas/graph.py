"""PREx impact-graph schema.

Single source of truth for the structure produced by `prex review <PR>`.
Downstream Claude sessions and any UI/predicate engine consume these models.

Generation rules:
    - Pydantic v2 models defined here are authoritative.
    - `prex/schemas/graph.schema.json` is generated from `Graph.model_json_schema()`.
      Never hand-edit it; regenerate via `python -m prex.schemas.gen`.

Design overview:
    The graph is a directed multigraph with five node kinds and eight edge types.
    Nodes form a discriminated union over `kind`; edges are uniform.

    Tree view  = projection over (contains, defines, touches), filtered to non-unchanged.
    Impact view = projection over (calls, references, imports), reverse-traversed
                  from changed Symbol nodes to depth N (N=1 in v0).

    Every node and edge carries:
        - `change_state`: how the diff overlay sees it
        - `confidence`:   how the resolver knew about it
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------- enums ----------


class NodeKind(str, Enum):
    """Top-level node category. Discriminator for the polymorphic Node union.

    Each kind maps to one Pydantic model with a fixed `kind` literal.
    """

    MODULE = "module"
    FILE = "file"
    SYMBOL = "symbol"
    HUNK = "hunk"
    EXTERNAL_REF = "external_ref"


class SymbolKind(str, Enum):
    """Sub-kind of a Symbol node. The reviewer-visible classification of a definition."""

    FUNCTION = "function"  # Top-level function (def at module scope).
    METHOD = "method"  # Function defined inside a class body.
    CLASS = "class"  # Class definition.
    TYPE = "type"  # Type alias, TypedDict, dataclass-style type-only def.
    CONST = "const"  # Top-level assignment treated as constant (ALL_CAPS or annotated).
    TEST = "test"  # Function/method that is a test entry point (pytest convention).


class ExternalRefKind(str, Enum):
    """Category of an external (out-of-repo) reference.

    Used for things the call graph cannot resolve symbolically because they live
    outside the codebase (database, network) but are still load-bearing for review.
    """

    DB_TABLE = "db_table"  # Postgres/MySQL/etc. table referenced by name in a SQL string.
    HTTP_ROUTE = "http_route"  # HTTP route attached via decorator or framework registration.
    GRPC_METHOD = "grpc_method"  # gRPC method name registered to a servicer.
    PACKAGE = "package"  # External Python/JS/etc. package import.
    OTHER = "other"  # Catch-all for newly-detected resource kinds.


class ChangeState(str, Enum):
    """Node-level diff overlay.

    Computed by overlaying the unified diff on the AST: a node is `added` if it
    appears only at head_sha, `removed` if only at base_sha, `modified` if any
    hunk overlaps its line range, otherwise `unchanged`.
    """

    UNCHANGED = "unchanged"
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


class HunkChangeType(str, Enum):
    """Hunk-level diff direction. A hunk is the smallest atomic edit unit in a unified diff."""

    ADDED = "added"  # Pure addition (no `-` lines).
    MODIFIED = "modified"  # Mixed +/- lines in the same hunk.
    REMOVED = "removed"  # Pure deletion (no `+` lines).


class EdgeType(str, Enum):
    """Typed, directed edge.

    Allowed source/target kinds per type:
        contains:    Module->File, File->Symbol, File->Hunk
        defines:     Hunk->Symbol  (this hunk creates or modifies the symbol's signature)
        touches:     Hunk->Symbol  (this hunk overlaps body, no signature change)
        calls:       Symbol->Symbol
        references:  Symbol->Symbol  (non-call: type usage, identifier read, attribute access)
        imports:     File->Symbol or File->Module
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


class Confidence(str, Enum):
    """Provenance / certainty of the node or edge.

    `exact`        — derived directly from tree-sitter AST or stack-graphs/SCIP semantic resolution.
    `ambiguous`    — multiple candidates resolved by name; pick is heuristic. UI should badge.
    `llm_inferred` — produced by --llm-enrich. UI must badge distinctly; not authoritative.
    """

    EXACT = "exact"
    AMBIGUOUS = "ambiguous"
    LLM_INFERRED = "llm_inferred"


# ---------- supporting structs ----------


class LineRange(BaseModel):
    """Inclusive 1-indexed line range in a file at a given SHA."""

    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=1, description="1-indexed start line.")
    end: int = Field(ge=1, description="1-indexed end line, inclusive of `start`.")


class PRMetadata(BaseModel):
    """Identifying info for the PR the graph was built from.

    Captures everything needed to reproduce the parse: repo, base/head SHAs,
    branch names, plus surface metadata for UI display.
    """

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="Canonical PR URL (e.g. https://github.com/<org>/<repo>/pull/<n>).")
    repo: str = Field(description="Owner/name slug, e.g. 'connectlyai/connectly-backend'.")
    number: int = Field(ge=1, description="PR number within the repo.")
    title: str = Field(description="PR title at fetch time.")
    author: str = Field(description="Login of PR author.")
    base_ref: str = Field(description="Base branch name (usually 'main').")
    head_ref: str = Field(description="Head branch name.")
    base_sha: str = Field(min_length=7, description="Commit SHA of the base.")
    head_sha: str = Field(min_length=7, description="Commit SHA of the head.")
    additions: int = Field(ge=0, description="Total lines added across all files.")
    deletions: int = Field(ge=0, description="Total lines removed across all files.")
    changed_files: int = Field(ge=0, description="Total file count touched by the PR.")


class Diagnostic(BaseModel):
    """Non-fatal warning emitted during graph construction.

    Used to surface stack-graphs misses, ripgrep ambiguities, schema invariant
    violations, and any LLM enrichment failures. Reviewer-visible.
    """

    model_config = ConfigDict(extra="forbid")

    level: Literal["info", "warn", "error"] = Field(description="Severity of the diagnostic.")
    code: str = Field(description="Stable identifier (e.g. 'STACK_GRAPHS_NO_CALLERS', 'INVARIANT_ORPHAN_EDGE').")
    message: str = Field(description="Human-readable description.")
    related_node_ids: List[str] = Field(
        default_factory=list,
        description="Node IDs this diagnostic refers to. Empty for global diagnostics.",
    )


# ---------- nodes (discriminated union by `kind`) ----------


class _NodeBase(BaseModel):
    """Common fields for all node kinds. Not instantiated directly.

    `id` is the stable, globally-unique identifier within one graph document.
    Recommended id format: `<kind>:<stable-key>` where stable-key is a path,
    qualified name, or hash. The CLI keeps ids deterministic for a given PR.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Globally unique within this graph. Format: '<kind>:<stable-key>'.")
    confidence: Confidence = Field(
        default=Confidence.EXACT,
        description="How certain the resolver is about this node's existence/identity.",
    )
    change_state: ChangeState = Field(
        default=ChangeState.UNCHANGED,
        description="Diff overlay state of this node.",
    )


class ModuleNode(_NodeBase):
    """A logical module — a directory containing source files belonging to one unit."""

    kind: Literal[NodeKind.MODULE] = Field(default=NodeKind.MODULE, description="Discriminator.")
    name: str = Field(description="Dotted or path-shaped module identifier (e.g. 'agent_evaluation').")
    path: str = Field(description="Repo-relative directory path of the module root.")


class FileNode(_NodeBase):
    """A source file at head_sha (or base_sha if removed)."""

    kind: Literal[NodeKind.FILE] = Field(default=NodeKind.FILE, description="Discriminator.")
    path: str = Field(description="Repo-relative file path.")
    language: str = Field(
        description="tree-sitter grammar name, e.g. 'python', 'typescript', 'sql', 'proto'.",
    )
    generated: bool = Field(
        default=False,
        description=(
            "True if classified as generated/codegen (proto-gen, openapi, lockfile, snapshot). "
            "Generated files should be collapsed in UIs by default."
        ),
    )


class SymbolNode(_NodeBase):
    """A named, addressable definition: function, method, class, type, const, or test."""

    kind: Literal[NodeKind.SYMBOL] = Field(default=NodeKind.SYMBOL, description="Discriminator.")
    symbol_kind: SymbolKind = Field(description="Sub-classification of the symbol.")
    name: str = Field(description="Local name without path (e.g. 'query_evaluated_sessions').")
    qualified_name: str = Field(
        description=(
            "Module-rooted dotted name. "
            "Example: 'agent_evaluation.controller.controller.query_evaluated_sessions'."
        ),
    )
    file_id: str = Field(description="ID of the FileNode containing this symbol.")
    line_range: LineRange = Field(
        description="Lines in head_sha where the symbol's definition lives (or base_sha if removed).",
    )
    signature: Optional[str] = Field(
        default=None,
        description="One-line signature when extractable (e.g. 'def foo(a: int) -> str:').",
    )
    public: bool = Field(
        default=False,
        description=(
            "Heuristic: not '_'-prefixed; in __all__; appears in proto/openapi/IDL; "
            "or referenced from outside its declaring module."
        ),
    )


class HunkNode(_NodeBase):
    """A contiguous diff region within a single file. The atomic unit of change."""

    kind: Literal[NodeKind.HUNK] = Field(default=NodeKind.HUNK, description="Discriminator.")
    file_id: str = Field(description="ID of the FileNode this hunk lives in.")
    line_range: LineRange = Field(
        description="Lines at head_sha (or base_sha for removed-only hunks).",
    )
    change_type: HunkChangeType = Field(description="Whether the hunk is added/modified/removed.")
    patch: str = Field(
        description="Unified-diff fragment for this hunk: '@@' header plus +/-/' ' lines.",
    )


class ExternalRefNode(_NodeBase):
    """A reference to a resource outside the codebase (DB table, HTTP route, etc.)."""

    kind: Literal[NodeKind.EXTERNAL_REF] = Field(
        default=NodeKind.EXTERNAL_REF, description="Discriminator."
    )
    ref_kind: ExternalRefKind = Field(description="Category of external resource.")
    name: str = Field(
        description=(
            "Canonical name. Examples: 'ticket_associations' (db_table), "
            "'POST /v1/sessions' (http_route), 'agent_evaluation.v1.QueryEvaluatedSessions' (grpc_method)."
        ),
    )
    detail: Optional[str] = Field(
        default=None,
        description=(
            "Optional structured detail. For db_table: JSON path or column expression used. "
            "For http_route: handler module. Free-form."
        ),
    )


Node = Annotated[
    Union[ModuleNode, FileNode, SymbolNode, HunkNode, ExternalRefNode],
    Field(discriminator="kind"),
]


# ---------- edges ----------


class Edge(BaseModel):
    """Typed directed edge between two nodes.

    Allowed source/target kind combinations are constrained by `EdgeType` semantics
    (see EdgeType docstring). The Graph-level invariant check enforces them at emit.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Globally unique edge id. Format: '<type>:<source_id>->-<target_id>'.")
    type: EdgeType = Field(description="Edge type.")
    source_id: str = Field(description="ID of the source node.")
    target_id: str = Field(description="ID of the target node.")
    confidence: Confidence = Field(
        default=Confidence.EXACT,
        description="Provenance of this edge (resolver determines).",
    )
    change_state: ChangeState = Field(
        default=ChangeState.UNCHANGED,
        description=(
            "Edge-level diff overlay. An edge is `added` if it exists only at head_sha, "
            "`removed` if only at base_sha, `unchanged` otherwise."
        ),
    )
    note: Optional[str] = Field(
        default=None,
        description="Free-text annotation. Especially used for llm_inferred edges to record reasoning.",
    )


# ---------- root ----------


class Graph(BaseModel):
    """Complete impact graph for one PR. Versioned root document.

    Backwards-compatibility: bump `schema_version` on any breaking change.
    Downstream consumers should pin to a major version range.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1.0"] = Field(
        default="0.1.0", description="Semantic version of this schema. Bump on breaking change."
    )
    generated_at: datetime = Field(description="UTC timestamp when the graph was emitted.")
    generator: str = Field(description="Tool name + version, e.g. 'prex 0.1.0'.")
    pr: PRMetadata = Field(description="Identifying info for the PR.")
    nodes: List[Node] = Field(
        description="Heterogeneous node list, discriminated by 'kind'.",
    )
    edges: List[Edge] = Field(description="All edges in the graph.")
    diagnostics: List[Diagnostic] = Field(
        default_factory=list,
        description="Non-fatal warnings emitted during construction.",
    )
    llm_enrichment_used: bool = Field(
        default=False,
        description="True iff at least one node/edge has confidence=llm_inferred.",
    )


__all__ = [
    "ChangeState",
    "Confidence",
    "Diagnostic",
    "Edge",
    "EdgeType",
    "ExternalRefKind",
    "ExternalRefNode",
    "FileNode",
    "Graph",
    "HunkChangeType",
    "HunkNode",
    "LineRange",
    "ModuleNode",
    "Node",
    "NodeKind",
    "PRMetadata",
    "SymbolKind",
    "SymbolNode",
]
