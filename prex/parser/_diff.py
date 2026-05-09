"""Unified diff parser.

Splits a unified-diff string into per-file lists of FileDiff/Hunk records.
v0 only needs line-range information; we keep the patch text per hunk for
later attachment to HunkNode.patch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


@dataclass
class Hunk:
    """One @@ section in a file diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    text: str  # the @@ header + body of the hunk

    @property
    def head_line_range(self) -> tuple[int, int]:
        """Line range in the head (post-change) version. (start, end_inclusive)"""
        if self.new_count == 0:
            # pure deletion — anchor at new_start (which points to the line BEFORE the deletion in head)
            return self.new_start or 1, self.new_start or 1
        return self.new_start, self.new_start + self.new_count - 1

    @property
    def base_line_range(self) -> tuple[int, int]:
        if self.old_count == 0:
            return self.old_start or 1, self.old_start or 1
        return self.old_start, self.old_start + self.old_count - 1

    @property
    def change_type(self) -> str:
        """'added' / 'removed' / 'modified'."""
        body = self.text.split("\n", 1)[1] if "\n" in self.text else ""
        has_add = any(l.startswith("+") and not l.startswith("+++") for l in body.splitlines())
        has_del = any(l.startswith("-") and not l.startswith("---") for l in body.splitlines())
        if has_add and not has_del:
            return "added"
        if has_del and not has_add:
            return "removed"
        return "modified"

    def head_changed_lines(self) -> set[int]:
        """Return the set of head-side 1-indexed lines that are actually '+' lines.

        Context lines (' ') and removed lines ('-') are excluded. This is what
        we should overlap against to decide whether a symbol is touched —
        the diff hunk header reports a wider range that includes context.
        """
        out: set[int] = set()
        body_lines = self.text.split("\n", 1)[1].splitlines() if "\n" in self.text else []
        cur = self.new_start
        for raw in body_lines:
            if not raw:
                cur += 1
                continue
            tag = raw[0]
            if tag == "+":
                out.add(cur)
                cur += 1
            elif tag == "-":
                # removed line — does not advance head pointer
                continue
            else:
                # context line (' ' or '\\') advances head pointer
                cur += 1
        return out


@dataclass
class FileDiff:
    old_path: Optional[str]
    new_path: Optional[str]
    hunks: List[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or ""


_FILE_HEADER_RE = re.compile(r"^diff --git a/(?P<a>.+?) b/(?P<b>.+?)$")
_OLD_RE = re.compile(r"^--- (?:a/(?P<p>.+)|/dev/null)")
_NEW_RE = re.compile(r"^\+\+\+ (?:b/(?P<p>.+)|/dev/null)")
_HUNK_RE = re.compile(
    r"^@@ -(?P<os>\d+)(?:,(?P<oc>\d+))? \+(?P<ns>\d+)(?:,(?P<nc>\d+))? @@"
)


def parse(diff: str) -> List[FileDiff]:
    """Parse a unified-diff string into FileDiff records."""
    files: List[FileDiff] = []
    cur: Optional[FileDiff] = None
    cur_hunk_lines: List[str] = []
    cur_hunk_meta: Optional[tuple[int, int, int, int]] = None

    def flush_hunk() -> None:
        nonlocal cur_hunk_lines, cur_hunk_meta
        if cur is not None and cur_hunk_meta is not None:
            os_, oc, ns, nc = cur_hunk_meta
            cur.hunks.append(
                Hunk(
                    old_start=os_,
                    old_count=oc,
                    new_start=ns,
                    new_count=nc,
                    text="\n".join(cur_hunk_lines),
                )
            )
        cur_hunk_lines = []
        cur_hunk_meta = None

    for line in diff.splitlines():
        if line.startswith("diff --git"):
            flush_hunk()
            if cur is not None:
                files.append(cur)
            m = _FILE_HEADER_RE.match(line)
            if m:
                cur = FileDiff(old_path=m.group("a"), new_path=m.group("b"))
            else:
                cur = FileDiff(old_path=None, new_path=None)
            continue
        if cur is None:
            continue
        if line.startswith("new file mode"):
            cur.is_new = True
            continue
        if line.startswith("deleted file mode"):
            cur.is_deleted = True
            continue
        if line.startswith("--- "):
            m = _OLD_RE.match(line)
            if m and m.group("p"):
                cur.old_path = m.group("p")
            elif "/dev/null" in line:
                cur.old_path = None
                cur.is_new = True
            continue
        if line.startswith("+++ "):
            m = _NEW_RE.match(line)
            if m and m.group("p"):
                cur.new_path = m.group("p")
            elif "/dev/null" in line:
                cur.new_path = None
                cur.is_deleted = True
            continue
        m = _HUNK_RE.match(line)
        if m:
            flush_hunk()
            os_ = int(m.group("os"))
            oc = int(m.group("oc") or 1)
            ns = int(m.group("ns"))
            nc = int(m.group("nc") or 1)
            cur_hunk_meta = (os_, oc, ns, nc)
            cur_hunk_lines = [line]
            continue
        if cur_hunk_meta is not None:
            cur_hunk_lines.append(line)

    flush_hunk()
    if cur is not None:
        files.append(cur)
    return files


def overlaps(symbol_range: tuple[int, int], hunk_range: tuple[int, int]) -> bool:
    """Inclusive line-range overlap test."""
    a_start, a_end = symbol_range
    b_start, b_end = hunk_range
    return a_start <= b_end and b_start <= a_end
