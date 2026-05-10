import type { CouplingMapInputT } from "./schemas";
import { A2Card } from "./A2Card";

const W = 560;
const H = 220;

export function CouplingMap({ title, nodes, edges, source }: CouplingMapInputT) {
  // Lay nodes out on an ellipse; deterministic.
  const cx = W / 2;
  const cy = H / 2;
  const rx = W / 2 - 80;
  const ry = H / 2 - 50;
  const positions = new Map<string, { x: number; y: number }>();
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2;
    positions.set(n.id, {
      x: cx + Math.cos(angle) * rx,
      y: cy + Math.sin(angle) * ry,
    });
  });

  return (
    <A2Card componentName="CouplingMap" title={title ?? "Hidden coupling"} source={source}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ background: "var(--surface)" }}
      >
        {edges.map((e, i) => {
          const a = positions.get(e.from);
          const b = positions.get(e.to);
          if (!a || !b) return null;
          const llm = e.derivation === "llm";
          return (
            <g key={i}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={llm ? "var(--accent)" : "var(--ink-3)"}
                strokeWidth={1.5}
                strokeDasharray={llm ? "4 4" : undefined}
              />
              {e.label && (
                <text
                  x={(a.x + b.x) / 2}
                  y={(a.y + b.y) / 2 - 6}
                  fontFamily="var(--mono)"
                  fontSize={10}
                  fill={llm ? "var(--accent)" : "var(--muted)"}
                  textAnchor="middle"
                >
                  {e.label}
                </text>
              )}
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = positions.get(n.id);
          if (!p) return null;
          return (
            <g key={n.id} transform={`translate(${p.x}, ${p.y})`}>
              <rect
                x={-70}
                y={-16}
                width={140}
                height={32}
                rx={6}
                fill={n.sensitive ? "var(--accent-soft)" : "var(--surface-2)"}
                stroke={n.sensitive ? "var(--accent)" : "var(--border)"}
              />
              <text
                fontFamily="var(--mono)"
                fontSize={11}
                fill={n.sensitive ? "var(--accent)" : "var(--ink-2)"}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label}
              </text>
            </g>
          );
        })}
      </svg>
    </A2Card>
  );
}
