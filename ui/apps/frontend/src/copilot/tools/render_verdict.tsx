"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const ParamsSchema = z.object({
  headline: z.string(),
  kind: z.string(),
  change_state: z.string(),
  scope: z.enum(["contained", "local", "cross-cutting"]),
  public: z.boolean().optional(),
});

const SCOPE_STYLE: Record<string, string> = {
  contained: "bg-gray-100 text-gray-700 border-gray-300",
  local: "bg-blue-50 text-blue-700 border-blue-300",
  "cross-cutting": "bg-amber-50 text-amber-800 border-amber-300",
};

const CHANGE_STYLE: Record<string, string> = {
  added: "bg-green-100 text-green-800",
  removed: "bg-red-100 text-red-800",
  modified: "bg-yellow-100 text-yellow-800",
  unchanged: "bg-gray-100 text-gray-700",
};

export function useRenderVerdictTool(): void {
  useComponent({
    name: "render_verdict",
    description:
      "One-line classification chip. Always call this first on an analysis response.",
    parameters: ParamsSchema,
    render: ({ headline, kind, change_state, scope, public: isPublic }) => (
      <div
        className={`my-2 border rounded-md px-3 py-2 text-xs flex flex-wrap items-center gap-2 ${SCOPE_STYLE[scope] ?? SCOPE_STYLE.local}`}
      >
        <span className="font-semibold">{headline}</span>
        <span
          className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${CHANGE_STYLE[change_state] ?? CHANGE_STYLE.unchanged}`}
        >
          {change_state}
        </span>
        <span className="px-1.5 py-0.5 rounded bg-white/60 text-[10px] font-mono">
          {kind}
        </span>
        <span className="px-1.5 py-0.5 rounded bg-white/60 text-[10px] font-mono">
          {scope}
        </span>
        {isPublic && (
          <span className="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 text-[10px] font-mono">
            public
          </span>
        )}
      </div>
    ),
  });
}
