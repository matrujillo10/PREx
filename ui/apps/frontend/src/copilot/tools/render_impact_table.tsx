"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const RowSchema = z.object({
  node_id: z.string(),
  relation: z.enum(["upstream", "downstream"]),
  edge_type: z.string(),
  confidence: z.enum(["exact", "ambiguous", "llm_inferred"]).optional(),
  note: z.string().optional(),
});

const ParamsSchema = z.object({
  title: z.string().optional(),
  rows: z.array(RowSchema),
});

export function useRenderImpactTableTool(): void {
  useComponent({
    name: "render_impact_table",
    description:
      "Render a structured impact table of nodes affected by, or affecting, the selected node. Prefer this over inline markdown tables.",
    parameters: ParamsSchema,
    render: ({ title, rows }) => {
      const list = rows ?? [];
      return (
        <div className="my-2 border border-gray-200 rounded-md overflow-hidden text-xs">
          {title && (
            <div className="bg-gray-100 px-3 py-1.5 font-semibold text-gray-700 border-b">
              {title}
            </div>
          )}
          <table className="w-full">
            <thead className="bg-gray-50 text-gray-500">
              <tr>
                <th className="text-left px-3 py-1.5 font-medium">Node</th>
                <th className="text-left px-3 py-1.5 font-medium">Relation</th>
                <th className="text-left px-3 py-1.5 font-medium">Edge</th>
                <th className="text-left px-3 py-1.5 font-medium">Conf.</th>
              </tr>
            </thead>
            <tbody>
              {list.map((r, i) => (
                <tr key={i} className="border-t">
                  <td className="px-3 py-1.5 font-mono">{r?.node_id}</td>
                  <td className="px-3 py-1.5">
                    <span
                      className={
                        r?.relation === "upstream"
                          ? "text-blue-700"
                          : "text-amber-700"
                      }
                    >
                      {r?.relation}
                    </span>
                  </td>
                  <td className="px-3 py-1.5">{r?.edge_type}</td>
                  <td className="px-3 py-1.5 text-gray-500">
                    {r?.confidence ?? "exact"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    },
  });
}
