"use client";

/**
 * GenUI tool registry.
 *
 * Each tool is one file exporting a `useXxxTool()` hook that wraps
 * `useComponent` from `@copilotkit/react-core/v2`. To add a tool:
 *   1. Drop a file here, e.g. `render_foo.tsx`.
 *   2. Add `import { useRenderFooTool } from "./render_foo";` below.
 *   3. Add `useRenderFooTool` to the `TOOL_HOOKS` array.
 *   4. Document its name + parameters in `apps/agent/prompts/base.md`
 *      so the agent knows it can call it.
 *
 * Hook ordering must be stable across renders — the array literal
 * keeps it that way. Tools register only while the chat bubble is
 * mounted (this hook is called from inside `AgentChatBubble`).
 */

import { useRenderImpactTableTool } from "./render_impact_table";
import { useRenderCodeDiffTool } from "./render_code_diff";
import { useRenderVerdictTool } from "./render_verdict";
import { useRenderNeighborsTool } from "./render_neighbors";
import { useRenderOpenQuestionsTool } from "./render_open_questions";
import { useRenderFileRefTool } from "./render_file_ref";

const TOOL_HOOKS: ReadonlyArray<() => void> = [
  useRenderVerdictTool,
  useRenderImpactTableTool,
  useRenderNeighborsTool,
  useRenderOpenQuestionsTool,
  useRenderCodeDiffTool,
  useRenderFileRefTool,
];

export function useGraphCopilotTools(): void {
  for (const useTool of TOOL_HOOKS) useTool();
}
