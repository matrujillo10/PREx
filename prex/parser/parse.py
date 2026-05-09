"""parse_pr orchestrator. Composes _pr / _diff / _treesitter / _stackgraphs / _external / _enrich / _emit."""
from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Set, Tuple

from prex.parser import _diff, _enrich, _external, _pr, _stackgraphs, _treesitter
from prex.parser._stackgraphs import CrossRef
from prex.parser._treesitter import ExtractedSymbol
from prex.schemas.graph import (
    ChangeState,
    Confidence,
    Diagnostic,
    Edge,
    EdgeType,
    ExternalRefKind,
    ExternalRefNode,
    FileNode,
    Graph,
    HunkChangeType,
    HunkNode,
    LineRange,
    ModuleNode,
    NodeKind,
    PRMetadata,
    SymbolKind,
    SymbolNode,
)


GENERATED_PATTERNS = (
    "idl/gen/*",
    "*/gen/*",
    "*_pb2.py",
    "*_pb2.pyi",
    "*_pb2_grpc.py",
    "*.pb.go",
    "*.swagger.json",
    "*ts_proto*",
)

LANGUAGE_BY_EXT = {
    ".py": "python",
    ".pyi": "python",
    ".proto": "proto",
    ".sql": "sql",
    ".go": "go",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _is_generated(path: str) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in GENERATED_PATTERNS)


