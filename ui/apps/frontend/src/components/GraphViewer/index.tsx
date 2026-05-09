"use client";

import React, { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  NodeMouseHandler,
  Node,
  Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { CustomNode } from './CustomNode';
import { GraphStyleConfig } from '../../config/graphConfigSchema';

interface GraphViewerProps {
  initialData: { nodes: Node[], edges: Edge[] };
  styleConfig: GraphStyleConfig;
  onNodeClick?: (nodeData: any) => void;
}

export function GraphViewer({ initialData, styleConfig, onNodeClick }: GraphViewerProps) {
  
  const [nodes, setNodes, onNodesChange] = useNodesState(initialData.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialData.edges);

  useEffect(() => {
    setNodes(initialData.nodes);
    setEdges(initialData.edges);
  }, [initialData, setNodes, setEdges]);

  const nodeTypes = useMemo(() => ({ custom: CustomNode }), []);

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      if (onNodeClick) {
        onNodeClick(node.data);
      }
    },
    [onNodeClick]
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background variant={"dots" as any} gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}
