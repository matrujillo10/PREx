"""prex CLI entry point.

Examples:
    prex review https://github.com/connectlyai/connectly-backend/pull/19858
    prex review <url> --out graph.json --mermaid graph.mmd
    prex review <url> --llm-enrich
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click

from prex.parser import parse_pr
from prex.parser._emit import to_json, to_mermaid


@click.group()
def main() -> None:
    """PREx — diff impact graph generator."""


@main.command()
@click.argument("pr_url")
@click.option("--out", "out_path", default="output/graph.json", show_default=True, help="Path to write graph JSON.")
@click.option("--mermaid", "mermaid_path", default="output/graph.mmd", show_default=True, help="Path to write Mermaid view.")
@click.option("--llm-enrich/--no-llm-enrich", default=False, help="Enable LLM enrichment for ambiguous edges + zero-caller public symbols. Requires ANTHROPIC_API_KEY.")
@click.option("--work-dir", default=None, type=click.Path(), help="Local clone cache root. Defaults to ~/.cache/prex/repos.")
def review(pr_url: str, out_path: str, mermaid_path: str, llm_enrich: bool, work_dir: Optional[str]) -> None:
    """Build the impact graph for a PR."""
    work = Path(work_dir).expanduser() if work_dir else None
    graph = parse_pr(pr_url, llm_enrich=llm_enrich, work_dir=work)

    out = Path(out_path)
    mer = Path(mermaid_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mer.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_json(graph) + "\n")
    mer.write_text(to_mermaid(graph) + "\n")

    n_changed_syms = sum(1 for n in graph.nodes if getattr(n, "kind", None) == "symbol" and n.change_state != "unchanged")
    n_callers = sum(1 for e in graph.edges if e.type.value in ("calls", "references", "imports"))
    n_externals = sum(1 for n in graph.nodes if getattr(n, "kind", None) == "external_ref")
    n_diag = len(graph.diagnostics)

    click.echo(f"PR: {graph.pr.repo}#{graph.pr.number} — {graph.pr.title}")
    click.echo(f"Wrote {out_path} and {mermaid_path}")
    click.echo(
        f"  changed symbols: {n_changed_syms}  "
        f"caller edges: {n_callers}  "
        f"external refs: {n_externals}  "
        f"diagnostics: {n_diag}"
    )


if __name__ == "__main__":
    main()
