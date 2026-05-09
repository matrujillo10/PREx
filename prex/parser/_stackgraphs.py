"""Cross-file reference resolver.

v0 strategy: stack-graphs is the documented intent (see plan), but the Python
binding (`tree_sitter_stack_graphs`) is not yet stable enough to ship as a
hard dependency on macOS without native build tooling. We therefore start with
a **ripgrep-based resolver** that delivers the same edges with `confidence` set
to AMBIGUOUS when name collision is possible. Stack-graphs swaps in cleanly
later because the public surface here returns the same edge tuples.

What this module does:
    - For each changed Symbol, find candidate caller files via ripgrep over
      the local clone (Python only in v0).
    - Classify each hit by tree-sitter on the candidate file: is it inside a
      function/method/class body? Is it a `from X import name` statement?
    - Emit `(source_id, target_id, EdgeType, Confidence)` tuples.

What this module deliberately does NOT do:
    - Resolve method-receiver types (no flow analysis).
    - Distinguish two same-named symbols across modules (we mark AMBIGUOUS).
    - Dynamic dispatch / framework wiring (LLM enrichment territory).
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from prex.parser._treesitter import (
    ExtractedSymbol,
    PY_LANGUAGE,
    _PARSER,
    extract_symbols,
)
from prex.schemas.graph import Confidence, EdgeType


@dataclass
class CrossRef:
    """One reference to a target symbol from a source file/symbol."""

    source_file: str  # repo-relative path of the file containing the reference
    source_symbol_qualname: Optional[str]  # qualified name of enclosing symbol, if any
    target_name: str
    target_qualname: Optional[str]  # set when uniquely resolvable; None means AMBIGUOUS
    line: int  # 1-indexed line of the reference
    edge_type: EdgeType
    confidence: Confidence


def have_ripgrep() -> bool:
    return shutil.which("rg") is not None


def _rg_search(repo_path: Path, term: str, globs: Iterable[str]) -> List[Tuple[str, int, str]]:
    """Run ripgrep with word-boundary search. Returns list of (file, line, line_text)."""
    if not have_ripgrep():
        return []
    cmd = [
        "rg", "--no-heading", "--with-filename", "--line-number",
        "--word-regexp", "--fixed-strings",
    ]
    for g in globs:
        cmd.extend(["-g", g])
    cmd.extend([term, str(repo_path)])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception:
        return []
    hits: List[Tuple[str, int, str]] = []
    for line in out.stdout.splitlines():
        # format: <abs_path>:<lineno>:<text>
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file, lineno, text = parts
        try:
            hits.append((file, int(lineno), text))
        except ValueError:
            continue
    return hits


def _rel(path: str, repo_path: Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(repo_path.resolve())).replace("\\", "/")
    except ValueError:
        return str(p)


def _enclosing_symbol(
    repo_path: Path,
    rel_path: str,
    line: int,
) -> Tuple[Optional[ExtractedSymbol], List[ExtractedSymbol]]:
    """Return the innermost symbol whose line range contains `line`, plus full list (cached caller)."""
    abs_path = repo_path / rel_path
    if not abs_path.exists():
        return None, []
    try:
        src = abs_path.read_bytes()
    except Exception:
        return None, []
    syms = extract_symbols(src, rel_path)
    enclosing = None
    for s in syms:
        if s.start_line <= line <= s.end_line:
            if enclosing is None or (s.start_line >= enclosing.start_line and s.end_line <= enclosing.end_line):
                enclosing = s
    return enclosing, syms


def _classify_edge(line_text: str, target_name: str) -> EdgeType:
    """Heuristic edge classification from the textual line."""
    t = line_text.strip()
    if t.startswith("from ") and " import " in t and target_name in t.split(" import ", 1)[1]:
        return EdgeType.IMPORTS
    if t.startswith("import ") and target_name in t.split("import ", 1)[1]:
        return EdgeType.IMPORTS
    if f"{target_name}(" in line_text:
        return EdgeType.CALLS
    return EdgeType.REFERENCES


def find_cross_refs(
    repo_path: Path,
    targets: Dict[str, ExtractedSymbol],
    *,
    file_globs: Iterable[str] = ("*.py",),
    exclude_paths: Iterable[str] = (),
) -> List[CrossRef]:
    """Find references to each target symbol across the repo.

    Args:
        repo_path: local clone root.
        targets: {target_qualname: ExtractedSymbol} — symbols to find callers of.
        file_globs: ripgrep -g patterns to scope the search.
        exclude_paths: repo-relative paths to skip (e.g. the file the symbol lives in,
                       to avoid self-loops on definition lines).

    Returns:
        List of CrossRef. AMBIGUOUS confidence when target name resolves to >1 known target.
    """
    by_name: Dict[str, List[ExtractedSymbol]] = {}
    for sym in targets.values():
        by_name.setdefault(sym.name, []).append(sym)

    excluded = {p.replace("\\", "/") for p in exclude_paths}
    out: List[CrossRef] = []

    for name, sym_list in by_name.items():
        # Skip dunder names — too noisy.
        if name.startswith("__") and name.endswith("__"):
            continue
        hits = _rg_search(repo_path, name, file_globs)
        seen: set[Tuple[str, int]] = set()
        for abs_file, lineno, line_text in hits:
            rel_path = _rel(abs_file, repo_path)
            if rel_path in excluded:
                continue
            # Skip the actual definition site of any of the candidates
            if any(s.start_line == lineno and rel_path.endswith(_qn_to_filename_hint(s.qualified_name)) for s in sym_list):
                continue
            if (rel_path, lineno) in seen:
                continue
            seen.add((rel_path, lineno))
            edge_type = _classify_edge(line_text, name)
            enclosing, _all_syms = _enclosing_symbol(repo_path, rel_path, lineno)
            confidence = Confidence.EXACT if len(sym_list) == 1 else Confidence.AMBIGUOUS
            target_qn = sym_list[0].qualified_name if len(sym_list) == 1 else None
            out.append(
                CrossRef(
                    source_file=rel_path,
                    source_symbol_qualname=enclosing.qualified_name if enclosing else None,
                    target_name=name,
                    target_qualname=target_qn,
                    line=lineno,
                    edge_type=edge_type,
                    confidence=confidence,
                )
            )
    return out


def _qn_to_filename_hint(qualname: str) -> str:
    """Best-effort: '<pkg>.<mod>.<ClassOrFn>...' -> '<mod>.py' or just last segment.

    Only used to suppress definition-line hits as references. Not authoritative.
    """
    parts = qualname.split(".")
    # Strip class+symbol tail; the first non-PascalCase segment is the module.
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] and parts[i][0].islower() and "_" not in parts[i][:1]:
            return f"{parts[i]}.py"
    return f"{parts[-1]}.py"
