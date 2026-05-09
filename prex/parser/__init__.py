"""prex.parser — PR-to-graph pipeline.

Public API:
    parse_pr(url: str, *, llm_enrich: bool = False, work_dir: Path | None = None) -> Graph

All collaborator modules (`_pr`, `_diff`, `_treesitter`, `_stackgraphs`, `_external`,
`_enrich`, `_emit`) are private. Stable surface is `parser.parse_pr` and the schemas.
"""
from prex.parser.parse import parse_pr

__all__ = ["parse_pr"]
