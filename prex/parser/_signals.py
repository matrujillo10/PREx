"""AST-derived risk signals per hunk.

Each function inspects a HunkNode's patch text + the enclosing Symbol's
context and decides whether a signal applies. Signals are deterministic
(no LLM); v1 covers the catalog of `RiskSignal` literals in `schemas.brief`.

Cheap heuristics where they suffice; tree-sitter where structure matters.
All signal detectors return `(triggered: bool, evidence_excerpt: str | None)`.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from prex.schemas.brief import RiskSignal


# A "+ line" or "- line" excluding the +++/--- diff header lines.
def _added_lines(patch: str) -> List[str]:
    return [
        ln[1:].rstrip()
        for ln in patch.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    ]


def _removed_lines(patch: str) -> List[str]:
    return [
        ln[1:].rstrip()
        for ln in patch.splitlines()
        if ln.startswith("-") and not ln.startswith("---")
    ]


# ---------- individual detectors ----------


_AUTH_RE = re.compile(
    r"\b(authoriz|authentic|permission|jwt|oauth|saml|session_cookie|csrf|api_key|access_token|secret_key)\b",
    re.IGNORECASE,
)
def _auth_or_authz_touched(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch) + _removed_lines(patch):
        if _AUTH_RE.search(ln):
            return True, ln.strip()[:120]
    return False, ""


_SQL_RE = re.compile(
    r"\b(SELECT\b|INSERT\s+INTO\b|UPDATE\s+\w+\s+SET\b|DELETE\s+FROM\b|JOIN\s+\w+|FROM\s+\w+)",
    re.IGNORECASE,
)


def _sql_in_changed_lines(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch):
        stripped = ln.strip()
        # Skip Python imports — `from X import Y` would otherwise match `FROM\s+\w+`.
        if stripped.startswith(("from ", "import ")) and " import " in (stripped + " import "):
            continue
        if _SQL_RE.search(ln):
            return True, stripped[:120]
    return False, ""


_IO_RE = re.compile(
    r"\b(requests\.|httpx\.|urlopen|boto3|botocore|s3_client|pubsub|kafka|kinesis|smtp|email\.send|psycopg|sqlalchemy|asyncpg|redis|mongo)\b",
    re.IGNORECASE,
)
def _external_io(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch):
        if _IO_RE.search(ln):
            return True, ln.strip()[:120]
    return False, ""


def _removes_assertion(patch: str, *, in_test_file: bool) -> Tuple[bool, str]:
    if not in_test_file:
        return False, ""
    for ln in _removed_lines(patch):
        s = ln.lstrip()
        if s.startswith("assert ") or s.startswith("self.assert"):
            return True, ln.strip()[:120]
    return False, ""


_VALIDATION_RE = re.compile(
    r"\b(Field\s*\(.*?(min_length|max_length|gt|ge|lt|le|regex|pattern)|"
    r"@validator|@field_validator|raise\s+(ValueError|TypeError|AssertionError))",
    re.IGNORECASE,
)
def _weakens_validation(patch: str) -> Tuple[bool, str]:
    """Heuristic: removed validation rule that wasn't replaced on a `+` line nearby."""
    removed_validations = [ln for ln in _removed_lines(patch) if _VALIDATION_RE.search(ln)]
    added = "\n".join(_added_lines(patch))
    for r in removed_validations:
        # If the same field's validation isn't restored on the added side, count it as weakening.
        token = r.strip()[:30]
        if token and token not in added:
            return True, r.strip()[:120]
    return False, ""


_RAISES_SWALLOWED_RE = re.compile(r"^\s*(except\b.*:\s*)$|^\s*pass\s*$")
def _raises_swallowed(patch: str) -> Tuple[bool, str]:
    """Crude detector for `except X: pass` patterns introduced in this hunk."""
    added = _added_lines(patch)
    for i, ln in enumerate(added):
        if re.match(r"\s*except\b.*:\s*$", ln):
            tail = added[i + 1] if i + 1 < len(added) else ""
            if tail.strip() == "pass":
                return True, ln.strip()[:120]
    return False, ""


