import type { CouplingMapInputT } from "./schemas";
import { A2Card } from "./A2Card";

const NODE_W = 200;
const NODE_H = 36;
const COL_GAP = 28;
const ROW_GAP = 64;
const MARGIN = 28;
const MAX_LABEL = 26;

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

interface Pos {
  x: number;
  y: number;
}

function layout(nodeCount: number): {
  positions: (i: number) => Pos;
  width: number;
  height: number;
} {
  if (nodeCount <= 1) {
    return {
      positions: () => ({ x: MARGIN + NODE_W / 2, y: MARGIN + NODE_H / 2 }),
      width: NODE_W + MARGIN * 2,
      height: NODE_H + MARGIN * 2,
    };
  }
  // For 2-4 nodes use a single row.
  if (nodeCount <= 4) {
    const cols = nodeCount;
    const w = MARGIN * 2 + cols * NODE_W + (cols - 1) * COL_GAP;
    const h = MARGIN * 2 + NODE_H + ROW_GAP / 2;
    return {
      positions: (i) => ({
        x: MARGIN + NODE_W / 2 + i * (NODE_W + COL_GAP),
        y: MARGIN + NODE_H / 2,
      }),
      width: w,
      height: h,
    };
  }
  // Otherwise grid with 3 columns.
  const cols = 3;
  const rows = Math.ceil(nodeCount / cols);
  const w = MARGIN * 2 + cols * NODE_W + (cols - 1) * COL_GAP;
  const h = MARGIN * 2 + rows * NODE_H + (rows - 1) * ROW_GAP;
  return {
    positions: (i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      return {
        x: MARGIN + NODE_W / 2 + col * (NODE_W + COL_GAP),
        y: MARGIN + NODE_H / 2 + row * (NODE_H + ROW_GAP),
      };
    },
    width: w,
    height: h,
  };
}

export function CouplingMap({ title, nodes, edges, source }: CouplingMapInputT) {
  const layoutInfo = layout(nodes.length);
  const positions = new Map<string, Pos>();
  nodes.forEach((n, i) => positions.set(n.id, layoutInfo.positions(i)));

  return (
    <A2Card componentName="CouplingMap" title={title ?? "Coupling map"} source={source}>
      <svg
        viewBox={`0 0 ${layoutInfo.width} ${layoutInfo.height}`}
        width="100%"
        preserveAspectRatio="xMidYMid meet"
        style={{ background: "var(--surface)" }}
      >
        {/* edges first so nodes paint over them */}
        {edges.map((e, i) => {
          const a = positions.get(e.from);
          const b = positions.get(e.to);
          if (!a || !b) return null;
          const llm = e.derivation === "llm";
          // Compute trimmed endpoints so edges meet rect borders, not centers.
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const ux = dx / len;
          const uy = dy / len;
          const ax = a.x + ux * (NODE_W / 2 + 2);
          const ay = a.y + uy * (NODE_H / 2 + 2);
          const bx = b.x - ux * (NODE_W / 2 + 2);
          const by = b.y - uy * (NODE_H / 2 + 2);
          return (
            <g key={i}>
              <line
                x1={ax}
                y1={ay}
                x2={bx}
                y2={by}
                stroke={llm ? "var(--accent)" : "var(--ink-3)"}
                strokeWidth={1.4}
                strokeDasharray={llm ? "4 4" : undefined}
              />
              {e.label && (
                <text
                  x={(ax + bx) / 2}
                  y={(ay + by) / 2 - 4}
                  fontFamily="var(--mono)"
                  fontSize={9.5}
                  fill={llm ? "var(--accent)" : "var(--muted)"}
                  textAnchor="middle"
                  paintOrder="stroke"
                  stroke="var(--surface)"
                  strokeWidth={3}
                  strokeLinejoin="round"
                >
                  {truncate(e.label, 22)}
                </text>
              )}
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = positions.get(n.id)!;
          return (
            <g key={n.id} transform={`translate(${p.x}, ${p.y})`}>
              <rect
                x={-NODE_W / 2}
                y={-NODE_H / 2}
                width={NODE_W}
                height={NODE_H}
                rx={6}
                fill={n.sensitive ? "var(--accent-soft)" : "var(--surface-2)"}
                stroke={n.sensitive ? "var(--accent)" : "var(--border)"}
              />
              <text
                fontFamily="var(--mono)"
                fontSize={10.5}
                fill={n.sensitive ? "var(--accent)" : "var(--ink-2)"}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                <title>{n.label}</title>
                {truncate(n.label, MAX_LABEL)}
              </text>
            </g>
          );
        })}
      </svg>
    </A2Card>
  );
}
