"""LLM prose layer for the Brief.

Three call sites, in order:
    A. per-hunk insights (one_liner + intent), batched 8-at-a-time
    B. PR-level headline + pr_type evidence summary
    C. ReviewPlan What/Why/Impact prose for ranked steps

All output anchored to Citations from Build 1; validation rejects unsourced prose.
Off unless the orchestrator passes `enabled=True` (driven by --llm-summarise).

Backend: Anthropic Messages API directly (same key as the chat agent at
prex/agent.py). litellm path removed — needed two adapters for the same
provider, and litellm wrapped JSON in fences on Anthropic which made the
extractor work harder. Override the model via PREX_LLM_MODEL.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import anthropic

from prex.schemas._shared import Citation, Derivation, Diagnostic
from prex.schemas.brief import (
    Brief,
    HunkInsight,
    HunkIntent,
    ReviewBrief,
    ReviewPlan,
    ReviewStep,
)
from prex.schemas.graph import (
    EdgeType,
    FileNode,
    Graph,
    HunkNode,
    SymbolNode,
)


_LOG = logging.getLogger("prex.brief_llm")

# Anthropic model id. Strip the "anthropic/" prefix if present so users can
# share PREX_LLM_MODEL with litellm-style ids.
DEFAULT_MODEL = os.environ.get("PREX_LLM_MODEL", "claude-sonnet-4-5-20250929")
if DEFAULT_MODEL.startswith("anthropic/"):
    DEFAULT_MODEL = DEFAULT_MODEL[len("anthropic/") :]

# Kept for backwards-compat with callers that still pass these kwargs; not used.
DEFAULT_PROJECT = os.environ.get("VERTEXAI_PROJECT", "prex-hackathon")
DEFAULT_LOCATION = os.environ.get("VERTEXAI_LOCATION", "us-central1")

HUNKS_PER_BATCH = 8
MAX_HUNKS_PER_PR = 30


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


_CLIENT_CACHE: Optional[anthropic.Anthropic] = None


def _client() -> Optional[anthropic.Anthropic]:
    global _CLIENT_CACHE
    if _CLIENT_CACHE is not None:
        return _CLIENT_CACHE
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    _CLIENT_CACHE = anthropic.Anthropic(api_key=api_key)
    return _CLIENT_CACHE


def _call_llm(prompt: str, *, model: str, project: str, location: str) -> Optional[str]:
    """Anthropic Messages API call returning the assistant text."""
    client = _client()
    if client is None:
        _LOG.warning("ANTHROPIC_API_KEY not set; skipping LLM call.")
        return None
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        # Concatenate any text blocks; ignore tool_use here (this path is
        # plain prose, no tools registered).
        out_parts: List[str] = []
        for block in resp.content:
            if getattr(block, "type", "") == "text":
                out_parts.append(getattr(block, "text", "") or "")
        return "".join(out_parts) or None
    except Exception as e:
        _LOG.warning("Anthropic call failed: %s", e)
        return None


def _extract_json(content: str) -> Optional[dict]:
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        cleaned = re.sub(r",\s*([\}\]])", r"\1", m.group(0))
        try:
            return json.loads(cleaned)
        except Exception:
            return None


# ---------- Call A: per-hunk insights ----------


def _select_hunks_for_summary(graph: Graph, brief: Brief) -> List[Tuple[HunkInsight, HunkNode, str]]:
    """Pick up to MAX_HUNKS_PER_PR hunks worth summarising. Skip generated files."""
    nodes_by_id = {n.id: n for n in graph.nodes}
    out: List[Tuple[HunkInsight, HunkNode, str]] = []
    for hi in brief.hunks:
        hn = nodes_by_id.get(hi.hunk_id)
        if not isinstance(hn, HunkNode):
            continue
        file_node = nodes_by_id.get(hn.file_id)
        if not isinstance(file_node, FileNode):
            continue
        if getattr(file_node, "generated", False):
            continue
        out.append((hi, hn, file_node.path))
        if len(out) >= MAX_HUNKS_PER_PR:
            break
    return out


_INTENT_VALUES = {
    "adds_capability", "fixes_bug", "renames", "extracts", "inlines",
    "reorders", "tightens_types", "weakens_test", "adds_test",
    "removes_dead", "comments_only", "style_only", "unknown",
}


def _build_hunk_batch_prompt(batch: List[Tuple[HunkInsight, HunkNode, str]]) -> str:
    parts = [
        "You are summarising hunks from a pull request.",
        "For each hunk, return a one-liner (≤80 chars) and an intent label.",
        "",
        f'Allowed `intent` values: {", ".join(sorted(_INTENT_VALUES))}.',
        "",
        "Be factual and specific. Do not editorialise. Avoid adverbs.",
        "",
    ]
    for i, (hi, hn, path) in enumerate(batch, start=1):
        parts.append(f"[{i}] hunk_id: {hi.hunk_id}")
        parts.append(f"    file: {path}")
        parts.append(f"    risk_signals: {list(hi.risk_signals)}")
        parts.append("    patch:")
        parts.append("```")
        parts.append(hn.patch[:1500])
        parts.append("```")
        parts.append("")
    parts.append('Respond with: {"hunks": [{"i": 1, "one_liner": "...", "intent": "..."}, ...]}.')
    parts.append("No prose outside JSON.")
    return "\n".join(parts)


def fill_hunk_insights(
    graph: Graph,
    brief: Brief,
    *,
    diagnostics: List[Diagnostic],
    model: str = DEFAULT_MODEL,
    project: str = DEFAULT_PROJECT,
    location: str = DEFAULT_LOCATION,
) -> int:
    """Populate `one_liner` + `intent` on hunk insights via LLM. Returns # filled."""
    selection = _select_hunks_for_summary(graph, brief)
    if not selection:
        return 0
    hunks_by_idx = {h.hunk_id: h for h in brief.hunks}
    filled = 0
    for batch_start in range(0, len(selection), HUNKS_PER_BATCH):
        batch = selection[batch_start: batch_start + HUNKS_PER_BATCH]
        prompt = _build_hunk_batch_prompt(batch)
        content = _call_llm(prompt, model=model, project=project, location=location)
        if content is None:
            diagnostics.append(
                Diagnostic(
                    level="warn",
                    code="LLM_BRIEF_HUNK_BATCH_FAILED",
                    message=f"LLM hunk-summary batch failed (offset {batch_start}).",
                )
            )
            continue
        data = _extract_json(content)
        if not data or "hunks" not in data:
            diagnostics.append(
                Diagnostic(
                    level="warn",
                    code="LLM_BRIEF_HUNK_PARSE_FAILED",
                    message=f"Could not parse hunk-summary response (offset {batch_start}).",
                )
            )
            continue
        for entry in data["hunks"]:
            i = entry.get("i")
            if not isinstance(i, int) or i < 1 or i > len(batch):
                continue
            hi, _, _ = batch[i - 1]
            current = hunks_by_idx.get(hi.hunk_id)
            if current is None:
                continue
            one_liner = (entry.get("one_liner") or "").strip()[:200]
            intent_raw = (entry.get("intent") or "unknown").strip()
            intent = intent_raw if intent_raw in _INTENT_VALUES else "unknown"
            if one_liner:
                current.one_liner = one_liner
                # Add an LLM citation; ground it in the original hunk node.
                current.cites.append(
                    Citation(
                        kind="node",
                        ref=current.hunk_id,
                        excerpt=one_liner[:120],
                        derivation=Derivation.LLM,
                        score=0.85,
                    )
                )
            current.intent = intent  # type: ignore[assignment]
            filled += 1
    return filled


