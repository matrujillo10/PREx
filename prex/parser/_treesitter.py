"""tree-sitter symbol extraction for Python.

Extracts top-level functions, classes, methods, and tests from a Python source
file. Returns lightweight `ExtractedSymbol` records keyed by qualified name.

We deliberately stay shallow: no nested-function symbols, no closures, no
constants for v0. Reviewer relevance is at function/class/method granularity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, Optional

import tree_sitter_python as tsp
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tsp.language())
_PARSER = Parser(PY_LANGUAGE)


@dataclass
class ExtractedSymbol:
    """One extractable Python symbol."""

    qualified_name: str  # 'module.path.ClassName.method_name' (module rooted at file)
    name: str
    kind: str  # 'function' | 'method' | 'class' | 'test'
    start_line: int  # 1-indexed
    end_line: int  # 1-indexed inclusive
    signature: Optional[str]
    public: bool


def _module_qualname_for_path(repo_relative_path: str) -> str:
    """Convert 'python/agent_evaluation/agent_evaluation/controller/controller.py'
    to a dotted module path 'python.agent_evaluation.agent_evaluation.controller.controller'.
    """
    p = PurePosixPath(repo_relative_path)
    parts = list(p.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts.pop()
    return ".".join(parts)


def _is_test_name(name: str) -> bool:
    return name.startswith("test_") or name == "test"


def _signature(source: bytes, node) -> str:
    """First line of `def foo(...):` / `class Foo(...):`, trimmed."""
    text = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    head, _, _ = text.partition("\n")
    return head.strip()


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def extract_symbols(source: bytes, repo_relative_path: str) -> List[ExtractedSymbol]:
    """Extract function/method/class/test symbols from a Python source buffer."""
    tree = _PARSER.parse(source)
    root = tree.root_node
    module_qn = _module_qualname_for_path(repo_relative_path)
    is_test_file = (
        "/tests/" in f"/{repo_relative_path}/" or
        PurePosixPath(repo_relative_path).name.startswith("test_") or
        PurePosixPath(repo_relative_path).name.endswith("_test.py")
    )

    out: List[ExtractedSymbol] = []

    def add_symbol(node, kind: str, name: str, parent_qn: str) -> None:
        qn = f"{parent_qn}.{name}" if parent_qn else name
        out.append(
            ExtractedSymbol(
                qualified_name=qn,
                name=name,
                kind=kind,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                signature=_signature(source, node),
                public=_is_public(name),
            )
        )

    def child_named_name(node) -> Optional[str]:
        # function_definition / class_definition both have a child of type 'identifier' named 'name'
        n = node.child_by_field_name("name")
        if n is None:
            return None
        return source[n.start_byte:n.end_byte].decode("utf-8", errors="replace")

    # Walk top-level
    for child in root.named_children:
        if child.type == "function_definition":
            name = child_named_name(child) or "<anon>"
            kind = "test" if (is_test_file and _is_test_name(name)) else "function"
            add_symbol(child, kind, name, module_qn)
        elif child.type == "class_definition":
            cname = child_named_name(child) or "<anon>"
            add_symbol(child, "class", cname, module_qn)
            class_qn = f"{module_qn}.{cname}" if module_qn else cname
            _walk_class_body(source, child, class_qn, is_test_file, out)
        elif child.type == "decorated_definition":
            # `@deco\ndef foo():` — the inner def carries the name; line range starts at the decorator.
            inner = child.child_by_field_name("definition")
            if inner is None:
                continue
            iname = child_named_name(inner) or "<anon>"
            if inner.type == "function_definition":
                kind = "test" if (is_test_file and _is_test_name(iname)) else "function"
                # use the decorated_definition's line range so decorators count as part of the symbol
                ext = ExtractedSymbol(
                    qualified_name=f"{module_qn}.{iname}" if module_qn else iname,
                    name=iname,
                    kind=kind,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    signature=_signature(source, inner),
                    public=_is_public(iname),
                )
                out.append(ext)
            elif inner.type == "class_definition":
                add_symbol(child, "class", iname, module_qn)
                class_qn = f"{module_qn}.{iname}" if module_qn else iname
                _walk_class_body(source, inner, class_qn, is_test_file, out)

    return out


def _walk_class_body(source: bytes, class_node, class_qn: str, is_test_file: bool, out: List[ExtractedSymbol]) -> None:
    """Extract methods (including decorated) from inside a class body."""
    body = class_node.child_by_field_name("body")
    if body is None:
        return
    for member in body.named_children:
        if member.type == "function_definition":
            mn = member.child_by_field_name("name")
            mname = source[mn.start_byte:mn.end_byte].decode("utf-8", errors="replace") if mn else "<anon>"
            mkind = "test" if (is_test_file and _is_test_name(mname)) else "method"
            out.append(
                ExtractedSymbol(
                    qualified_name=f"{class_qn}.{mname}",
                    name=mname,
                    kind=mkind,
                    start_line=member.start_point[0] + 1,
                    end_line=member.end_point[0] + 1,
                    signature=_signature(source, member),
                    public=_is_public(mname),
                )
            )
        elif member.type == "decorated_definition":
            inner = member.child_by_field_name("definition")
            if inner is None or inner.type != "function_definition":
                continue
            mn = inner.child_by_field_name("name")
            mname = source[mn.start_byte:mn.end_byte].decode("utf-8", errors="replace") if mn else "<anon>"
            mkind = "test" if (is_test_file and _is_test_name(mname)) else "method"
            out.append(
                ExtractedSymbol(
                    qualified_name=f"{class_qn}.{mname}",
                    name=mname,
                    kind=mkind,
                    start_line=member.start_point[0] + 1,
                    end_line=member.end_point[0] + 1,
                    signature=_signature(source, inner),
                    public=_is_public(mname),
                )
            )


def parse_file(path) -> List[ExtractedSymbol]:
    """Convenience: parse a path on disk and extract symbols (path is repo-relative).

    `path` may be a Path object or string. The repo-relative path used for module
    qualification must be passed as `path.as_posix()` — caller is responsible for
    ensuring the path is repo-relative when stored on disk.
    """
    raise NotImplementedError("Use extract_symbols(source_bytes, repo_relative_path) directly.")