def _broad_except(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch):
        s = ln.strip()
        if s.startswith("except:") or s.startswith("except Exception"):
            return True, s[:120]
    return False, ""


_FLAG_ADDED_RE = re.compile(
    r"\b(launchdarkly|growthbook|featureflag|FeatureFlag|launch_darkly|gb_client|flags?\.is_(enabled|on))\b",
    re.IGNORECASE,
)
def _feature_flag_added(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch):
        if _FLAG_ADDED_RE.search(ln):
            return True, ln.strip()[:120]
    return False, ""


def _feature_flag_removed(patch: str) -> Tuple[bool, str]:
    for ln in _removed_lines(patch):
        if _FLAG_ADDED_RE.search(ln):
            return True, ln.strip()[:120]
    return False, ""


_SECRET_RE = re.compile(
    r"""(['"])(?:[A-Za-z0-9_\-+/=]{32,})\1|"""           # generic long opaque tokens
    r"""\bAKIA[0-9A-Z]{16}\b|"""                          # AWS access key id
    r"""\bAIza[0-9A-Za-z_\-]{35}\b|"""                    # Google API key
    r"""\bsk-[A-Za-z0-9]{20,}\b|"""                       # OpenAI / Anthropic-style
    r"""xox[baprs]-[A-Za-z0-9-]{10,}\b"""                 # Slack token
)
def _secret_like_string(patch: str) -> Tuple[bool, str]:
    for ln in _added_lines(patch):
        if _SECRET_RE.search(ln):
            return True, "(secret-shaped string redacted)"
    return False, ""


_NUMERIC_CONST_RE = re.compile(r"=\s*\d+(\.\d+)?")
def _numeric_constant_changed_in_hot_loop(patch: str) -> Tuple[bool, str]:
    """Heuristic: numeric assignment changed inside a function body. We don't
    know which loops are 'hot' — flag conservatively when both `+` and `-`
    lines contain a numeric assignment to the same identifier."""
    added = _added_lines(patch)
    removed = _removed_lines(patch)
    added_targets = {re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln) for ln in added}
    removed_targets = {re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln) for ln in removed}
    common = {m.group(1) for m in added_targets if m} & {m.group(1) for m in removed_targets if m}
    if not common:
        return False, ""
    # Confirm at least one side has a numeric literal.
    for ln in added + removed:
        if _NUMERIC_CONST_RE.search(ln):
            return True, ln.strip()[:120]
    return False, ""


# ---------- aggregator ----------


def signals_for_hunk(patch: str, *, in_test_file: bool) -> List[Tuple[RiskSignal, str]]:
    """Return list of (signal, evidence_excerpt) for everything that fires."""
    out: List[Tuple[RiskSignal, str]] = []
    detectors = [
        ("auth_or_authz_touched", lambda: _auth_or_authz_touched(patch)),
        ("sql_in_changed_lines", lambda: _sql_in_changed_lines(patch)),
        ("external_io", lambda: _external_io(patch)),
        ("removes_assertion", lambda: _removes_assertion(patch, in_test_file=in_test_file)),
        ("weakens_validation", lambda: _weakens_validation(patch)),
        ("raises_swallowed", lambda: _raises_swallowed(patch)),
        ("broad_except", lambda: _broad_except(patch)),
        ("feature_flag_added", lambda: _feature_flag_added(patch)),
        ("feature_flag_removed", lambda: _feature_flag_removed(patch)),
        ("secret_like_string", lambda: _secret_like_string(patch)),
        ("numeric_constant_changed_in_hot_loop", lambda: _numeric_constant_changed_in_hot_loop(patch)),
    ]
    for name, fn in detectors:
        triggered, excerpt = fn()
        if triggered:
            out.append((name, excerpt))  # type: ignore[arg-type]
    return out