# ---------- Call B: PR-level headline ----------


def _build_headline_prompt(brief: Brief) -> str:
    rb = brief.review
    return (
        "Summarise this pull request in one sentence (≤140 chars).\n"
        "Be factual; mention the most consequential change and its blast radius.\n"
        "Do not start with 'This PR'.\n\n"
        f"Title: {brief.pr.title}\n"
        f"PR type: {rb.pr_type} (confidence {rb.pr_type_confidence:.2f})\n"
        f"Risk tier: {rb.risk_tier}\n"
        f"Public symbols modified: {rb.blast_radius.public_symbols_modified}\n"
        f"Caller files: {rb.blast_radius.caller_files}\n"
        f"External refs added: {rb.blast_radius.external_refs_added}\n"
        f"Advisory flags: {rb.advisory_flags}\n"
        f"Body excerpt: {(brief.pr.body or '')[:600]}\n\n"
        'Respond with: {"headline": "..."}'
    )


def fill_headline(
    brief: Brief,
    *,
    diagnostics: List[Diagnostic],
    model: str = DEFAULT_MODEL,
    project: str = DEFAULT_PROJECT,
    location: str = DEFAULT_LOCATION,
) -> bool:
    prompt = _build_headline_prompt(brief)
    content = _call_llm(prompt, model=model, project=project, location=location)
    if content is None:
        diagnostics.append(
            Diagnostic(level="warn", code="LLM_BRIEF_HEADLINE_FAILED", message="Headline LLM call failed.")
        )
        return False
    data = _extract_json(content)
    if not data or "headline" not in data:
        return False
    headline = (data["headline"] or "").strip()[:200]
    if not headline:
        return False
    brief.review.headline = headline
    brief.review.cites.append(
        Citation(
            kind="external_doc",
            ref=brief.pr.url,
            excerpt=headline[:120],
            derivation=Derivation.LLM,
            score=0.85,
        )
    )
    return True


