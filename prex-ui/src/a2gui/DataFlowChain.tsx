import type { DataFlowChainInputT } from "./schemas";
import { A2Card } from "./A2Card";

export function DataFlowChain({ title, cards, source }: DataFlowChainInputT) {
  return (
    <A2Card componentName="DataFlowChain" title={title ?? "Data flow"} source={source}>
      <div
        style={{
          display: "flex",
          gap: 6,
          alignItems: "stretch",
          flexWrap: "nowrap",
          overflowX: "auto",
        }}
      >
        {cards.map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center" }}>
            <div
              style={{
                border: "1px solid var(--border-2)",
                borderRadius: 6,
                background: "var(--surface-2)",
                padding: "10px 14px",
                minWidth: 130,
                fontFamily: "var(--mono)",
                fontSize: 12,
                color: "var(--ink-2)",
              }}
            >
              <div style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase" }}>
                {c.role}
              </div>
              <div style={{ fontWeight: 600, marginTop: 4 }}>{c.label}</div>
              {c.fileLoc && (
                <div style={{ fontSize: 10, color: "var(--muted)" }}>{c.fileLoc}</div>
              )}
            </div>
            {i < cards.length - 1 && (
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 14,
                  color: "var(--muted)",
                  margin: "0 6px",
                }}
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>
    </A2Card>
  );
}
