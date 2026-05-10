"""Graph-diff analyst agent.

Builds a LangChain react agent whose system prompt is composed from
externalized markdown files under `apps/agent/prompts/`:

- `prompts/base.md` — agent role + tool contract + output rules.
- `prompts/analyses/<name>.md` — one file per analysis flow. All are
  loaded at boot and appended to the system prompt under an
  "Available analyses" section, keyed by file stem. The frontend
  selects one per turn via AG-UI agent context (`analysis: <name>`).

Drop a new file under `prompts/analyses/` and restart the agent to
extend the analysis surface — no code changes.

Tools
-----
- ``read_source`` — read a file at `CODEBASE_ROOT/path`, with optional
  1-indexed inclusive line range. Required for any analysis that needs
  to consult source beyond what the graph already carries.

The codebase root must be supplied via the `CODEBASE_ROOT` environment
variable when launching `langgraph dev`. Fails fast if unset — there is
no default.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.state import CompiledStateGraph

from copilotkit import CopilotKitMiddleware

from .timing import TimingMiddleware


# --- prompt loading -----------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_ANALYSES_DIR = _PROMPTS_DIR / "analyses"


def _load_base_prompt() -> str:
    base = _PROMPTS_DIR / "base.md"
    if not base.is_file():
        raise FileNotFoundError(f"missing required prompt: {base}")
    return base.read_text(encoding="utf-8").strip()


def _load_analyses() -> dict[str, str]:
    if not _ANALYSES_DIR.is_dir():
        raise FileNotFoundError(f"missing analyses dir: {_ANALYSES_DIR}")
    out: dict[str, str] = {}
    for path in sorted(_ANALYSES_DIR.glob("*.md")):
        out[path.stem] = path.read_text(encoding="utf-8").strip()
    if not out:
        raise FileNotFoundError(
            f"no analyses found in {_ANALYSES_DIR} — add at least one *.md file"
        )
    return out


def _compose_system_prompt() -> str:
    base = _load_base_prompt()
    analyses = _load_analyses()
    sections = [base, "", "# Available analyses", ""]
    for name, body in analyses.items():
        sections.append(f"## `{name}`\n\n{body}\n")
    return "\n".join(sections)


# --- tools --------------------------------------------------------------


def _resolve_codebase_root() -> Path:
    raw = os.getenv("CODEBASE_ROOT")
    if not raw:
        raise RuntimeError(
            "CODEBASE_ROOT env var is unset. Set it to the absolute path "
            "of the codebase the loaded graph was built from, e.g. "
            "`CODEBASE_ROOT=/abs/path npm run dev:agent`."
        )
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"CODEBASE_ROOT={root} is not an existing directory")
    return root


@tool
def read_source(path: str, start: int | None = None, end: int | None = None) -> str:
    """Read a repo-relative file from the codebase.

    Args:
        path: Repo-relative path, e.g. ``src/core/utils.ts``.
        start: 1-indexed start line (inclusive). Optional.
        end: 1-indexed end line (inclusive). Optional. Requires `start`.

    Returns the requested lines, prefixed with their 1-indexed line
    numbers. Returns an ``ERROR: ...`` string (not an exception) for
    expected failures (missing path, bad range, traversal) so the model
    can adapt. Raises only on configuration errors (e.g. CODEBASE_ROOT
    unset) which the model cannot recover from.
    """
    root = _resolve_codebase_root()
    target = (root / path).resolve()
    if root not in target.parents and target != root:
        return f"ERROR: path {path!r} escapes CODEBASE_ROOT"
    if not target.is_file():
        return f"ERROR: no such file under CODEBASE_ROOT: {path}"

    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if start is None and end is None:
        sl, el = 1, len(lines)
    else:
        if start is None:
            return "ERROR: `end` provided without `start`"
        sl = start
        el = end if end is not None else start
    if sl < 1 or el < sl or sl > len(lines):
        return (
            f"ERROR: invalid line range {sl}-{el} for {path} "
            f"(file has {len(lines)} lines)"
        )
    el = min(el, len(lines))
    width = len(str(el))
    return "\n".join(
        f"{str(i).rjust(width)}: {lines[i - 1]}" for i in range(sl, el + 1)
    )


# --- graph builder ------------------------------------------------------


def build_graph_agent() -> CompiledStateGraph:
    """Compile the graph-diff analyst agent.

    Model: Gemini Flash-Lite (same as the starter agent — keeps the
    existing GEMINI_API_KEY wiring). Override the model id with
    ``GEMINI_MODEL`` if you want a different tier.

    Fails fast if neither ``GEMINI_API_KEY`` nor ``GOOGLE_API_KEY`` is set.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is unset. "
            "Set it in apps/agent/.env."
        )

    model_id = os.getenv("GEMINI_MODEL")
    if not model_id:
        raise RuntimeError(
            "GEMINI_MODEL is unset. Set it in apps/agent/.env "
            "(e.g. GEMINI_MODEL=gemini-3.1-flash-lite)."
        )

    system_prompt = _compose_system_prompt()
    llm = ChatGoogleGenerativeAI(
        model=model_id,
        temperature=0,
        api_key=api_key,
    )

    middleware = [TimingMiddleware(), CopilotKitMiddleware()]

    return create_agent(
        model=llm,
        tools=[read_source],
        system_prompt=system_prompt,
        middleware=middleware,
    )
