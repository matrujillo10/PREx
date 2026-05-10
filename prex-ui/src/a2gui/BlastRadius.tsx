import type { BlastRadiusInputT } from "./schemas";
import { A2Card } from "./A2Card";

const W = 560;
const H = 240;

export function BlastRadius({ title, target, neighborhood, edges, source }: BlastRadiusInputT) {
  const cx = W / 2;
  const cy = H / 2;
  const r = Math.min(W, H) / 2 - 40;
  const positions = new Map<string, { x: number; y: number }>();
  positions.set(target.id, { x: cx, y: cy });
  neighborhood.forEach((n, i) => {
    const angle = (i / Math.max(1, neighborhood.length)) * 2 * Math.PI - Math.PI / 2;
    positions.set(n.id, {
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
    });
  });

  return (
    <A2Card componentName="BlastRadius" title={title ?? `Blast radius of ${target.label}`} source={source}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%">
        {edges.map((e, i) => {
          const a = positions.get(e.from);
          const b = positions.get(e.to);
          if (!a || !b) return null;
          const llm = e.derivation === "llm";
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={llm ? "var(--accent)" : "var(--ink-3)"}
              strokeWidth={1.4}
              strokeDasharray={llm ? "4 4" : undefined}
            />
          );
        })}
        <g transform={`translate(${cx}, ${cy})`}>
          <rect
            x={-90}
            y={-22}
            width={180}
            height={44}
            rx={8}
            fill="var(--accent-soft)"
            stroke="var(--accent)"
            strokeWidth={1.5}
          />
          <text
            fontFamily="var(--mono)"
            fontSize={12}
            fill="var(--accent)"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {target.label.length > 28 ? target.label.slice(0, 27) + "…" : target.label}
          </text>
        </g>
        {neighborhood.map((n) => {
          const p = positions.get(n.id);
          if (!p) return null;
          return (
            <g key={n.id} transform={`translate(${p.x}, ${p.y})`}>
              <rect
                x={-70}
                y={-14}
                width={140}
                height={28}
                rx={5}
                fill={n.inferred ? "var(--surface)" : "var(--surface-2)"}
                stroke={n.inferred ? "var(--accent)" : "var(--border)"}
                strokeDasharray={n.inferred ? "4 4" : undefined}
              />
              <text
                fontFamily="var(--mono)"
                fontSize={10.5}
                fill={n.inferred ? "var(--accent)" : "var(--ink-3)"}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label}
              </text>
              {n.inferred && (
                <text
                  y={24}
                  fontFamily="var(--mono)"
                  fontSize={9}
                  fill="var(--accent)"
                  textAnchor="middle"
                >
                  ⚠ inferred (LLM)
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </A2Card>
  );
}
