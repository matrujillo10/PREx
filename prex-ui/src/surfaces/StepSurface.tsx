import { lazy, Suspense, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Edge, FileNode, GraphNode, ReviewStep, SymbolNode } from "../api/types";
import { CitationLink } from "../components/CitationLink";
import { useStore } from "../state/store";
import styles from "./StepSurface.module.css";

const ChatShell = lazy(() =>
  import("../components/ChatShell").then((m) => ({ default: m.ChatShell })),
);

export function StepSurface() {
  const params = useParams<{ rank: string }>();
  const navigate = useNavigate();
  const brief = useStore((s) => s.brief)!;
  const graph = useStore((s) => s.graph);
  const select = useStore((s) => s.selectStep);
  const selectedRank = parseInt(params.rank ?? "1", 10);
  const step = brief.plan.steps.find((s) => s.rank === selectedRank);

  useEffect(() => {
    if (step) select(step.rank);
  }, [step, select]);

  if (!step) {
    return (
      <div className={styles.focus}>
        <button className={styles.back} onClick={() => navigate("/")}>
          ‹ back to plan
        </button>
        <div>Step not found.</div>
      </div>
    );
  }

  const target = graph?.nodes.find((n) => n.id === step.target);
  const callers = useCallers(graph?.nodes ?? [], graph?.edges ?? [], step.target);

  return (
    <div className={styles.body}>
      <aside className={styles.rail}>
        <div className={styles.railH}>Plan rail</div>
        {brief.plan.steps.map((s) => (
          <button
            key={s.rank}
            className={`${styles.railStep} ${
              s.rank === step.rank ? styles.railStepActive : ""
            }`}
            onClick={() => navigate(`/step/${s.rank}`)}
          >
            <span className={styles.rank}>{s.rank}</span>
            <span className={styles.title}>
              {s.title ?? `step ${s.rank}`}
            </span>
            <span className={styles.minutes}>{s.estimated_minutes}m</span>
          </button>
        ))}
      </aside>
      <main className={styles.focus}>
        <button className={styles.back} onClick={() => navigate("/")}>
          ‹ back to plan
        </button>
        <div className={styles.head}>
          <span className={styles.headRank}>{step.rank}</span>
          <span className={styles.headTitle}>
            {step.title ?? <em>(LLM title missing)</em>}
          </span>
          <span className={styles.headMinutes}>~{step.estimated_minutes}m</span>
        </div>
        <div className={styles.qn}>
          <span className={styles.info}>{step.target.split(":")[0]}:</span>
          <span>{step.target.split(":").slice(1).join(":")}</span>
        </div>
        <div className={styles.wwI}>
          <Block label="WHAT" text={step.what} cites={step.cites} source={`step ${step.rank} / what`} />
          <Block label="WHY" text={step.why} cites={step.cites} source={`step ${step.rank} / why`} />
          <Block
            label="IMPACT"
            text={step.impact}
            cites={step.cites}
            source={`step ${step.rank} / impact`}
            impact
          />
        </div>
        <Suspense fallback={<div style={{ color: "var(--muted)", fontStyle: "italic" }}>Loading Copilot…</div>}>
          <ChatShell scope={`step:${step.rank}`} />
        </Suspense>
        <div className={styles.nav}>
          {step.rank > 1 && (
            <button onClick={() => navigate(`/step/${step.rank - 1}`)}>
              ‹ prev
            </button>
          )}
          {step.rank < brief.plan.steps.length && (
            <button onClick={() => navigate(`/step/${step.rank + 1}`)}>
              next ›
            </button>
          )}
          <span className={styles.minutes} style={{ marginLeft: "auto" }}>
            step {step.rank} / {brief.plan.steps.length}
          </span>
        </div>
      </main>
      <aside className={styles.rightRail}>
        <div className={styles.card}>
          <div className={styles.cardH}>1-hop callers</div>
          {callers.length === 0 && (
            <div className={styles.note}>No resolved callers in graph.</div>
          )}
          {callers.map((c, i) => (
            <div key={i} className={styles.callerRow}>
              <span className={styles.qn}>{c.qn}</span>
              <span className={styles.note}>{c.fileLine}</span>
              <span
                className={`${styles.derivChip} ${
                  c.llm ? styles.derivChipLlm : ""
                }`}
              >
                {c.derivation}
                {c.llm ? " · ⚠ inferred" : ""}
              </span>
            </div>
          ))}
        </div>
        <div className={styles.card}>
          <div className={styles.cardH}>Related targets</div>
          {step.related_targets.length === 0 && (
            <div className={styles.note}>None.</div>
          )}
          {step.related_targets.map((rt, i) => (
            <div key={i} className={styles.callerRow}>
              <span className={styles.qn}>{rt}</span>
            </div>
          ))}
        </div>
        <div className={styles.note}>
          AI-inferred edges always wear the chip — never silently mixed with deterministic ones.
        </div>
      </aside>
    </div>
  );
}

function Block({
  label,
  text,
  cites,
  source,
  impact,
}: {
  label: string;
  text: string | null | undefined;
  cites: ReviewStep["cites"];
  source: string;
  impact?: boolean;
}) {
  return (
    <div className={`${styles.block} ${impact ? styles.impactBlock : ""}`}>
      <span className={styles.blockLabel}>{label}</span>
      <div
        className={styles.blockText}
        dangerouslySetInnerHTML={{ __html: render(text) }}
      />
      <span className={styles.cite}>
        <CitationLink cites={cites} source={source} />
      </span>
    </div>
  );
}

function render(text: string | null | undefined): string {
  if (!text) {
    return `<em style="color:var(--muted)">(LLM prose not generated)</em>`;
  }
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\b(\d+)\b/g, "<b>$1</b>");
}

function useCallers(nodes: GraphNode[], edges: Edge[], targetId: string) {
  return useMemo(() => {
    const node = nodes.find((n) => n.id === targetId);
    if (!node) return [];
    const fileById = new Map<string, FileNode>();
    for (const n of nodes) if (n.kind === "file") fileById.set(n.id, n);
    const out: { qn: string; fileLine: string; derivation: string; llm: boolean }[] = [];
    for (const e of edges) {
      if (e.target_id !== targetId) continue;
      if (!["calls", "references", "imports"].includes(e.type)) continue;
      const src = nodes.find((n) => n.id === e.source_id);
      if (!src) continue;
      const file =
        src.kind === "symbol" || src.kind === "caller_stub"
          ? fileById.get((src as SymbolNode).file_id)
          : src.kind === "file"
            ? src
            : undefined;
      const qn =
        src.kind === "symbol" || src.kind === "caller_stub"
          ? (src as SymbolNode).qualified_name
          : src.kind === "file"
            ? src.path
            : src.id;
      const cite = e.cites?.[0];
      const fileLine = cite?.kind === "file_line" ? cite.ref : file?.path ?? "";
      out.push({
        qn,
        fileLine,
        derivation: e.derivation,
        llm: e.derivation === "llm",
      });
    }
    return out.slice(0, 6);
  }, [nodes, edges, targetId]);
}
