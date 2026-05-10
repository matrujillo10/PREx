"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  CopilotChat,
  useAgent,
  useAgentContext,
  useConfigureSuggestions,
} from "@copilotkit/react-core/v2";
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

  const questions = [
    ...changePromptContext.questions,
    ...kindPromptContext.questions,
  ];

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

  useConfigureSuggestions(
    {
      instructions: [
        `You are suggesting follow-up questions a PR reviewer might ask about the currently selected ${changeState} ${kind} "${nodeName}" under the "${analysis}" analysis.`,
        `Use these UI hints as seeds (rewrite to fit the exact node):`,
        ...questions.map((q) => `- ${q}`),
        `Each suggestion must be ≤ 8 words, action-oriented, and answerable from the node + its 1-hop neighborhood.`,
      ].join("\n"),
      minSuggestions: 2,
      maxSuggestions: 4,
      available: "always",
    },
    [analysis, selectedNode.id],
  );

  const { agent } = useAgent();
  const [runStatus, setRunStatus] = useState<
    "idle" | "running" | "ok" | "error"
  >("idle");
  const [runError, setRunError] = useState<string | null>(null);
  const [runStartMs, setRunStartMs] = useState<number | null>(null);
  const [tickMs, setTickMs] = useState<number>(0);

  useEffect(() => {
    if (runStatus !== "running" || runStartMs === null) return;
    const id = window.setInterval(() => {
      setTickMs(Date.now() - runStartMs);
    }, 250);
    return () => window.clearInterval(id);
  }, [runStatus, runStartMs]);

  useEffect(() => {
    if (!agent) return;
    let cancelled = false;
    (async () => {
      await Promise.resolve();
      if (cancelled) return;
      agent.addMessage({
        id: `kickoff-${selectedNode.id}-${Date.now()}`,
        role: "user",
        content: `Run \`${analysis}\` analysis on the selected node now.`,
      } as any);
      const startedAt = Date.now();
      setRunStartMs(startedAt);
      setTickMs(0);
      setRunStatus("running");
      setRunError(null);
      try {
        await agent.runAgent();
        if (!cancelled) setRunStatus("ok");
      } catch (e) {
        if (!cancelled) {
          setRunStatus("error");
          setRunError(e instanceof Error ? e.message : String(e));
          console.error("[AgentChatBubble] runAgent failed", e);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [agent, selectedNode.id, analysis]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    console.debug("[AgentChatBubble] context", {
      analysis,
      node: selectedNode,
      neighbors: neighborhood.nodes,
      neighbor_edges: neighborhood.edges,
      ui_hints: {
        change_state_prompt: changePromptContext.initialPrompt,
        kind_prompt: kindPromptContext.initialPrompt,
        suggested_questions: questions,
      },
    });
  }, [
    analysis,
    selectedNode,
    neighborhood,
    changePromptContext,
    kindPromptContext,
    questions,
  ]);

  return (
    <div className="absolute right-4 top-4 w-[28rem] max-h-[90vh] flex flex-col bg-white shadow-2xl rounded-xl border border-gray-200 overflow-hidden z-50">
      <div className="flex justify-between items-center bg-gray-100 px-4 py-2.5 border-b gap-2">
        <h3 className="font-semibold text-gray-800 text-sm truncate min-w-0">
          <span className="text-gray-500">{analysis}</span>
          <span className="text-gray-300 mx-1">·</span>
          <span className="font-mono text-xs">{nodeName}</span>
        </h3>
        <StatusBadge status={runStatus} elapsedMs={tickMs} error={runError} />
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-black shrink-0"
        >
          ×
        </button>
      </div>

      <div className="flex-1 min-h-0 bg-gray-50">
        <CopilotChat
          labels={{
            chatInputPlaceholder: `Ask about this ${changeState} ${kind}`,
          }}
        />
      </div>

      {runStatus === "error" && runError && (
        <div className="bg-red-50 border-t border-red-200 px-3 py-2 text-[11px] text-red-800 font-mono break-all">
          {runError}
        </div>
      )}
    </div>
  );
}

function StatusBadge({
  status,
  elapsedMs,
  error,
}: {
  status: "idle" | "running" | "ok" | "error";
  elapsedMs: number;
  error: string | null;
}) {
  if (status === "idle") return null;
  const seconds = (elapsedMs / 1000).toFixed(1);
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-0.5 shrink-0">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
        thinking · {seconds}s
      </span>
    );
  }
  if (status === "ok") {
    return (
      <span
        className="inline-flex items-center gap-1.5 text-[11px] text-green-700 bg-green-50 border border-green-200 rounded px-2 py-0.5 shrink-0"
        title={`completed in ${seconds}s`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        ok
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-red-700 bg-red-50 border border-red-200 rounded px-2 py-0.5 shrink-0"
      title={error ?? "run failed"}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
      failed
    </span>
  );
}
