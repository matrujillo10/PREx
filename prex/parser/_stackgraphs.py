"""Cross-file reference resolver.

v0 strategy: stack-graphs is the documented intent (see plan), but its Python
binding requires native build tooling. We therefore start with a **native
Python text-search resolver** that delivers the same edge shape with
`confidence=AMBIGUOUS` when name collision is possible. Stack-graphs swaps in
cleanly later because the public surface here returns the same edge tuples.

What this module does:
    - For each changed Symbol, find candidate caller files by walking the
      local clone (Python only in v0) and scanning for word-boundary name hits.
    - Classify each hit by tree-sitter on the candidate file: is it inside a
      function/method/class body? Is it a `from X import name` statement?
    - Emit `(source_id, target_id, EdgeType, Confidence)` tuples.

What this module deliberately does NOT do:
    - Resolve method-receiver types (no flow analysis).
    - Distinguish two same-named symbols across modules (we mark AMBIGUOUS).
    - Dynamic dispatch / framework wiring (LLM enrichment territory).
"""
from __future__ import annotations

import re
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


_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache"}
_TEST_DIR_HINTS = ("/tests/", "/test/")
_TEST_FILE_PREFIXES = ("test_",)
_TEST_FILE_SUFFIXES = ("_test.py", "_test.ts", "_test.js")

# Names that are too common across Python repos to be useful as cross-ref targets.
# A function called `main` in a changed file resolves to every `main()` in the repo.
COMMON_ENTRYPOINT_NAMES = {
    "main", "handler", "app", "run", "setup", "factory", "wrapper", "decorator",
    "init", "deps", "cli", "fn", "func", "callback", "process", "execute",
    "start", "stop", "close", "open", "read", "write", "send", "receive",
    "load", "save", "get", "set", "update", "delete", "create", "build",
    "wrap", "make", "new", "from_dict", "to_dict", "parse", "format",
    "__init__", "__call__", "__str__", "__repr__",
}

# A name resolved by stack-graphs/text-search where the same name has more than this many
# definition sites repo-wide is considered too ambiguous to emit as a per-edge signal.
# Methods like `async_upsert` defined in 5+ classes produce wrong edges with high confidence
# because text search cannot distinguish receiver types.
MAX_REPO_DEFINITION_SITES = 2

# When a name has this many or more definition sites repo-wide, downgrade emitted edges
# to AMBIGUOUS confidence even if only one of those sites is in the changed-target set.
AMBIGUOUS_DEFINITION_SITES = 2


def is_test_path(rel_or_abs: str) -> bool:
    """Heuristic: file lives in a tests/ dir OR matches a test-naming convention."""
    p = rel_or_abs.replace("\\", "/")
    if any(h in f"/{p.strip('/')}/" for h in _TEST_DIR_HINTS):
        return True
    name = p.rsplit("/", 1)[-1]
    if any(name.startswith(pref) for pref in _TEST_FILE_PREFIXES):
        return True
    if any(name.endswith(suf) for suf in _TEST_FILE_SUFFIXES):
        return True
    return False


def have_ripgrep() -> bool:
    """Always True now — we use native Python search. Kept for API compatibility."""
    return True


def _walk_files(repo_path: Path, suffixes: Iterable[str]) -> List[Path]:
    """Yield candidate files, skipping common noise dirs. Suffixes like ('.py',)."""
    out: List[Path] = []
    suffix_set = set(suffixes)
    for entry in repo_path.rglob("*"):
        if entry.is_dir():
            continue
        # Reject under any skip-dir component
        if any(part in _SKIP_DIRS for part in entry.parts):
            continue
        if entry.suffix in suffix_set:
            out.append(entry)
    return out


