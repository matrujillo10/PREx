"""prex CLI entry point.

Default invocation produces four artifacts under output/:
    graph.json              — full impact graph (deep store for citations)
    brief.json              — briefing for the host LLM (the primary input)
    manifest.snapshot.yaml  — copy of the .review/types.yaml used (Build 2)
    CONTRACT.md             — auto-generated description of the artifacts

Examples:
    prex review https://github.com/connectlyai/connectly-backend/pull/19858
    prex review <url> --llm-enrich              # disambiguate ambiguous cross-refs
    prex review <url> --llm-summarise           # fill prose fields (one_liner / headline / What/Why/Impact)
    prex review <url> --debug-mermaid           # also write output/graph.mmd
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from prex.parser import parse_pr
from prex.parser._brief import build_brief
from prex.parser._emit import to_json, to_mermaid


@click.group()
def main() -> None:
    """PREx — diff impact graph + briefing for generative-UI hosts."""


@main.command()
@click.argument("pr_url")
@click.option("--out-dir", "out_dir", default="output", show_default=True, type=click.Path(), help="Directory for all output artifacts.")
@click.option("--llm-enrich/--no-llm-enrich", default=False, help="LLM disambiguation of ambiguous cross-ref edges. Requires GCP ADC + Vertex AI.")
@click.option("--llm-summarise/--no-llm-summarise", default=False, help="LLM-fill prose fields (one_liner, headline, What/Why/Impact).")
@click.option("--include-tests/--no-include-tests", default=False, help="Include test-file callers as graph nodes. Default off.")
@click.option("--debug-mermaid/--no-debug-mermaid", default=False, help="Also write output/graph.mmd for debugging.")
@click.option("--manifest", "manifest_path", default=None, type=click.Path(), help="Path to .review/types.yaml. Defaults to repo's own / bundled fallback.")
@click.option("--work-dir", default=None, type=click.Path(), help="Local clone cache root. Defaults to ~/.cache/prex/repos.")
def review(
    pr_url: str,
    out_dir: str,
    llm_enrich: bool,
    llm_summarise: bool,
    include_tests: bool,
    debug_mermaid: bool,
    manifest_path: Optional[str],
    work_dir: Optional[str],
) -> None:
    """Build the impact graph + briefing for a PR."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    work = Path(work_dir).expanduser() if work_dir else None
    graph = parse_pr(pr_url, llm_enrich=llm_enrich, work_dir=work, include_tests=include_tests)

    graph_path = out / "graph.json"
    graph_path.write_text(to_json(graph) + "\n")

    brief = build_brief(graph, graph_ref="graph.json")
    brief_path = out / "brief.json"
    brief_path.write_text(brief.model_dump_json(indent=2) + "\n")

    if debug_mermaid:
        (out / "graph.mmd").write_text(to_mermaid(graph) + "\n")

    n_changed_syms = sum(
        1 for n in graph.nodes
        if getattr(n, "kind", None) == "symbol" and getattr(n, "change_state", None) and n.change_state.value != "unchanged"
    )
    n_callers = sum(1 for e in graph.edges if e.type.value in ("calls", "references", "imports"))
    n_externals = sum(1 for n in graph.nodes if getattr(n, "kind", None) == "external_ref")
    n_signals = sum(len(h.risk_signals) for h in brief.hunks)
    n_steps = len(brief.plan.steps)

    click.echo(f"PR: {graph.pr.repo}#{graph.pr.number} — {graph.pr.title}")
    click.echo(f"Wrote {graph_path} and {brief_path}")
    click.echo(
        f"  changed symbols: {n_changed_syms}  "
        f"caller edges: {n_callers}  "
        f"external refs: {n_externals}  "
        f"risk signals: {n_signals}  "
        f"plan steps: {n_steps}"
    )
    click.echo(
        f"  pr_type: {brief.review.pr_type}  "
        f"risk_tier: {brief.review.risk_tier}  "
        f"risk_score: {brief.review.risk_score:.2f}  "
        f"advisory_flags: {brief.review.advisory_flags}"
    )


if __name__ == "__main__":
    main()
