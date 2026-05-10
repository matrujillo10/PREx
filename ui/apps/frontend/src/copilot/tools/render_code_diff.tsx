"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const ParamsSchema = z.object({
  path: z.string(),
  patch: z.string(),
});

export function useRenderCodeDiffTool(): void {
  useComponent({
    name: "render_code_diff",
    description:
      "Render a unified-diff patch for a single file with line-level coloring. Use when showing the user a specific hunk.",
    parameters: ParamsSchema,
    render: ({ path, patch }) => {
      const lines = (patch ?? "").split("\n");
      return (
        <div className="my-2 border border-gray-200 rounded-md overflow-hidden text-xs font-mono">
          <div className="bg-gray-100 px-3 py-1.5 font-semibold text-gray-700 border-b">
            {path}
          </div>
          <pre className="bg-white p-2 overflow-x-auto">
            {lines.map((line, i) => {
              const cls =
                line.startsWith("+") && !line.startsWith("+++")
                  ? "bg-green-50 text-green-800"
                  : line.startsWith("-") && !line.startsWith("---")
                    ? "bg-red-50 text-red-800"
                    : line.startsWith("@@")
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700";
              return (
                <div key={i} className={`${cls} px-2 leading-tight`}>
                  {line || " "}
                </div>
              );
            })}
          </pre>
        </div>
      );
    },
  });
}
