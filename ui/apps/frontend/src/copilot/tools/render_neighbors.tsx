"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const ParamsSchema = z.object({
  upstream: z.array(z.string()).default([]),
  downstream: z.array(z.string()).default([]),
});

function Column({ title, ids, color }: { title: string; ids: string[]; color: string }) {
  if (ids.length === 0) return null;
  return (
    <div className="flex-1 min-w-0">
      <div className={`text-[10px] uppercase font-semibold mb-1 ${color}`}>
        {title} ({ids.length})
      </div>
      <ul className="space-y-0.5">
        {ids.map((id) => (
          <li key={id} className="font-mono text-[11px] truncate" title={id}>
            {id}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function useRenderNeighborsTool(): void {
  useComponent({
    name: "render_neighbors",
    description:
      "Compact upstream/downstream split list of node ids. Use for 1–6 neighbors when an edge-type breakdown isn't needed.",
    parameters: ParamsSchema,
    render: ({ upstream, downstream }) => (
      <div className="my-2 border border-gray-200 rounded-md p-2 flex gap-3 text-xs">
        <Column title="Upstream" ids={upstream ?? []} color="text-blue-700" />
        <Column title="Downstream" ids={downstream ?? []} color="text-amber-700" />
      </div>
    ),
  });
}
