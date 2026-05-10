"use client";

import { z } from "zod";
import { useComponent } from "@copilotkit/react-core/v2";

const ParamsSchema = z.object({
  items: z.array(
    z.object({
      question: z.string(),
      why: z.string().optional(),
    }),
  ),
});

export function useRenderOpenQuestionsTool(): void {
  useComponent({
    name: "render_open_questions",
    description:
      "Yellow callout listing open questions or unverified items. Use when neighbors are ambiguous/llm_inferred or you couldn't ground an answer.",
    parameters: ParamsSchema,
    render: ({ items }) => {
      const list = items ?? [];
      return (
        <div className="my-2 border border-amber-300 bg-amber-50 rounded-md p-2 text-xs">
          <div className="text-[10px] uppercase font-semibold text-amber-800 mb-1">
            Open questions ({list.length})
          </div>
          <ul className="space-y-1">
            {list.map((item, i) => (
              <li key={i}>
                <div className="text-amber-900">{item?.question}</div>
                {item?.why && (
                  <div className="text-amber-700 text-[11px] italic">
                    {item.why}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      );
    },
  });
}
