"""Schemas for PREx output artifacts.

Three modules:
    - `_shared`  Citation, Diagnostic, LineRange, ChangeState, Derivation.
    - `graph`    Graph + Node (Module/File/Symbol/CallerStub/Hunk/ExternalRef) + Edge + PRMetadata.
    - `brief`    Brief + ReviewBrief + ReviewPlan + HunkInsight + ChecklistBinding (+ supporting models).

Public API: `from prex.schemas import Brief, Graph, Citation, ...`.
"""
from prex.schemas._shared import (
    ChangeState,
    Citation,
    Derivation,
    Diagnostic,
    LineRange,
)
from prex.schemas.brief import (
    AdvisoryFlag,
    BlastRadius,
    Brief,
    ChecklistBinding,
    ChecklistItem,
    ChecklistStatus,
    HunkInsight,
    HunkIntent,
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
    Edge,
    EdgeType,
    ExternalRefKind,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkChangeType,
    HunkNode,
    ModuleNode,
    Node,
    NodeKind,
    PRMetadata,
    SymbolKind,
    SymbolNode,
)

__all__ = [
    "AdvisoryFlag",
    "BlastRadius",
    "Brief",
    "CallerStub",
    "ChangeState",
    "ChecklistBinding",
    "ChecklistItem",
    "ChecklistStatus",
    "Citation",
    "Derivation",
    "Diagnostic",
    "Edge",
    "EdgeType",
    "ExternalRefKind",
    "ExternalRefNode",
    "FileNode",
    "Graph",
    "HunkChangeType",
    "HunkInsight",
    "HunkIntent",
    "HunkNode",
    "LineRange",
    "ModuleNode",
    "Node",
    "NodeKind",
    "Novelty",
    "Novelty",
    "PRMetadata",
    "PRType",
    "ReviewBrief",
    "ReviewPlan",
    "ReviewStep",
    "RiskSignal",
    "RiskTier",
    "SymbolKind",
    "SymbolNode",
]
