"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const ParamsSchema = z.object({
  path: z.string(),
  start: z.number().int().min(1).optional(),
  end: z.number().int().min(1).optional(),
  label: z.string().optional(),
});

export function useRenderFileRefTool(): void {
  useComponent({
    name: "render_file_ref",
    description:
      "Inline tag pointing at a source location: path with optional line range and label.",
    parameters: ParamsSchema,
    render: ({ path, start, end, label }) => {
      const range =
        start !== undefined
          ? end !== undefined && end !== start
            ? `:${start}-${end}`
            : `:${start}`
          : "";
      return (
        <span className="inline-flex items-center gap-1 my-1 px-2 py-0.5 rounded border border-gray-300 bg-gray-50 text-[11px] font-mono">
          {label && <span className="text-gray-500">{label}</span>}
          <span className="text-gray-800">
            {path}
            {range}
          </span>
        </span>
      );
    },
  });
}
