"""Generate JSON Schemas for PREx output models.

Writes:
    prex/schemas/dist/shared.schema.json
    prex/schemas/dist/graph.schema.json
    prex/schemas/dist/brief.schema.json
    prex/schemas/dist/combined.schema.json   (one file with all definitions)

Run via: `python -m prex.schemas.gen`.
"""
from __future__ import annotations

import json
from pathlib import Path

from prex.schemas._shared import Citation, ChangeState, Derivation, Diagnostic, LineRange
from prex.schemas.brief import (
    Brief,
    BlastRadius,
    ChecklistBinding,
    ChecklistItem,
    HunkInsight,
    Novelty,
    ReviewBrief,
    ReviewPlan,
    ReviewStep,
)
from prex.schemas.graph import (
    CallerStub,
    Edge,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkNode,
    ModuleNode,
    PRMetadata,
    SymbolNode,
)


_DIST = Path(__file__).parent / "dist"


def _emit_schema(model, name: str) -> None:
    schema = model.model_json_schema(mode="serialization")
    out = _DIST / f"{name}.schema.json"
    out.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n")
    print(f"wrote {out}")


def _emit_combined() -> None:
    """Emit one combined schema file containing every public model under $defs."""
    defs: dict = {}
    titles = []
    for model in (
        # shared primitives
        LineRange,
        Citation,
        Diagnostic,
        # graph
        PRMetadata,
        ModuleNode,
        FileNode,
        SymbolNode,
        CallerStub,
        HunkNode,
        ExternalRefNode,
        Edge,
        Graph,
        # brief
        BlastRadius,
        Novelty,
        ReviewBrief,
        ReviewStep,
        ReviewPlan,
        HunkInsight,
        ChecklistItem,
        ChecklistBinding,
        Brief,
    ):
        s = model.model_json_schema(mode="serialization")
        title = s.get("title", model.__name__)
        defs[title] = s
        titles.append(title)
    combined = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PREx output (combined)",
        "description": (
            "All models PREx emits across `output/graph.json` and `output/brief.json`. "
            "Use `Graph` and `Brief` as the two top-level documents."
        ),
        "$defs": defs,
        "topLevel": ["Graph", "Brief"],
    }
    out = _DIST / "combined.schema.json"
    out.write_text(json.dumps(combined, indent=2, sort_keys=False) + "\n")
    print(f"wrote {out}")


def main() -> None:
    _DIST.mkdir(parents=True, exist_ok=True)
    # Per-module top-level schemas (each one inlines its $defs).
    _emit_schema(Graph, "graph")
    _emit_schema(Brief, "brief")
    # Shared primitives shipped as a single schema referencing each model.
    shared = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PREx shared primitives",
        "description": "Models reused across graph.json and brief.json.",
        "$defs": {
            "LineRange": LineRange.model_json_schema(mode="serialization"),
            "Citation": Citation.model_json_schema(mode="serialization"),
            "Diagnostic": Diagnostic.model_json_schema(mode="serialization"),
        },
    }
    (_DIST / "shared.schema.json").write_text(json.dumps(shared, indent=2) + "\n")
    print(f"wrote {_DIST / 'shared.schema.json'}")
    _emit_combined()


if __name__ == "__main__":
    main()