def _language_of(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return LANGUAGE_BY_EXT.get(suffix, "unknown")


def _git_show(repo_path: Path, sha: str, file_path: str) -> Optional[bytes]:
    try:
        out = subprocess.run(
            ["git", "show", f"{sha}:{file_path}"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def _node_id(prefix: str, key: str) -> str:
    safe = key.replace(":", "_")
    return f"{prefix}:{safe}"


def _module_for_file(rel_path: str) -> Tuple[str, str]:
    """Return (module_id, module_name) — module is the file's parent directory."""
    parent = PurePosixPath(rel_path).parent.as_posix()
    name = parent.replace("/", ".") if parent and parent != "." else "(root)"
    return _node_id("module", parent or "."), name


@dataclass
class _BuiltSymbol:
    """Internal record: extracted symbol with its assigned node id and change_state."""
    extracted: ExtractedSymbol
    file_id: str
    rel_path: str
    node_id: str
    change_state: ChangeState


def parse_pr(
    url: str,
    *,
    llm_enrich: bool = False,
    work_dir: Optional[Path] = None,
) -> Graph:
    """Resolve a PR, parse the diff, build the impact graph.

    Args:
        url: GitHub PR URL.
        llm_enrich: When True, run LLM enrichment for zero-caller public symbols
                    and other ambiguous resolutions. Requires ANTHROPIC_API_KEY.
        work_dir: Local clone cache root. Defaults to ~/.cache/prex/repos.

    Returns:
        A complete `Graph` with nodes, edges, diagnostics, and PRMetadata.
    """
    diagnostics: List[Diagnostic] = []
    nodes: List = []
    edges: List[Edge] = []

    # 1. Resolve PR ----------------------------------------------------------
    resolved = _pr.resolve(url, work_dir=work_dir)
    pr_meta = resolved.metadata
    repo_path = resolved.repo_path
    raw_diff = resolved.raw_diff

    # 2. Parse diff ----------------------------------------------------------
    file_diffs = _diff.parse(raw_diff)

    # 3. For each changed file, build File / Hunk / Symbol nodes -------------
    modules_seen: Set[str] = set()
    files_by_path: Dict[str, FileNode] = {}
    built_symbols_by_qn: Dict[str, _BuiltSymbol] = {}
    file_node_id_by_path: Dict[str, str] = {}

    # changed Python files we'll find cross-refs FOR (the targets)
    changed_python_files: List[str] = []

    for fd in file_diffs:
        rel_path = fd.path
        if not rel_path:
            continue
        lang = _language_of(rel_path)
        generated = _is_generated(rel_path)

        # Module + File nodes
        module_id, module_name = _module_for_file(rel_path)
        if module_id not in modules_seen:
            modules_seen.add(module_id)
            module_node = ModuleNode(
                id=module_id,
                name=module_name,
                path=str(PurePosixPath(rel_path).parent),
            )
            nodes.append(module_node)

        if fd.is_deleted:
            file_change_state = ChangeState.REMOVED
        elif fd.is_new:
            file_change_state = ChangeState.ADDED
        else:
            file_change_state = ChangeState.MODIFIED

        file_id = _node_id("file", rel_path)
        file_node = FileNode(
            id=file_id,
            path=rel_path,
            language=lang,
            generated=generated,
            change_state=file_change_state,
        )
        files_by_path[rel_path] = file_node
        file_node_id_by_path[rel_path] = file_id
        nodes.append(file_node)
        edges.append(
            Edge(
                id=_node_id("contains", f"{module_id}->{file_id}"),
                type=EdgeType.CONTAINS,
                source_id=module_id,
                target_id=file_id,
            )
        )

        # Hunk nodes
        for h_idx, hunk in enumerate(fd.hunks):
            h_start, h_end = hunk.head_line_range
            change_type = HunkChangeType(hunk.change_type)
            hunk_id = _node_id("hunk", f"{rel_path}#{h_idx}")
            hunk_node = HunkNode(
                id=hunk_id,
                file_id=file_id,
                line_range=LineRange(start=max(1, h_start), end=max(h_start, h_end)),
                change_type=change_type,
                patch=hunk.text,
                change_state=ChangeState.MODIFIED if change_type == HunkChangeType.MODIFIED else (ChangeState.ADDED if change_type == HunkChangeType.ADDED else ChangeState.REMOVED),
            )
            nodes.append(hunk_node)
            edges.append(
                Edge(
                    id=_node_id("contains", f"{file_id}->{hunk_id}"),
                    type=EdgeType.CONTAINS,
                    source_id=file_id,
                    target_id=hunk_id,
                )
            )

        # Symbols: only extract for Python (v0)
        if lang != "python" or generated or fd.is_deleted:
            continue
        changed_python_files.append(rel_path)

        head_src = _git_show(repo_path, pr_meta.head_sha, rel_path)
        if head_src is None:
            diagnostics.append(
                Diagnostic(
                    level="warn",
                    code="MISSING_FILE_AT_HEAD",
                    message=f"Could not read {rel_path} at head_sha={pr_meta.head_sha}",
                    related_node_ids=[file_id],
                )
            )
            continue

        head_syms = _treesitter.extract_symbols(head_src, rel_path)
        base_src = _git_show(repo_path, pr_meta.base_sha, rel_path)
        base_syms = _treesitter.extract_symbols(base_src, rel_path) if base_src else []
        base_qns: Set[str] = {s.qualified_name for s in base_syms}

        for sym in head_syms:
            change_state = ChangeState.UNCHANGED
            sym_range = (sym.start_line, sym.end_line)
            for hunk in fd.hunks:
                if _diff.overlaps(sym_range, hunk.head_line_range):
                    change_state = ChangeState.MODIFIED
                    break
            if sym.qualified_name not in base_qns:
                change_state = ChangeState.ADDED

            sym_id = _node_id("symbol", sym.qualified_name)
            sym_node = SymbolNode(
                id=sym_id,
                symbol_kind=SymbolKind(sym.kind),
                name=sym.name,
                qualified_name=sym.qualified_name,
                file_id=file_id,
                line_range=LineRange(start=sym.start_line, end=sym.end_line),
                signature=sym.signature,
                public=sym.public,
                change_state=change_state,
            )
            nodes.append(sym_node)
            edges.append(
                Edge(
                    id=_node_id("contains", f"{file_id}->{sym_id}"),
                    type=EdgeType.CONTAINS,
                    source_id=file_id,
                    target_id=sym_id,
                )
            )
            built_symbols_by_qn[sym.qualified_name] = _BuiltSymbol(
                extracted=sym,
                file_id=file_id,
                rel_path=rel_path,
                node_id=sym_id,
                change_state=change_state,
            )

            # Defines / touches edges from hunks to this symbol
            for h_idx, hunk in enumerate(fd.hunks):
                if not _diff.overlaps(sym_range, hunk.head_line_range):
                    continue
                hunk_id = _node_id("hunk", f"{rel_path}#{h_idx}")
                # Heuristic for defines vs touches: signature line overlap means defines
                signature_line = sym.start_line
                signature_overlap = hunk.head_line_range[0] <= signature_line <= hunk.head_line_range[1]
                edge_type = EdgeType.DEFINES if signature_overlap or change_state == ChangeState.ADDED else EdgeType.TOUCHES
                edges.append(
                    Edge(
                        id=_node_id(edge_type.value, f"{hunk_id}->{sym_id}"),
                        type=edge_type,
                        source_id=hunk_id,
                        target_id=sym_id,
                        change_state=change_state,
                    )
                )

        # Removed symbols (in base but not in head)
        head_qns = {s.qualified_name for s in head_syms}
        for sym in base_syms:
            if sym.qualified_name in head_qns:
                continue
            sym_id = _node_id("symbol", sym.qualified_name)
            sym_node = SymbolNode(
                id=sym_id,
                symbol_kind=SymbolKind(sym.kind),
                name=sym.name,
                qualified_name=sym.qualified_name,
                file_id=file_id,
                line_range=LineRange(start=sym.start_line, end=sym.end_line),
                signature=sym.signature,
                public=sym.public,
                change_state=ChangeState.REMOVED,
            )
            nodes.append(sym_node)
            built_symbols_by_qn[sym.qualified_name] = _BuiltSymbol(
                extracted=sym,
                file_id=file_id,
                rel_path=rel_path,
                node_id=sym_id,
                change_state=ChangeState.REMOVED,
            )

        # SQL external refs: scan changed-hunk lines only.
        head_text = head_src.decode("utf-8", errors="replace")
        head_lines = head_text.splitlines()
        sql_refs = _external.find_sql_refs(head_text)
        seen_tables: Set[str] = set()
        for ref in sql_refs:
            # Only emit refs whose line is inside a changed hunk
            in_change = any(
                hunk.head_line_range[0] <= ref.line <= hunk.head_line_range[1]
                for hunk in fd.hunks
            )
            if not in_change:
                continue
            if ref.table in seen_tables:
                continue
            seen_tables.add(ref.table)
            ext_id = _node_id("external_ref", f"db_table:{ref.table}")
            existing = next((n for n in nodes if isinstance(n, ExternalRefNode) and n.id == ext_id), None)
            if existing is None:
                ext_node = ExternalRefNode(
                    id=ext_id,
                    ref_kind=ExternalRefKind.DB_TABLE,
                    name=ref.table,
                    detail=ref.surrounding,
                    change_state=ChangeState.ADDED,
                )
                nodes.append(ext_node)
            # Edge from enclosing symbol to the external ref
            enclosing = None
            for sym in head_syms:
                if sym.start_line <= ref.line <= sym.end_line:
                    if enclosing is None or (sym.start_line >= enclosing.start_line):
                        enclosing = sym
            if enclosing is None:
                continue
            sym_id = _node_id("symbol", enclosing.qualified_name)
            edges.append(
                Edge(
                    id=_node_id("external", f"{sym_id}->{ext_id}:{ref.line}"),
                    type=EdgeType.EXTERNAL,
                    source_id=sym_id,
                    target_id=ext_id,
                    change_state=ChangeState.ADDED,
                )
            )

    # 4. Cross-file references: for each changed Symbol, find callers --------
    target_symbols: Dict[str, ExtractedSymbol] = {
        qn: bs.extracted
        for qn, bs in built_symbols_by_qn.items()
        if bs.change_state in (ChangeState.MODIFIED, ChangeState.ADDED)
    }

    if not _stackgraphs.have_ripgrep():
        diagnostics.append(
            Diagnostic(
                level="warn",
                code="RIPGREP_MISSING",
                message="ripgrep not found; cross-file references will be empty.",
            )
        )
        cross_refs: List[CrossRef] = []
    else:
        cross_refs = _stackgraphs.find_cross_refs(
            repo_path,
            target_symbols,
            file_globs=("*.py",),
            exclude_paths=changed_python_files,  # exclude same-file (we already have intra-file edges via hunk overlap)
        )

    # 5. Materialise caller nodes + edges from cross-refs --------------------
    extra_files: Dict[str, FileNode] = {}
    extra_symbols: Dict[str, _BuiltSymbol] = {}

    for cr in cross_refs:
        if cr.target_qualname is None:
            # Ambiguous — try best guess: pick first match by name
            candidates = [bs for bs in built_symbols_by_qn.values() if bs.extracted.name == cr.target_name]
            if not candidates:
                continue
            target_node_id = candidates[0].node_id
            confidence = Confidence.AMBIGUOUS
            note = f"Ambiguous: {len(candidates)} candidates with name {cr.target_name}."
        else:
            bs = built_symbols_by_qn.get(cr.target_qualname)
            if bs is None:
                continue
            target_node_id = bs.node_id
            confidence = cr.confidence
            note = None

        # Caller file
        caller_file = cr.source_file
        if caller_file not in files_by_path and caller_file not in extra_files:
            mid, mname = _module_for_file(caller_file)
            if mid not in modules_seen:
                modules_seen.add(mid)
                nodes.append(ModuleNode(id=mid, name=mname, path=str(PurePosixPath(caller_file).parent)))
            file_id = _node_id("file", caller_file)
            file_node = FileNode(
                id=file_id,
                path=caller_file,
                language=_language_of(caller_file),
                generated=_is_generated(caller_file),
                change_state=ChangeState.UNCHANGED,
            )
            extra_files[caller_file] = file_node
            file_node_id_by_path[caller_file] = file_id
            nodes.append(file_node)
            edges.append(
                Edge(
                    id=_node_id("contains", f"{mid}->{file_id}"),
                    type=EdgeType.CONTAINS,
                    source_id=mid,
                    target_id=file_id,
                )
            )

        # Caller symbol
        source_sym_id: Optional[str] = None
        if cr.source_symbol_qualname:
            qn = cr.source_symbol_qualname
            if qn in built_symbols_by_qn:
                source_sym_id = built_symbols_by_qn[qn].node_id
            elif qn in extra_symbols:
                source_sym_id = extra_symbols[qn].node_id
            else:
                # Materialise caller symbol node
                # Re-extract enclosing symbol details; we already have line via cross_refs source line
                file_id = file_node_id_by_path[caller_file]
                # Re-parse to get the symbol's line range
                try:
                    src_bytes = (repo_path / caller_file).read_bytes()
                except Exception:
                    src_bytes = None
                enclosing_sym: Optional[ExtractedSymbol] = None
                if src_bytes:
                    for s in _treesitter.extract_symbols(src_bytes, caller_file):
                        if s.qualified_name == qn:
                            enclosing_sym = s
                            break
                if enclosing_sym is not None:
                    sym_id = _node_id("symbol", enclosing_sym.qualified_name)
                    nodes.append(
                        SymbolNode(
                            id=sym_id,
                            symbol_kind=SymbolKind(enclosing_sym.kind),
                            name=enclosing_sym.name,
                            qualified_name=enclosing_sym.qualified_name,
                            file_id=file_id,
                            line_range=LineRange(start=enclosing_sym.start_line, end=enclosing_sym.end_line),
                            signature=enclosing_sym.signature,
                            public=enclosing_sym.public,
                            change_state=ChangeState.UNCHANGED,
                        )
                    )
                    edges.append(
                        Edge(
                            id=_node_id("contains", f"{file_id}->{sym_id}"),
                            type=EdgeType.CONTAINS,
                            source_id=file_id,
                            target_id=sym_id,
                        )
                    )
                    extra_symbols[qn] = _BuiltSymbol(
                        extracted=enclosing_sym,
                        file_id=file_id,
                        rel_path=caller_file,
                        node_id=sym_id,
                        change_state=ChangeState.UNCHANGED,
                    )
                    source_sym_id = sym_id

        # If no enclosing symbol, the source is the file itself (typical for module-level imports)
        edge_source = source_sym_id or file_node_id_by_path[caller_file]
        edge_id = _node_id(cr.edge_type.value, f"{edge_source}->{target_node_id}:{cr.source_file}:{cr.line}")
        edges.append(
            Edge(
                id=edge_id,
                type=cr.edge_type,
                source_id=edge_source,
                target_id=target_node_id,
                confidence=confidence,
                note=note,
            )
        )

    # 6. Test-coverage inference (naming convention) -------------------------
    for bs in extra_symbols.values():
        if bs.extracted.kind != "test":
            continue
        # try to map back to a tested module by stripping leading 'test_' / parent path
        candidate = _treesitter.PY_LANGUAGE  # placeholder; reuse symbols_by_name lookup
        for target_qn, target_bs in built_symbols_by_qn.items():
            if target_bs.extracted.name and target_bs.extracted.name in bs.extracted.qualified_name:
                edges.append(
                    Edge(
                        id=_node_id("covers", f"{bs.node_id}->{target_bs.node_id}"),
                        type=EdgeType.COVERS,
                        source_id=bs.node_id,
                        target_id=target_bs.node_id,
                        confidence=Confidence.AMBIGUOUS,
                        note="Heuristic: test-name substring match.",
                    )
                )

    # 7. LLM enrichment (optional) ------------------------------------------
    llm_used = False
    if llm_enrich:
        zero_caller_pubs = []
        edges_by_target: Dict[str, List[Edge]] = {}
        for e in edges:
            edges_by_target.setdefault(e.target_id, []).append(e)
        for bs in built_symbols_by_qn.values():
            if not bs.extracted.public:
                continue
            if bs.change_state == ChangeState.UNCHANGED:
                continue
            inbound = [e for e in edges_by_target.get(bs.node_id, []) if e.type in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS)]
            if inbound:
                continue
            zero_caller_pubs.append(
                {
                    "symbol_id": bs.node_id,
                    "qualified_name": bs.extracted.qualified_name,
                    "signature": bs.extracted.signature,
                    "file_path": bs.rel_path,
                }
            )
        new_edges = _enrich.enrich_zero_caller_public_symbols(
            enrichment_input=_enrich.EnrichmentInput(repo=pr_meta.repo),
            public_symbols_with_no_callers=zero_caller_pubs,
            diagnostics=diagnostics,
        )
        edges.extend(new_edges)
        llm_used = any(e.confidence == Confidence.LLM_INFERRED for e in edges)

    # 8. Build Graph + invariant validation ---------------------------------
    graph = Graph(
        generated_at=datetime.now(timezone.utc),
        generator="prex 0.1.0",
        pr=pr_meta,
        nodes=nodes,
        edges=edges,
        diagnostics=diagnostics,
        llm_enrichment_used=llm_used,
    )

    # Re-validate after Graph construction (Pydantic validates field types; we add semantic invariants)
    from prex.parser._emit import validate_invariants

    graph.diagnostics.extend(validate_invariants(graph))
    return graph