# ---------- Call C: ReviewPlan What/Why/Impact ----------


def _step_context(graph: Graph, brief: Brief, step: ReviewStep) -> str:
    nodes_by_id = {n.id: n for n in graph.nodes}
    target = nodes_by_id.get(step.target)
    target_label = step.target
    target_kind = "unknown"
    if isinstance(target, SymbolNode):
        target_label = target.qualified_name
        target_kind = f"{target.symbol_kind.value} ({target.line_range.start}-{target.line_range.end})"
    elif isinstance(target, HunkNode):
        file_node = nodes_by_id.get(target.file_id)
        target_label = f"{file_node.path}:{target.line_range.start}" if isinstance(file_node, FileNode) else target.id
        target_kind = "hunk"

    callers: List[str] = []
    for e in graph.edges:
        if e.target_id == step.target and e.type in (EdgeType.CALLS, EdgeType.REFERENCES, EdgeType.IMPORTS):
            src = nodes_by_id.get(e.source_id)
            if isinstance(src, SymbolNode):
                callers.append(src.qualified_name)
            elif isinstance(src, FileNode):
                callers.append(src.path)
            else:
                callers.append(e.source_id)
    if isinstance(target, SymbolNode):
        # also gather external refs from this symbol
        externals: List[str] = []
        for e in graph.edges:
            if e.source_id == target.id and e.type == EdgeType.EXTERNAL:
                externals.append(e.target_id)
        ext_part = f", new external_refs: {externals[:5]}" if externals else ""
    else:
        ext_part = ""

    risk = list(step.risk_signals) if step.risk_signals else []
    return (
        f"step.rank={step.rank}\n"
        f"target_label: {target_label}\n"
        f"target_kind: {target_kind}\n"
        f"callers (1-hop): {callers[:6]}\n"
        f"risk_signals: {risk}{ext_part}\n"
    )


def _build_plan_prompt(graph: Graph, brief: Brief) -> str:
    rb = brief.review
    parts = [
        "You are guiding a reviewer through a pull request.",
        "Produce navigation prose for each ranked step. For every step, write:",
        "  what:   ≤2 sentences. The objective change in plain language.",
        "  why:    ≤2 sentences. Tie to author intent (PR title/body) or pr_type. If neither, say 'Author did not state intent for this region.'",
        "  impact: ≤2 sentences. Quote at least one number from blast_radius or one downstream caller.",
        "Plus an `overview` (≤3 sentences tying steps together) and a `title` per step (≤60 chars).",
        "",
        f"PR title: {brief.pr.title}",
        f"PR body: {(brief.pr.body or '')[:800]}",
        f"pr_type: {rb.pr_type}",
        f"risk_tier: {rb.risk_tier}",
        f"blast_radius: caller_files={rb.blast_radius.caller_files}, modules_crossed={rb.blast_radius.modules_crossed}, public_symbols_modified={rb.blast_radius.public_symbols_modified}, external_refs_added={rb.blast_radius.external_refs_added}",
        f"advisory_flags: {rb.advisory_flags}",
        "",
        "Steps:",
    ]
    for step in brief.plan.steps:
        parts.append("---")
        parts.append(_step_context(graph, brief, step))
    parts.append("---")
    parts.append("")
    parts.append(
        'Respond with JSON: {"overview": "...", "steps": [{"rank": 1, "title": "...", "what": "...", "why": "...", "impact": "..."}, ...]}'
    )
    parts.append("No prose outside JSON. Use the `rank` numbers from the steps above.")
    return "\n".join(parts)