def _search_term_in_files(
    files: List[Path],
    term: str,
) -> List[Tuple[str, int, str]]:
    """Word-boundary search for `term` across files. Returns (abs_path, line, text)."""
    pattern = re.compile(r"\b" + re.escape(term) + r"\b")
    hits: List[Tuple[str, int, str]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append((str(f), i, line))
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
    include_tests: bool = False,
) -> List[CrossRef]:
    """Find references to each target symbol across the repo.

    Args:
        repo_path: local clone root.
        targets: {target_qualname: ExtractedSymbol} — symbols to find callers of.
        file_globs: ripgrep -g patterns to scope the search.
        exclude_paths: repo-relative paths to skip (e.g. the file the symbol lives in,
                       to avoid self-loops on definition lines).
        include_tests: when False (default), drop hits from test files. Tests are
                       almost always callers of the changed code; they create
                       graph noise without adding signal beyond a count.

    Returns:
        List of CrossRef. AMBIGUOUS confidence when target name resolves to >1 known target.
    """
    by_name: Dict[str, List[ExtractedSymbol]] = {}
    for sym in targets.values():
        by_name.setdefault(sym.name, []).append(sym)

    excluded = {p.replace("\\", "/") for p in exclude_paths}
    out: List[CrossRef] = []

    # Translate file_globs (e.g. "*.py") to suffixes ('.py').
    suffixes = {("." + g.split(".")[-1]) for g in file_globs if "." in g}
    files = _walk_files(repo_path, suffixes)

    # Build a lightweight global definition-count by name across non-test files
    # so we can skip names that appear as definitions everywhere ("main", "handler",
    # plus repo-specific common methods like "async_upsert").
    def_count_by_name = _count_definition_sites(files, by_name.keys(), include_tests=include_tests)

    for name, sym_list in by_name.items():
        # Skip dunder names — too noisy.
        if name.startswith("__") and name.endswith("__"):
            continue
        # Skip very short or very common names — too many false positives.
        if len(name) < 4:
            continue
        if name in COMMON_ENTRYPOINT_NAMES:
            continue
        if def_count_by_name.get(name, 0) > MAX_REPO_DEFINITION_SITES:
            continue
        hits = _search_term_in_files(files, name)
        seen: set[Tuple[str, int]] = set()
        # Dedup: at most one edge per (source_file, target_qualname) so generated
        # stubs that register a name many times produce one edge instead of many.
        seen_file_target: set[Tuple[str, str]] = set()
        for abs_file, lineno, line_text in hits:
            rel_path = _rel(abs_file, repo_path)
            if rel_path in excluded:
                continue
            if not include_tests and is_test_path(rel_path):
                continue
            # Skip the actual definition site of any of the candidates
            if any(s.start_line == lineno and rel_path.endswith(_qn_to_filename_hint(s.qualified_name)) for s in sym_list):
                continue
            if (rel_path, lineno) in seen:
                continue
            seen.add((rel_path, lineno))
            # File-level dedup: only first edge from a given source file to this target name.
            target_key = sym_list[0].qualified_name if len(sym_list) == 1 else f"~{name}"
            if (rel_path, target_key) in seen_file_target:
                continue
            seen_file_target.add((rel_path, target_key))
            # Even a uniquely-changed-target name can be ambiguous if other places in the
            # repo define the same name. Downgrade confidence accordingly.
            repo_defs = def_count_by_name.get(name, 0)
            if len(sym_list) == 1 and repo_defs >= AMBIGUOUS_DEFINITION_SITES:
                resolved_confidence = Confidence.AMBIGUOUS
            elif len(sym_list) == 1:
                resolved_confidence = Confidence.EXACT
            else:
                resolved_confidence = Confidence.AMBIGUOUS
            edge_type = _classify_edge(line_text, name)
            enclosing, _all_syms = _enclosing_symbol(repo_path, rel_path, lineno)
            confidence = resolved_confidence
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


_DEF_RE_TEMPLATE = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)\s*[\(:]")


def _count_definition_sites(files: List[Path], names: Iterable[str], *, include_tests: bool) -> Dict[str, int]:
    """For each name in `names`, count distinct files where it appears as `def name` or `class name`.

    Conservative: scan each file once, regex over lines. Skips test files when not including tests.
    """
    name_set = set(names)
    if not name_set:
        return {}
    counts: Dict[str, int] = {n: 0 for n in name_set}
    for f in files:
        rel = str(f)
        if not include_tests and is_test_path(rel):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        seen_in_file: set[str] = set()
        for line in text.splitlines():
            m = _DEF_RE_TEMPLATE.match(line)
            if not m:
                continue
            n = m.group(1)
            if n in name_set and n not in seen_in_file:
                counts[n] += 1
                seen_in_file.add(n)
    return counts


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
