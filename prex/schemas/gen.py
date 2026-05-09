"""Generate prex/schemas/graph.schema.json from the Pydantic source of truth."""
from __future__ import annotations

import json
from pathlib import Path

from prex.schemas.graph import Graph


def main() -> None:
    schema = Graph.model_json_schema()
    out = Path(__file__).parent / "graph.schema.json"
    out.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
