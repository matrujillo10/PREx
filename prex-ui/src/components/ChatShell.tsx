import { useEffect } from "react";
import { useStore } from "../state/store";

interface Props {
  scope: "pr" | `step:${number}`;
}

/**
 * Minimal placeholder for the chat region.
 *
 * Real CopilotKit wiring is registered in `a2gui/registerTools.ts`; the chat
 * UI itself is not yet connected to a backend agent (per plan: "do not build
 * the agent yet"). For v0.1 we render a stub that explains what will live here
 * and previews the diagram chrome by mounting the registered components with
 * fixture data.
 */
export function ChatShell({ scope }: Props) {
  const setScope = useStore((s) => s.setChatScope);
  useEffect(() => {
    setScope(scope);
  }, [scope, setScope]);

  return (
    <div
      style={{
        border: "1px dashed var(--border)",
        borderRadius: 6,
        padding: "14px 16px",
        background: "var(--surface)",
        color: "var(--muted)",
        fontStyle: "italic",
        fontSize: 13,
      }}
    >
      <span>Copilot · {scope === "pr" ? "PR-scope" : `step ${scope.split(":")[1]}`}</span>
      <span style={{ marginLeft: 8 }}>
        — chat will live here. Diagrams will render from registered A2GUI tools
        (Treemap, CouplingMap, ClassDiff, BlastRadius, DataFlowChain, Sequence).
      </span>
    </div>
  );
}
