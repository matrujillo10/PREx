"""LangGraph entry point for the PREx graph-diff analyst.

Selected by `langgraph.json` → exposes `graph` to `langgraph dev`.
Imports nothing from the legacy leads stack — that code remains on disk
under `src/` (canvas.py, lead_*.py, notion_*.py, prompts.py, runtime.py)
but is not loaded by this entrypoint.
"""

from __future__ import annotations

from dotenv import load_dotenv

from src.graph_agent import build_graph_agent


load_dotenv()


graph = build_graph_agent()
