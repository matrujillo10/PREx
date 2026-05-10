"""Anthropic-powered chat agent for the PREx UI.

The frontend POSTs `{messages, scope}` to `/api/chat`; this module:
  - loads `brief.json` + `graph.json` from the artifact dir
  - builds a scoped system prompt + condensed graph context
  - registers the six A2GUI tools as Anthropic tool definitions
  - streams Claude's response (text + tool_use) as SSE events

Streaming format on the wire (Server-Sent Events):
    event: text   data: {"text": "..."}
    event: tool   data: {"name": "render_treemap", "args": {...}, "id": "tu_..."}
    event: done   data: {}
"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import anthropic


MODEL = os.environ.get("PREX_AGENT_MODEL", "claude-sonnet-4-5-20250929")
# Allow override; default to a fast Sonnet. The agent doesn't need the largest model.


# ---------- tool definitions (mirror prex-ui/src/a2gui/schemas.ts) ----------


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "render_treemap",
        "description": "Render a treemap of changed files with size + sensitivity coding. Use when answering 'where is the change densest' / 'which files matter most'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "additions": {"type": "integer", "minimum": 0},
                            "deletions": {"type": "integer", "minimum": 0},
                            "hunkCount": {"type": "integer", "minimum": 0},
                            "generated": {"type": "boolean"},
                            "sensitive": {"type": "boolean"},
                        },
                        "required": ["path", "additions", "deletions"],
                    },
                },
            },
            "required": ["files"],
        },
    },
    {
        "name": "render_coupling_map",
        "description": "Render a coupling map of related symbols/files. Use to surface hidden couplings (e.g. when one symbol is reused across unrelated endpoints). Mark cross-symbol references inferred by the LLM with derivation='llm' so they are dashed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "kind": {"type": "string", "enum": ["symbol", "file", "external_ref", "module"]},
                            "sensitive": {"type": "boolean"},
                        },
                        "required": ["id", "label"],
                    },
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "derivation": {"type": "string", "enum": ["ast", "diff", "crossref_text", "llm", "manifest", "heuristic"]},
                            "label": {"type": "string"},
                        },
                        "required": ["from", "to", "derivation"],
                    },
                },
            },
            "required": ["nodes", "edges"],
        },
    },
    {
        "name": "render_class_diff",
        "description": "Render a before/after class shape with added/removed/modified fields. Use for 'walk me through this class change' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "before": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "state": {"type": "string", "enum": ["unchanged", "added", "removed", "modified"]},
                                },
                                "required": ["name"],
                            },
                        },
                    },
                    "required": ["name", "fields"],
                },
                "after": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "state": {"type": "string", "enum": ["unchanged", "added", "removed", "modified"]},
                                },
                                "required": ["name"],
                            },
                        },
                    },
                    "required": ["name", "fields"],
                },
            },
            "required": ["before", "after"],
        },
    },
    {
        "name": "render_blast_radius",
        "description": "Render a 1-hop blast-radius around a target symbol. Use to answer 'who is affected by this change'. Inferred edges go dashed when derivation=llm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "target": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "inferred": {"type": "boolean"},
                    },
                    "required": ["id", "label"],
                },
                "neighborhood": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                            "inferred": {"type": "boolean"},
                        },
                        "required": ["id", "label"],
                    },
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "derivation": {"type": "string", "enum": ["ast", "diff", "crossref_text", "llm", "manifest", "heuristic"]},
                        },
                        "required": ["from", "to", "derivation"],
                    },
                },
            },
            "required": ["target", "neighborhood", "edges"],
        },
    },
    {
        "name": "render_data_flow_chain",
        "description": "Render a horizontal data-flow chain of cards joined by arrows. Use for 'how does the field flow through the system' answers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "fileLoc": {"type": "string"},
                            "role": {"type": "string", "enum": ["source", "transform", "sink"]},
                        },
                        "required": ["label"],
                    },
                },
            },
            "required": ["cards"],
        },
    },
    {
        "name": "render_sequence",
        "description": "Render a sequence diagram with actor lifelines + messages. message.kind sql highlights SQL traffic in accent. Use for 'show me the call sequence' answers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "source": {"type": "string"},
                "actors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                        },
                        "required": ["id", "name"],
                    },
                },
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string"},
                            "to": {"type": "string"},
                            "label": {"type": "string"},
                            "kind": {"type": "string", "enum": ["sync", "reply", "sql"]},
                        },
                        "required": ["from", "to", "label"],
                    },
                },
            },
            "required": ["actors", "messages"],
        },
    },
]


# ---------- prompt assembly ----------


SYSTEM_BASE = textwrap.dedent("""\
    You are PREx Copilot, a visual-first assistant for a peer reviewer reading a pull request.
    The reviewer did NOT write this PR. Default to DIAGRAMS, not prose.

    HARD RULES on output:
      - Prefer 1–3 diagrams over paragraphs. Multiple tool_use blocks in one turn are fine.
      - Text is a CAPTION, not the answer. Cap at ~30 words total per turn unless the reviewer
        explicitly asks for prose. One short sentence per diagram is plenty.
      - If a question can be answered by a single diagram, emit only the diagram + a ≤12-word lead-in.
      - Never restate what the diagram already shows.
      - Never include unified-diff content in prose; the reviewer has the diff column.

    Tool catalog — pick the SHAPE that fits, then fill it:
      - render_treemap          (file-by-file change density)
      - render_coupling_map     (cross-symbol/file couplings; derivation='llm' = dashed accent)
      - render_class_diff       (before/after class shape with added/removed/modified fields)
      - render_blast_radius     (1-hop neighbourhood around a target symbol)
      - render_data_flow_chain  (left→right cards joined by arrows)
      - render_sequence         (actor lifelines + messages; kind='sql' for db hops)

    Default mappings (use these unless the reviewer overrides):
      - "where is the change densest" / "what files matter"        → render_treemap
      - "anything sneaky" / "hidden coupling" / "who else uses X"  → render_coupling_map
      - "what changed in this class"                                → render_class_diff
      - "who is affected by this" / "blast radius"                  → render_blast_radius
      - "how does X flow through" / "trace the field"               → render_data_flow_chain
      - "what's the sequence of calls" / "show me the SQL path"     → render_sequence

    Faithfulness rules:
      - For tool args, derive ids from the graph node ids you have seen below; do not invent.
      - Mark any edge or node you inferred (not in the graph data) with derivation='llm'.
      - If the reviewer asks something you cannot ground, say so in ≤15 words and emit no diagram.