def fill_plan_prose(
    graph: Graph,
    brief: Brief,
    *,
    diagnostics: List[Diagnostic],
    model: str = DEFAULT_MODEL,
    project: str = DEFAULT_PROJECT,
    location: str = DEFAULT_LOCATION,
) -> int:
    """Fill `what`/`why`/`impact` on each ReviewStep + `overview` on the plan."""
    if not brief.plan.steps:
        return 0
    prompt = _build_plan_prompt(graph, brief)
    content = _call_llm(prompt, model=model, project=project, location=location)
    if content is None:
        diagnostics.append(
            Diagnostic(level="warn", code="LLM_BRIEF_PLAN_FAILED", message="Plan-prose LLM call failed.")
        )
        return 0
    data = _extract_json(content)
    if not data:
        return 0
    overview = (data.get("overview") or "").strip()[:600]
    if overview:
        brief.plan.overview = overview
        brief.plan.cites.append(
            Citation(
                kind="external_doc",
                ref=brief.pr.url,
                excerpt=overview[:120],
                derivation=Derivation.LLM,
                score=0.85,
            )
        )

    steps_by_rank = {s.rank: s for s in brief.plan.steps}
    filled = 0
    for entry in (data.get("steps") or []):
        rank = entry.get("rank")
        step = steps_by_rank.get(rank) if isinstance(rank, int) else None
        if step is None:
            continue
        title = (entry.get("title") or "").strip()[:120]
        what = (entry.get("what") or "").strip()[:600]
        why = (entry.get("why") or "").strip()[:600]
        impact = (entry.get("impact") or "").strip()[:600]
        if title:
            step.title = title
        if what:
            step.what = what
        if why:
            step.why = why
        if impact:
            step.impact = impact
        # Each prose addition gets a Citation back to the target node.
        for txt in (title, what, why, impact):
            if txt:
                step.cites.append(
                    Citation(
                        kind="node",
                        ref=step.target,
                        excerpt=txt[:120],
                        derivation=Derivation.LLM,
                        score=0.85,
                    )
                )
        filled += 1
    return filled


# ---------- top-level orchestration ----------


def enrich_brief_with_llm(
    graph: Graph,
    brief: Brief,
    *,
    diagnostics: List[Diagnostic],
    model: str = DEFAULT_MODEL,
    project: str = DEFAULT_PROJECT,
    location: str = DEFAULT_LOCATION,
) -> Brief:
    if not is_available():
        diagnostics.append(
            Diagnostic(
                level="info",
                code="LLM_BRIEF_UNAVAILABLE",
                message="litellm not installed; --llm-summarise no-op.",
            )
        )
        return brief
    n_hunks = fill_hunk_insights(graph, brief, diagnostics=diagnostics, model=model, project=project, location=location)
    headline_filled = fill_headline(brief, diagnostics=diagnostics, model=model, project=project, location=location)
    n_steps = fill_plan_prose(graph, brief, diagnostics=diagnostics, model=model, project=project, location=location)
    if n_hunks or headline_filled or n_steps:
        brief.llm_used = True
    diagnostics.append(
        Diagnostic(
            level="info",
            code="LLM_BRIEF_SUMMARY",
            message=f"Filled {n_hunks} hunk insights, headline={'yes' if headline_filled else 'no'}, plan steps {n_steps}/{len(brief.plan.steps)}.",
        )
    )
    return brief
