"""prex CLI entry point.

Default invocation:
    prex review <PR-URL>

Parses the PR, writes artifacts under output/pr-<number>/, then starts a local
HTTP server and opens the browser to the rendered review experience.

Artifacts written:
    graph.json              — full impact graph (deep store for citations)
    brief.json              — briefing for the host LLM (the primary input)
    manifest.snapshot.yaml  — copy of the .review/types.yaml used
    CONTRACT.md             — auto-generated description of the artifacts

Examples:
    prex review https://github.com/connectlyai/connectly-backend/pull/19858
    prex review <url> --llm-enrich              # disambiguate ambiguous cross-refs
    prex review <url> --llm-summarise           # fill prose fields
    prex review <url> --no-open                 # don't auto-open the browser
    prex review <url> --port 5173               # pin the server port
    prex review <url> --debug-mermaid           # also write output/graph.mmd
"""
from __future__ import annotations

import shutil
import webbrowser
from pathlib import Path
from typing import Optional

import click

from prex.manifest import find_manifest
from prex.manifest.contract_renderer import write_contract
from prex.parser import parse_pr
from prex.parser._brief import build_brief
from prex.parser._brief_llm import enrich_brief_with_llm
from prex.parser._emit import to_json, to_mermaid
from prex.parser._pr import parse_pr_url
from prex.server import serve


@click.group()
def main() -> None:
    """PREx — diff impact graph + briefing for generative-UI hosts."""


@main.command()
@click.argument("pr_url")
@click.option(
    "--out-dir",
    "out_dir",
    default=None,
    type=click.Path(),
    help="Directory for output artifacts. Defaults to output/pr-<number>/.",
)
@click.option("--llm-enrich/--no-llm-enrich", default=False, help="LLM disambiguation of ambiguous cross-ref edges.")
@click.option("--llm-summarise/--no-llm-summarise", default=False, help="LLM-fill prose fields.")
@click.option("--include-tests/--no-include-tests", default=False, help="Include test-file callers as graph nodes.")
@click.option("--debug-mermaid/--no-debug-mermaid", default=False, help="Also write graph.mmd for debugging.")
@click.option("--manifest", "manifest_path", default=None, type=click.Path(), help="Path to .review/types.yaml.")
@click.option("--work-dir", default=None, type=click.Path(), help="Local clone cache root.")
@click.option("--serve/--no-serve", "serve_ui", default=True, help="Start the local UI server after writing artifacts (default on).")
@click.option("--open/--no-open", "open_browser", default=True, help="Open the browser when the UI server starts.")
@click.option("--port", "port", default=0, type=int, help="UI server port. 0 = OS-pick a free port.")
def review(
    pr_url: str,
    out_dir: Optional[str],
    llm_enrich: bool,
    llm_summarise: bool,
    include_tests: bool,
    debug_mermaid: bool,
    manifest_path: Optional[str],
    work_dir: Optional[str],
    serve_ui: bool,
    open_browser: bool,
    port: int,
) -> None:
    """Build the impact graph + briefing for a PR, then open the UI."""
    # Resolve output dir before parsing so we know where artifacts will land.
    if out_dir is None:
        try:
            _, pr_number = parse_pr_url(pr_url)
            out = Path("output") / f"pr-{pr_number}"
        except ValueError:
            out = Path("output")
    else:
        out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    work = Path(work_dir).expanduser() if work_dir else None
    graph = parse_pr(pr_url, llm_enrich=llm_enrich, work_dir=work, include_tests=include_tests)

    graph_path = out / "graph.json"
    graph_path.write_text(to_json(graph) + "\n")

    manifest_p = Path(manifest_path).expanduser() if manifest_path else None
    brief = build_brief(graph, graph_ref="graph.json", manifest_path=manifest_p)

    if llm_summarise:
        brief = enrich_brief_with_llm(graph, brief, diagnostics=brief.diagnostics)
    brief_path = out / "brief.json"
    brief_path.write_text(brief.model_dump_json(indent=2) + "\n")

    manifest_resolved = find_manifest(repo_path=Path("."), override=manifest_p)
    if manifest_resolved is not None:
        shutil.copyfile(manifest_resolved, out / "manifest.snapshot.yaml")

    write_contract(out / "CONTRACT.md", graph.pr)

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

    if not serve_ui:
        return

    try:
        httpd, bound_port = serve(out, port=port)
    except FileNotFoundError as e:
        click.echo(f"⚠ {e}", err=True)
        return

    url = f"http://127.0.0.1:{bound_port}/"
    click.echo("")
    click.echo(f"  ↗ open {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        click.echo("")
        click.echo("  shutting down server …")
        httpd.shutdown()


if __name__ == "__main__":
    main()
