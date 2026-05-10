import { useEffect, useMemo, useRef, useState } from "react";
import type { Edge, GraphNode, NodeKind } from "../api/types";
import { useStore } from "../state/store";
import styles from "./GraphSurface.module.css";

const W = 1000;
const H = 700;

const COLOR: Record<NodeKind, string> = {
  module: "#cfd2ce",
  file: "#9ecdb8",
  symbol: "#7fb0d8",
  caller_stub: "#cdd6df",
  hunk: "#e7c98c",
  external_ref: "#b04a3a", // accent — risky-looking
};

const SIZE_BY_KIND: Partial<Record<NodeKind, number>> = {
  module: 5,
  file: 7,
  symbol: 9,
  caller_stub: 5,
  hunk: 4,
  external_ref: 8,
};

type Sim = { id: string; x: number; y: number; vx: number; vy: number };

export function GraphSurface() {
  const graph = useStore((s) => s.graph);
  const [showKinds, setShowKinds] = useState<Record<NodeKind, boolean>>({
    module: false,
    file: true,
    symbol: true,
    caller_stub: true,
    hunk: false,
    external_ref: true,
  });
  const [changedOnly, setChangedOnly] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!graph) return { nodes: [] as GraphNode[], edges: [] as Edge[] };
    let nodes = graph.nodes.filter((n) => showKinds[n.kind]);
    if (changedOnly) {
      nodes = nodes.filter((n) => {
        if (n.change_state !== "unchanged") return true;
        // keep caller_stubs — they're always 'unchanged' but interesting
        if (n.kind === "caller_stub") return true;
        return false;
      });
    }
    const ids = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter(
      (e) =>
        ids.has(e.source_id) &&
        ids.has(e.target_id) &&
        // skip 'contains' to reduce noise; we let layout cluster instead
        e.type !== "contains",
    );
    return { nodes, edges };
  }, [graph, showKinds, changedOnly]);

  const positions = useForceLayout(filtered.nodes, filtered.edges);

  if (!graph) {
    return (
      <div className={styles.shell}>
        <div className={styles.canvas}>
          <div style={{ padding: 24, color: "var(--muted)" }}>(no graph loaded)</div>
        </div>
        <div className={styles.detail} />
      </div>
    );
  }

  const selected = filtered.nodes.find((n) => n.id === selectedId);
  const selectedEdges = selected
    ? filtered.edges.filter((e) => e.source_id === selected.id || e.target_id === selected.id)
    : [];

  return (
    <div className={styles.shell}>
      <div className={styles.canvas}>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
          {filtered.edges.map((e, i) => {
            const a = positions.get(e.source_id);
            const b = positions.get(e.target_id);
            if (!a || !b) return null;
            const llm = e.derivation === "llm";
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={llm ? "var(--accent)" : "rgba(60,60,55,0.18)"}
                strokeWidth={llm ? 1.4 : 0.8}
                strokeDasharray={llm ? "4 3" : undefined}
              />
            );
          })}
          {filtered.nodes.map((n) => {
            const p = positions.get(n.id);
            if (!p) return null;
            const r = SIZE_BY_KIND[n.kind] ?? 6;
            const sel = n.id === selectedId;
            const fill = COLOR[n.kind] ?? "#aaa";
            const stroke =
              n.change_state !== "unchanged" ? "var(--accent)" : "var(--ink-3)";
            return (
              <g
                key={n.id}
                transform={`translate(${p.x}, ${p.y})`}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(n.id)}
              >
                <circle
                  r={sel ? r + 3 : r}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={sel ? 2 : n.change_state !== "unchanged" ? 1.5 : 0.5}
                />
                <title>{nodeLabel(n)}</title>
              </g>
            );
          })}
        </svg>
        <div className={styles.toolbar}>
          <h4>Show kinds</h4>
          {(Object.keys(showKinds) as NodeKind[]).map((k) => (
            <label key={k}>
              <input
                type="checkbox"
                checked={showKinds[k]}
                onChange={(e) =>
                  setShowKinds((s) => ({ ...s, [k]: e.target.checked }))
                }
              />
              <i style={{ background: COLOR[k] }} /> {k}
            </label>
          ))}
          <h4 style={{ marginTop: 4 }}>Filter</h4>
          <label>
            <input
              type="checkbox"
              checked={changedOnly}
              onChange={(e) => setChangedOnly(e.target.checked)}
            />
            changed-only (+ caller stubs)
          </label>
        </div>
        <div className={styles.legend}>
          <span>
            <i style={{ background: "var(--surface)", borderColor: "var(--accent)", borderWidth: 2 }} /> changed
          </span>
          <span>
            <i style={{ background: "transparent", borderColor: "var(--accent)", borderStyle: "dashed" }} /> LLM-inferred edge
          </span>
        </div>
      </div>
      <aside className={styles.detail}>
        {!selected && (
          <div className={styles.empty}>
            Click a node to inspect. Drag-free force layout; nodes settle on
            mount. Filters at top-left.
          </div>
        )}
        {selected && (
          <>
            <div>
              <span className={styles.kindChip}>{selected.kind}</span>
              {selected.change_state !== "unchanged" && (
                <span
                  className={styles.kindChip}
                  style={{ marginLeft: 6, background: "var(--accent-soft)", color: "var(--accent)", borderColor: "var(--accent)" }}
                >
                  {selected.change_state}
                </span>
              )}
            </div>
            <h3>{nodeLabel(selected)}</h3>
            <div className={styles.qn}>{selected.id}</div>
            <div className={styles.row}>
              <span className={styles.rowK}>derivation</span>
              <span>{selected.derivation}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowK}>score</span>
              <span>{selected.score?.toFixed(2)}</span>
            </div>
            <h4 style={{ margin: 0, fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Edges ({selectedEdges.length})
            </h4>
            <div className={styles.edges}>
              {selectedEdges.length === 0 && (
                <div className={styles.empty}>(none in current filter)</div>
              )}
              {selectedEdges.map((e, i) => {
                const otherId = e.source_id === selected.id ? e.target_id : e.source_id;
                const other = filtered.nodes.find((n) => n.id === otherId);
                const dir = e.source_id === selected.id ? "→" : "←";
                return (
                  <div
                    key={i}
                    className={`${styles.edge} ${e.derivation === "llm" ? styles.edgeLlm : ""}`}
                    onClick={() => setSelectedId(otherId)}
                    style={{ cursor: "pointer" }}
                  >
                    {e.type} {dir} {other ? nodeLabel(other) : otherId}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

function nodeLabel(n: GraphNode): string {
  if (n.kind === "symbol" || n.kind === "caller_stub") return n.qualified_name;
  if (n.kind === "file") return n.path;
  if (n.kind === "module") return n.name;
  if (n.kind === "external_ref") return `${n.ref_kind}:${n.name}`;
  if (n.kind === "hunk") return `${n.id}`;
  return (n as { id: string }).id;
}

/** Simple spring-based force layout. Hand-rolled to avoid d3-force dep. */
function useForceLayout(nodes: GraphNode[], edges: Edge[]): Map<string, Sim> {
  const [positions, setPositions] = useState<Map<string, Sim>>(new Map());
  const nodeKey = nodes.map((n) => n.id).join("|");
  const edgeKey = edges.map((e) => `${e.source_id}>${e.target_id}`).join("|");
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    if (animRef.current !== null) cancelAnimationFrame(animRef.current);
    if (nodes.length === 0) {
      setPositions(new Map());
      return;
    }
    const sims: Map<string, Sim> = new Map();
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      const r = 200;
      sims.set(n.id, {
        id: n.id,
        x: W / 2 + Math.cos(angle) * r,
        y: H / 2 + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
      });
    });
    const adjacency = new Map<string, string[]>();
    edges.forEach((e) => {
      adjacency.set(e.source_id, [...(adjacency.get(e.source_id) ?? []), e.target_id]);
      adjacency.set(e.target_id, [...(adjacency.get(e.target_id) ?? []), e.source_id]);
    });

    const REPULSION = 1400;
    const SPRING = 0.02;
    const SPRING_LEN = 90;
    const DAMP = 0.78;
    const CENTER = 0.005;
    const N_STEPS = 220;

    let stepCount = 0;
    const tick = () => {
      const arr = Array.from(sims.values());
      for (const a of arr) {
        let fx = 0;
        let fy = 0;
        // repulsion
        for (const b of arr) {
          if (a === b) continue;
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy + 0.01;
          const f = REPULSION / d2;
          const inv = 1 / Math.sqrt(d2);
          fx += dx * inv * f;
          fy += dy * inv * f;
        }
        // spring along edges
        const neigh = adjacency.get(a.id) ?? [];
        for (const nid of neigh) {
          const b = sims.get(nid);
          if (!b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = SPRING * (d - SPRING_LEN);
          fx += (dx / d) * f;
          fy += (dy / d) * f;
        }
        // pull to center
        fx += (W / 2 - a.x) * CENTER;
        fy += (H / 2 - a.y) * CENTER;
        a.vx = (a.vx + fx) * DAMP;
        a.vy = (a.vy + fy) * DAMP;
      }
      for (const a of arr) {
        a.x += a.vx;
        a.y += a.vy;
        // hard bounds
        a.x = Math.max(20, Math.min(W - 20, a.x));
        a.y = Math.max(20, Math.min(H - 20, a.y));
      }
      stepCount++;
      setPositions(new Map(sims));
      if (stepCount < N_STEPS) {
        animRef.current = requestAnimationFrame(tick);
      } else {
        animRef.current = null;
      }
    };
    animRef.current = requestAnimationFrame(tick);
    return () => {
      if (animRef.current !== null) cancelAnimationFrame(animRef.current);
    };
  }, [nodeKey, edgeKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return positions;
}
