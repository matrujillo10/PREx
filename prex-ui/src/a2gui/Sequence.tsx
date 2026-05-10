import type { SequenceInputT } from "./schemas";
import { A2Card } from "./A2Card";

const W = 560;

export function Sequence({ title, actors, messages, source }: SequenceInputT) {
  const lifelineX = (i: number) => 40 + i * ((W - 80) / Math.max(1, actors.length - 1));
  const headerY = 30;
  const lifelineTop = 50;
  const stepH = 28;
  const totalH = lifelineTop + messages.length * stepH + 30;

  const indexById = new Map(actors.map((a, i) => [a.id, i]));

  return (
    <A2Card componentName="Sequence" title={title ?? "Sequence"} source={source}>
      <svg viewBox={`0 0 ${W} ${totalH}`} width="100%">
        {actors.map((a, i) => (
          <g key={a.id}>
            <rect
              x={lifelineX(i) - 60}
              y={headerY - 14}
              width={120}
              height={26}
              rx={5}
              fill="var(--surface-2)"
              stroke="var(--border)"
            />
            <text
              x={lifelineX(i)}
              y={headerY + 2}
              fontFamily="var(--mono)"
              fontSize={11}
              textAnchor="middle"
              fill="var(--ink-2)"
              dominantBaseline="middle"
            >
              {a.name}
            </text>
            <line
              x1={lifelineX(i)}
              y1={lifelineTop}
              x2={lifelineX(i)}
              y2={totalH - 10}
              stroke="var(--border-2)"
              strokeDasharray="3 3"
            />
          </g>
        ))}
        {messages.map((m, i) => {
          const fromI = indexById.get(m.from);
          const toI = indexById.get(m.to);
          if (fromI === undefined || toI === undefined) return null;
          const y = lifelineTop + i * stepH + 10;
          const sql = m.kind === "sql";
          const reply = m.kind === "reply";
          return (
            <g key={i}>
              <line
                x1={lifelineX(fromI)}
                y1={y}
                x2={lifelineX(toI)}
                y2={y}
                stroke={sql ? "var(--accent)" : "var(--ink-3)"}
                strokeWidth={1.4}
                strokeDasharray={reply ? "5 4" : undefined}
                markerEnd="url(#arr)"
              />
              <text
                x={(lifelineX(fromI) + lifelineX(toI)) / 2}
                y={y - 4}
                fontFamily="var(--mono)"
                fontSize={10.5}
                textAnchor="middle"
                fill={sql ? "var(--accent)" : "var(--ink-3)"}
              >
                {m.label}
              </text>
            </g>
          );
        })}
        <defs>
          <marker id="arr" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" fill="var(--ink-3)" />
          </marker>
        </defs>
      </svg>
    </A2Card>
  );
}