""")


def _condense_graph(graph: Dict[str, Any], max_nodes: int = 80) -> Dict[str, Any]:
    """Project the graph down to the most relevant chunk for prompt context."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    keep_kinds = {"symbol", "file", "external_ref", "caller_stub"}
    changed = [n for n in nodes if n.get("kind") in keep_kinds and n.get("change_state") != "unchanged"]
    callers = [n for n in nodes if n.get("kind") == "caller_stub"]
    files = [n for n in nodes if n.get("kind") == "file" and n.get("change_state") != "unchanged"]
    selected: List[Dict[str, Any]] = []
    seen_ids = set()
    for n in changed + callers + files:
        if n["id"] in seen_ids:
            continue
        seen_ids.add(n["id"])
        selected.append({
            "id": n["id"],
            "kind": n.get("kind"),
            "qualified_name": n.get("qualified_name") or n.get("path") or n.get("name"),
            "file_id": n.get("file_id"),
            "public": n.get("public"),
            "change_state": n.get("change_state"),
        })
        if len(selected) >= max_nodes:
            break
    rel_edges = [
        {
            "type": e["type"],
            "source_id": e["source_id"],
            "target_id": e["target_id"],
            "derivation": e["derivation"],
        }
        for e in edges
        if e.get("type") in ("calls", "references", "imports", "external", "covers")
        and e.get("source_id") in seen_ids
        and e.get("target_id") in seen_ids
    ][:200]
    return {"nodes": selected, "edges": rel_edges}


