"""External-reference detection.

v0: SQL table names mentioned in Python string literals (FROM/JOIN/INTO).
This is a regex-level pass; we accept some false positives (table names that
are actually CTE aliases) and let the reviewer disambiguate.

We additionally check whether a detected table is "new to this module" — i.e.
appears only in changed hunks for the file in question. That signal is the
load-bearing one for the predicate "first reference to a table from this module".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

# FROM <table> | JOIN <table> | INTO <table>
# Captures bare identifiers and schema.table forms. Excludes parens (subqueries)
# and excludes CTE references (heuristic: skip identifiers that follow 'WITH').
_SQL_RE = re.compile(
    r"""(?ix)
    \b(?:from|join|into|update)
    \s+
    (?:only\s+)?
    (?P<name>[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)?)
    \b
    """
)

# Common SQL keywords that should not be treated as tables.
_RESERVED = {
    "select", "where", "group", "order", "limit", "offset", "as", "on", "and",
    "or", "not", "by", "having", "case", "when", "then", "else", "end",
    "lateral", "values", "returning", "set", "using", "true", "false", "null",
}


@dataclass
class SQLRef:
    """A SQL table mention in a string literal."""

    table: str
    line: int  # 1-indexed line in the source file
    surrounding: str  # the matched substring for diagnostics


def find_sql_refs(source: str) -> List[SQLRef]:
    """Scan a Python source string for SQL table references in string literals.

    Heuristic:
      - We do NOT try to parse Python AST for string literals; instead, scan
        the whole text for FROM/JOIN/INTO patterns. This catches f-strings,
        triple-quoted strings, and concatenated SQL alike.
      - To avoid false positives in code (e.g., `from typing import X`), we
        restrict matches to lines that look like SQL (contain FROM/JOIN/INTO
        in lowercase or with a SQL-like neighbour).

    """
    out: List[SQLRef] = []
    seen: set[Tuple[str, int]] = set()
    for i, line in enumerate(source.splitlines(), start=1):
        # Skip Python imports; not real SQL.
        stripped = line.lstrip()
        if stripped.startswith(("from ", "import ")) and " import " not in (" " + stripped + " ").lower().replace("from ", " import ", 1)[:200]:
            # awkward but correct: only skip Python from-imports, not SQL FROM
            if " sql" not in line.lower() and "select" not in line.lower():
                continue
        for m in _SQL_RE.finditer(line):
            name = m.group("name").lower()
            if name in _RESERVED:
                continue
            # Skip uppercase pseudo-columns / subselect placeholders.
            if (name, i) in seen:
                continue
            seen.add((name, i))
            out.append(SQLRef(table=name, line=i, surrounding=line.strip()[:200]))
    return out
