"use client";

/**
 * GenUI tool registry.
 *
 * Each tool lives in its own file as a `useXxxTool()` hook that calls
 * CopilotKit's `useComponent`. Add a new tool by dropping a file here
 * and importing it into `useGraphCopilotTools` below.
 *
 * Tools are registered only while the chat bubble is mounted — they
 * scope to the v2 CopilotKitProvider higher in the tree.
 */

import { useRenderImpactTableTool } from "./render_impact_table";
import { useRenderCodeDiffTool } from "./render_code_diff";

export function useGraphCopilotTools(): void {
  useRenderImpactTableTool();
  useRenderCodeDiffTool();
}
