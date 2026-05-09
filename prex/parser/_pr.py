"""PR resolution: fetch metadata + diff via `gh`, manage local clones.

We rely on `gh` rather than the GitHub REST API directly so private repos work
out-of-the-box if the user is already authenticated.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from prex.schemas.graph import PRMetadata


_PR_URL_RE = re.compile(r"^https?://github\.com/([^/]+/[^/]+)/pull/(\d+)/?")


@dataclass
class ResolvedPR:
    metadata: PRMetadata
    repo_path: Path  # local clone with base + head fetched
    raw_diff: str  # unified diff for entire PR (all files)


def _run(cmd: list[str], cwd: Optional[Path] = None) -> str:
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return out.stdout


def parse_pr_url(url: str) -> tuple[str, int]:
    """Extract (repo, pr_number) from a GitHub PR URL."""
    m = _PR_URL_RE.match(url.rstrip("/").replace("/files", "").replace("/changes", ""))
    if not m:
        raise ValueError(f"not a GitHub PR URL: {url!r}")
    return m.group(1), int(m.group(2))


def _gh_pr_view(repo: str, number: int) -> dict:
    out = _run(
        [
            "gh", "pr", "view", str(number),
            "--repo", repo,
            "--json",
            "title,body,author,baseRefName,headRefName,baseRefOid,headRefOid,additions,deletions,changedFiles,url",
        ]
    )
    return json.loads(out)


def _gh_pr_diff(repo: str, number: int) -> str:
    return _run(["gh", "pr", "diff", str(number), "--repo", repo])


def _ensure_clone(repo: str, base_sha: str, head_sha: str, work_dir: Path) -> Path:
    """Ensure a local clone exists with both base + head SHAs fetched."""
    work_dir.mkdir(parents=True, exist_ok=True)
    repo_path = work_dir / repo.replace("/", "__")
    if not (repo_path / ".git").exists():
        _run(["gh", "repo", "clone", repo, str(repo_path), "--", "--no-checkout", "--filter=blob:none"])
    # Fetch the two SHAs we need
    for sha in {base_sha, head_sha}:
        try:
            _run(["git", "cat-file", "-e", sha], cwd=repo_path)
        except subprocess.CalledProcessError:
            _run(["git", "fetch", "origin", sha], cwd=repo_path)
    # Checkout head
    _run(["git", "checkout", "--force", head_sha], cwd=repo_path)
    return repo_path


def resolve(url: str, work_dir: Optional[Path] = None) -> ResolvedPR:
    """Resolve a PR URL into metadata + cloned repo + raw diff."""
    repo, number = parse_pr_url(url)
    view = _gh_pr_view(repo, number)
    diff = _gh_pr_diff(repo, number)
    base_sha = view["baseRefOid"]
    head_sha = view["headRefOid"]

    work_dir = work_dir or (Path.home() / ".cache" / "prex" / "repos")
    repo_path = _ensure_clone(repo, base_sha, head_sha, work_dir)

    metadata = PRMetadata(
        url=view["url"],
        repo=repo,
        number=number,
        title=view["title"],
        author=(view["author"] or {}).get("login", "") or "unknown",
        base_ref=view["baseRefName"],
        head_ref=view["headRefName"],
        base_sha=base_sha,
        head_sha=head_sha,
        additions=view["additions"],
        deletions=view["deletions"],
        changed_files=view["changedFiles"],
    )
    return ResolvedPR(metadata=metadata, repo_path=repo_path, raw_diff=diff)
