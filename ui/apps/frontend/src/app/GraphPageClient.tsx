"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import dagre from "dagre";
import { GraphViewer } from "../components/GraphViewer";
import { AgentChatBubble } from "../components/AgentChatBubble";
import {
  GraphStyleConfig,
  GraphPromptsConfig,
  PRImpactGraph,
  GraphNodePayload
} from "../config/graphConfigSchema";

interface GraphPageClientProps {
  initialStyleConfig: GraphStyleConfig;
  initialPromptsConfig: GraphPromptsConfig;
}

export function GraphPageClient({ initialStyleConfig, initialPromptsConfig }: GraphPageClientProps) {
  const [graphData, setGraphData] = useState<PRImpactGraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8080/graph")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch graph data");
        return res.json();
      })
      .then((data) => setGraphData(data as PRImpactGraph))
      .catch((err) => setError(err.message));
  }, []);

  const reactFlowLayout = useMemo(() => {
    if (!graphData) return null;

    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: 'LR', nodesep: 50, ranksep: 200 });
    g.setDefaultEdgeLabel(() => ({}));

    // Add nodes to dagre
    graphData.nodes.forEach(node => {
      // Approximation of node size, could be dynamic
      g.setNode(node.id, { width: 180, height: 80 }); 
    });

    // Add edges
    graphData.edges.forEach(edge => {
      g.setEdge(edge.source_id, edge.target_id);
    });

    // Compute layout
    dagre.layout(g);

    // Map back to ReactFlow nodes
    const rfNodes = graphData.nodes.map(node => {
      const nodeWithPosition = g.node(node.id);
      const style = initialStyleConfig.changeStates[node.change_state] || initialStyleConfig.changeStates['unchanged'];
      const kindStyle = initialStyleConfig.kinds[node.kind] || initialStyleConfig.kinds['module'];

      return {
        id: node.id,
        type: 'custom',
        position: {
          x: nodeWithPosition.x - 90, // center offset
          y: nodeWithPosition.y - 40,
        },
        data: {
          payload: node,
          _style: style,
          _kindStyle: kindStyle
        }
      };
    });

    const rfEdges = graphData.edges.map(edge => {
      const isAdded = edge.change_state === "added";
      const isRemoved = edge.change_state === "removed";
      const isModified = edge.change_state === "modified";
      
      const strokeStr = isRemoved ? "#ef4444" : isAdded ? "#22c55e" : isModified ? "#eab308" : "#9ca3af";

      return {
        id: edge.id,
        source: edge.source_id,
        target: edge.target_id,
        animated: edge.change_state !== "unchanged",
        style: { stroke: strokeStr, strokeWidth: 2 }
      };
    });

    return { nodes: rfNodes, edges: rfEdges };
  }, [graphData, initialStyleConfig]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500 font-bold p-10 text-center">
        Error loading graph: {error}
        <br/><br/>
        Did you run the Bun server? `cd apps/graph-server && bun run start -- --file mock-graph.json`
      </div>
    );
  }

  if (!reactFlowLayout) {
    return <div className="flex items-center justify-center h-full">Loading Graph Topology...</div>;
  }

  return (
    <div className="w-full h-full relative">
      <GraphViewer
        initialData={reactFlowLayout as any}
        styleConfig={initialStyleConfig}
        onNodeClick={(nodeData) => {
          setSelectedNode(nodeData.payload);
        }}
      />

      {selectedNode && graphData && (
        <AgentChatBubble
          selectedNode={selectedNode}
          graph={graphData}
          promptsConfig={initialPromptsConfig}
          analysis="impact_summary"
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
