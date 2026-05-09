"use client";

import React, { useMemo } from "react";
import { CopilotChat, useAgentContext } from "@copilotkit/react-core/v2";
import {
  GraphPromptsConfig,
  GraphNodePayload,
  GraphEdgePayload,
  PRImpactGraph,
} from "../../config/graphConfigSchema";
import { useGraphCopilotTools } from "../../copilot/tools";

interface AgentChatBubbleProps {
  selectedNode: GraphNodePayload;
  graph: PRImpactGraph;
  promptsConfig: GraphPromptsConfig;
  analysis: string;
  onClose: () => void;
}

interface NeighborhoodEdge {
  edge: GraphEdgePayload;
  direction: "incoming" | "outgoing";
}

function computeNeighborhood(
  selectedId: string,
  graph: PRImpactGraph,
): { nodes: GraphNodePayload[]; edges: NeighborhoodEdge[] } {
  const incident: NeighborhoodEdge[] = [];
  const neighborIds = new Set<string>();
  for (const edge of graph.edges) {
    if (edge.source_id === selectedId) {
      incident.push({ edge, direction: "outgoing" });
      neighborIds.add(edge.target_id);
    } else if (edge.target_id === selectedId) {
      incident.push({ edge, direction: "incoming" });
      neighborIds.add(edge.source_id);
    }
  }
  const nodes = graph.nodes.filter((n) => neighborIds.has(n.id));
  return { nodes, edges: incident };
}

export function AgentChatBubble({
  selectedNode,
  graph,
  promptsConfig,
  analysis,
  onClose,
}: AgentChatBubbleProps) {
  useGraphCopilotTools();

  const changeState = selectedNode.change_state || "unchanged";
  const kind = selectedNode.kind || "module";

  const changePromptContext =
    promptsConfig.changeStates[changeState] || promptsConfig.changeStates["unchanged"];
  const kindPromptContext =
    promptsConfig.kinds[kind] || promptsConfig.kinds["module"];

  const combinedPrompt = `${changePromptContext.initialPrompt} \n\n${kindPromptContext.initialPrompt}`;
  const questions = [...changePromptContext.questions, ...kindPromptContext.questions];

  const nodeName =
    "name" in selectedNode
      ? selectedNode.name
      : "path" in selectedNode
        ? selectedNode.path
        : "Hunk";

  const neighborhood = useMemo(
    () => computeNeighborhood(selectedNode.id, graph),
    [selectedNode.id, graph],
  );

  const contextValue = useMemo(
    () =>
      JSON.stringify({
        analysis,
        node: selectedNode,
        change_state: changeState,
        kind,
        name: nodeName,
        neighbors: neighborhood.nodes,
        neighbor_edges: neighborhood.edges,
        pr: graph.pr,
        ui_hints: {
          change_state_prompt: changePromptContext.initialPrompt,
          kind_prompt: kindPromptContext.initialPrompt,
          suggested_questions: questions,
        },
      }),
    [
      analysis,
      selectedNode,
      changeState,
      kind,
      nodeName,
      neighborhood,
      graph.pr,
      changePromptContext,
      kindPromptContext,
      questions,
    ],
  );

  useAgentContext({
    description:
      "Selected PR-impact-graph node under review, plus its 1-hop neighborhood. JSON-encoded; deserialize before reasoning. Answer strictly with respect to this node and follow the requested analysis.",
    value: contextValue,
  });

  return (
    <div className="absolute right-4 top-4 w-[28rem] max-h-[90vh] flex flex-col bg-white shadow-2xl rounded-xl border border-gray-200 overflow-hidden z-50">
      <div className="flex justify-between items-center bg-gray-100 px-4 py-3 border-b">
        <h3 className="font-semibold text-gray-800 text-sm">
          Analysis: <span className="font-mono text-xs ml-1">{analysis}</span>
          <span className="text-gray-400 mx-1">·</span>
          <span className="font-mono text-xs">{nodeName}</span>
        </h3>
        <button onClick={onClose} className="text-gray-500 hover:text-black">
          ×
        </button>
      </div>

      <div className="flex-1 p-3 overflow-y-auto">
        <details className="text-xs bg-blue-50 border border-blue-200 text-blue-800 rounded p-2 mb-3">
          <summary className="cursor-pointer font-semibold">
            Context · {neighborhood.nodes.length} neighbor(s) ·{" "}
            {combinedPrompt.length} chars of UI hints
          </summary>
          <div className="mt-2 whitespace-pre-wrap">{combinedPrompt}</div>
          {questions.length > 0 && (
            <ul className="list-disc pl-5 mt-2">
              {questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          )}
        </details>

        <div className="h-[28rem] border rounded-md shadow-inner bg-gray-50">
          <CopilotChat
            labels={{
              chatInputPlaceholder: `Ask about this ${changeState} ${kind}: ${nodeName}`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
