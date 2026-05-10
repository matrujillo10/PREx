import type { SequenceInputT } from "./schemas";
import { A2Card } from "./A2Card";

const ACTOR_W = 150;
const ACTOR_H = 30;
const COL_GAP = 32;
const MARGIN_X = 24;
const HEADER_TOP = 14;
const LIFELINE_TOP_PAD = 22;
const STEP_H = 36;
const BOTTOM_PAD = 24;
const MAX_ACTOR_LABEL = 18;
const MAX_MSG_LABEL = 36;

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function Sequence({ title, actors, messages, source }: SequenceInputT) {
  const cols = actors.length;
  const width = MARGIN_X * 2 + cols * ACTOR_W + (cols - 1) * COL_GAP;
  const lifelineY = HEADER_TOP + ACTOR_H + LIFELINE_TOP_PAD;
  const totalH = lifelineY + messages.length * STEP_H + BOTTOM_PAD;

  const lifelineX = (i: number) =>
    MARGIN_X + ACTOR_W / 2 + i * (ACTOR_W + COL_GAP);

  const indexById = new Map(actors.map((a, i) => [a.id, i]));

  return (
    <A2Card componentName="Sequence" title={title ?? "Sequence"} source={source}>
      <svg
        viewBox={`0 0 ${width} ${totalH}`}
        width="100%"
        preserveAspectRatio="xMidYMin meet"
      >
        {actors.map((a, i) => (
          <g key={a.id}>
            <rect
              x={lifelineX(i) - ACTOR_W / 2}
              y={HEADER_TOP}
              width={ACTOR_W}
              height={ACTOR_H}
              rx={6}
              fill="var(--surface-2)"
              stroke="var(--border)"
            />
            <text
              x={lifelineX(i)}
              y={HEADER_TOP + ACTOR_H / 2}
              fontFamily="var(--mono)"
              fontSize={11}
              textAnchor="middle"
              fill="var(--ink-2)"
              dominantBaseline="middle"
            >
              <title>{a.name}</title>
              {truncate(a.name, MAX_ACTOR_LABEL)}
            </text>
            <line
              x1={lifelineX(i)}
              y1={HEADER_TOP + ACTOR_H}
              x2={lifelineX(i)}
              y2={totalH - 8}
              stroke="var(--border-2)"
              strokeDasharray="3 3"
            />
          </g>
        ))}
        {messages.map((m, i) => {
          const fromI = indexById.get(m.from);
          const toI = indexById.get(m.to);
          if (fromI === undefined || toI === undefined) return null;
          const y = lifelineY + i * STEP_H + STEP_H / 2;
          const sql = m.kind === "sql";
          const reply = m.kind === "reply";
          const fromX = lifelineX(fromI);
          const toX = lifelineX(toI);
          // Self-message: draw a small loop instead of a line.
          if (fromI === toI) {
            const r = 14;
            const x = fromX;
            return (
              <g key={i}>
                <path
                  d={`M ${x} ${y - r / 2} q ${r} 0 ${r} ${r} q 0 ${r / 2} ${-r} ${r / 2}`}
                  fill="none"
                  stroke={sql ? "var(--accent)" : "var(--ink-3)"}
                  strokeWidth={1.4}
                  strokeDasharray={reply ? "5 4" : undefined}
                  markerEnd="url(#sa)"
                />
                <text
                  x={x + r * 1.6}
                  y={y - 2}
                  fontFamily="var(--mono)"
                  fontSize={10}
                  fill={sql ? "var(--accent)" : "var(--ink-3)"}
                  textAnchor="start"
                >
                  {truncate(m.label, MAX_MSG_LABEL)}
                </text>
              </g>
            );
          }
          const midX = (fromX + toX) / 2;
          return (
            <g key={i}>
              <line
                x1={fromX}
                y1={y}
                x2={toX}
                y2={y}
                stroke={sql ? "var(--accent)" : "var(--ink-3)"}
                strokeWidth={1.4}
                strokeDasharray={reply ? "5 4" : undefined}
                markerEnd="url(#sa)"
              />
              <text
                x={midX}
                y={y - 5}
                fontFamily="var(--mono)"
                fontSize={10}
                textAnchor="middle"
                fill={sql ? "var(--accent)" : "var(--ink-3)"}
                paintOrder="stroke"
                stroke="var(--surface)"
                strokeWidth={3}
                strokeLinejoin="round"
              >
                {truncate(m.label, MAX_MSG_LABEL)}
              </text>
            </g>
          );
        })}
        <defs>
          <marker
            id="sa"
            viewBox="0 0 6 6"
            refX="6"
            refY="3"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 z" fill="var(--ink-3)" />
          </marker>
        </defs>
      </svg>
    </A2Card>
  );
}
