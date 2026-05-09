"""External-reference detection.

v0: SQL table names mentioned in Python string literals (FROM/JOIN/INTO/UPDATE).

Filters applied in order:
  1. Match `FROM/JOIN/INTO/UPDATE <name>` patterns in lowercase SQL.
  2. Skip SQL reserved words.
  3. Skip CTE-defined names (any identifier appearing in a `WITH x AS (`).
  4. Skip names starting with `_` (temp-table convention) and names of length < 3.
  5. Skip Python `from x import y` lines (not SQL).
  6. `find_new_sql_refs(head, base)` returns only tables present in head but not base.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set, Tuple

_SQL_RE = re.compile(
    r"""(?ix)
    \b(?:from|join|into|update)
    \s+
    (?:only\s+)?
    (?P<name>[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)?)
    \b
    """
)

# CTE detector: matches "WITH name AS (" or ", name AS (" patterns.
_CTE_RE = re.compile(r"(?i)(?:^|,|\bWITH\b)\s+([a-z_][a-z0-9_]*)\s+AS\s*\(")

_RESERVED = {
    "select", "where", "group", "order", "limit", "offset", "as", "on", "and",
    "or", "not", "by", "having", "case", "when", "then", "else", "end",
    "lateral", "values", "returning", "set", "using", "true", "false", "null",
    "distinct", "all", "any", "exists", "in", "is", "like", "between", "with",
    "left", "right", "inner", "outer", "full", "cross", "natural", "concat",
}


@dataclass
class SQLRef:
    """A SQL table mention in a string literal."""

    table: str
    line: int  # 1-indexed line in the source file
    surrounding: str


def _collect_cte_names(source: str) -> Set[str]:
    """Identifiers introduced by `WITH x AS (` clauses anywhere in the source."""
    return {m.group(1).lower() for m in _CTE_RE.finditer(source)}


def find_sql_refs(source: str) -> List[SQLRef]:
    """Scan a Python source string for SQL table references in string literals."""
    cte_names = _collect_cte_names(source)
    out: List[SQLRef] = []
    seen: Set[Tuple[str, int]] = set()
    for i, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        # Skip Python from-imports.
        if stripped.startswith(("from ", "import ")):
            if "select" not in line.lower() and "join" not in line.lower():
                continue
        for m in _SQL_RE.finditer(line):
            name = m.group("name").lower()
            if name in _RESERVED:
                continue
            if name in cte_names:
                continue
            if name.startswith("_"):
                continue
            base_name = name.split(".")[-1]
            if len(base_name) < 3:
                continue
            if (name, i) in seen:
                continue
            seen.add((name, i))
            out.append(SQLRef(table=name, line=i, surrounding=line.strip()[:200]))
    return out


def find_new_sql_refs(head_source: str, base_source: Optional[str]) -> List[SQLRef]:
    """Return SQL refs present in head but not in base.

    "New" is defined as: table name appears in head_source's set of refs but
    not in base_source's. Useful for the 'first-time external dep' predicate.
    """
    head_refs = find_sql_refs(head_source)
    if base_source is None:
        return head_refs
    base_tables = {r.table for r in find_sql_refs(base_source)}
    return [r for r in head_refs if r.table not in base_tables]