def build_system_prompt(brief: Dict[str, Any], graph: Dict[str, Any], scope: str) -> str:
    pr = brief["pr"]
    review = brief["review"]
    parts = [SYSTEM_BASE]
    parts.append("\n--- PR ---")
    parts.append(f"repo: {pr['repo']}#{pr['number']}")
    parts.append(f"title: {pr['title']}")
    parts.append(f"author: {pr['author']}  branch: {pr['head_ref']} -> {pr['base_ref']}")
    parts.append(f"+{pr['additions']} / -{pr['deletions']} across {pr['changed_files']} files")
    if pr.get("body"):
        parts.append(f"body excerpt: {pr['body'][:600]}")
    parts.append("\n--- ReviewBrief ---")
    parts.append(f"pr_type={review['pr_type']} (conf {review['pr_type_confidence']:.2f})")
    parts.append(f"risk_tier={review['risk_tier']}  risk_score={review['risk_score']:.2f}")
    blast = review["blast_radius"]
    parts.append(
        f"blast_radius: caller_files={blast['caller_files']}  modules_crossed={blast['modules_crossed']}  "
        f"public_symbols_modified={blast['public_symbols_modified']}  external_refs_added={blast['external_refs_added']}"
    )
    parts.append(f"advisory_flags: {review['advisory_flags']}")
    if review.get("headline"):
        parts.append(f"headline: {review['headline']}")
    parts.append("\n--- Plan steps (rank · title · risk_signals) ---")
    for s in brief["plan"]["steps"]:
        parts.append(
            f"  {s['rank']}. {(s.get('title') or s['target'])[:80]}  signals={s['risk_signals']}"
        )

    if scope.startswith("step:"):
        try:
            rank = int(scope.split(":", 1)[1])
        except ValueError:
            rank = None
        if rank is not None:
            for s in brief["plan"]["steps"]:
                if s["rank"] == rank:
                    parts.append(f"\n--- ACTIVE STEP {rank} ---")
                    parts.append(f"target: {s['target']}")
                    if s.get("title"):
                        parts.append(f"title: {s['title']}")
                    if s.get("what"):
                        parts.append(f"what: {s['what']}")
                    if s.get("why"):
                        parts.append(f"why: {s['why']}")
                    if s.get("impact"):
                        parts.append(f"impact: {s['impact']}")
                    parts.append(f"risk_signals: {s['risk_signals']}")
                    break

    condensed = _condense_graph(graph)
    parts.append("\n--- Graph (condensed) ---")
    parts.append(json.dumps(condensed, indent=None, separators=(",", ":")))

    return "\n".join(parts)


# ---------- streaming ----------


def stream_chat(
    artifact_dir: Path,
    messages: List[Dict[str, Any]],
    scope: str,
    *,
    api_key: Optional[str] = None,
    model: str = MODEL,
) -> Iterable[bytes]:
    """Yield SSE-encoded chunks for the chat reply."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield _sse(
            "error",
            {"message": "ANTHROPIC_API_KEY not set; set it in .env to enable chat."},
        )
        yield _sse("done", {})
        return

    brief = json.loads((artifact_dir / "brief.json").read_text(encoding="utf-8"))
    graph = json.loads((artifact_dir / "graph.json").read_text(encoding="utf-8"))
    system = build_system_prompt(brief, graph, scope)

    client = anthropic.Anthropic(api_key=api_key)
    try:
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=TOOLS,
        ) as stream:
            tool_buffer: Dict[int, Dict[str, Any]] = {}
            for event in stream:
                kind = getattr(event, "type", "")
                if kind == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block is not None and getattr(block, "type", "") == "tool_use":
                        idx = getattr(event, "index", 0)
                        tool_buffer[idx] = {
                            "name": block.name,
                            "id": getattr(block, "id", None),
                            "raw_input": "",
                        }
                elif kind == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta is None:
                        continue
                    dt = getattr(delta, "type", "")
                    if dt == "text_delta":
                        text = getattr(delta, "text", "") or ""
                        if text:
                            yield _sse("text", {"text": text})
                    elif dt == "input_json_delta":
                        idx = getattr(event, "index", 0)
                        partial = getattr(delta, "partial_json", "") or ""
                        if idx in tool_buffer:
                            tool_buffer[idx]["raw_input"] += partial
                elif kind == "content_block_stop":
                    idx = getattr(event, "index", 0)
                    if idx in tool_buffer:
                        rec = tool_buffer.pop(idx)
                        try:
                            args = json.loads(rec["raw_input"]) if rec["raw_input"] else {}
                        except json.JSONDecodeError:
                            args = {}
                        yield _sse(
                            "tool",
                            {"id": rec["id"], "name": rec["name"], "args": args},
                        )
    except anthropic.APIError as e:
        yield _sse("error", {"message": f"Anthropic error: {e}"})
    except Exception as e:  # pragma: no cover
        yield _sse("error", {"message": f"agent error: {type(e).__name__}: {e}"})
    yield _sse("done", {})


def _sse(event: str, payload: Dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")
