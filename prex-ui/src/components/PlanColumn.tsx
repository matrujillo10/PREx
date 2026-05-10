import { useNavigate } from "react-router-dom";
import type { ReviewStep } from "../api/types";
import { useStore } from "../state/store";
import { CitationLink } from "./CitationLink";
import styles from "./PlanColumn.module.css";

const RISKY_SIGNALS = new Set([
  "auth_or_authz_touched",
  "secret_like_string",
  "removes_assertion",
  "broad_except",
  "raises_swallowed",
]);

export function PlanColumn() {
  const brief = useStore((s) => s.brief)!;
  const selected = useStore((s) => s.selectedStep);
  const select = useStore((s) => s.selectStep);
  const totalMinutes = brief.plan.steps.reduce(
    (acc, s) => acc + (s.estimated_minutes || 0),
    0,
  );

  return (
    <aside className={styles.col}>
      <div className={styles.colH}>
        <span className={styles.ttl}>Suggested reading plan</span>
        <span className={styles.meta}>
          {brief.plan.steps.length} · ~{totalMinutes}m total
        </span>
      </div>
      {brief.plan.overview ? (
        <div className={styles.overview}>
          {brief.plan.overview}
          <CitationLink cites={brief.plan.cites} source="plan.overview" />
        </div>
      ) : (
        <div className={`${styles.overview} ${styles.empty}`}>
          (LLM overview not generated — falling back to per-step reading order)
        </div>
      )}
      <div className={styles.list}>
        {brief.plan.steps.map((step) => (
          <StepCard
            key={step.rank}
            step={step}
            selected={step.rank === selected}
            onSelect={() => {
              select(step.rank);
            }}
          />
        ))}
      </div>
    </aside>
  );
}

function StepCard({
  step,
  selected,
  onSelect,
}: {
  step: ReviewStep;
  selected: boolean;
  onSelect: () => void;
}) {
  const empty = !step.what && !step.why && !step.impact;
  const navigate = useNavigate();
  return (
    <button
      className={`${styles.step} ${selected ? styles.stepSelected : ""} ${
        empty ? styles.stepEmpty : ""
      }`}
      onClick={() => {
        onSelect();
        navigate(`/step/${step.rank}`);
      }}
    >
      <div className={styles.top}>
        <span className={styles.rank}>{step.rank}</span>
        <span className={styles.ttl}>
          {step.title ?? <em>(LLM title missing)</em>}
        </span>
        <span className={styles.minutes}>{step.estimated_minutes}m</span>
      </div>
      {empty ? (
        <div className={styles.body}>
          <span className={styles.empty}>
            (LLM prose not generated — falling back to AST summary).{" "}
            target: <code>{shortTarget(step.target)}</code>
          </span>
        </div>
      ) : (
        <div className={styles.body}>
          <Row label="WHAT" text={step.what} />
          <Row label="WHY" text={step.why} />
          <Row label="IMPACT" text={step.impact} highlight={step.rank === 1} />
        </div>
      )}
      {step.risk_signals.length > 0 && (
        <div className={styles.signals}>
          {step.risk_signals.map((s) => (
            <span
              key={s}
              className={`${styles.sigChip} ${
                RISKY_SIGNALS.has(s) ? styles.sigChipRisk : ""
              }`}
            >
              {s}
            </span>
          ))}
        </div>
      )}
      <CitationLink cites={step.cites} source={`plan.steps[${step.rank}]`} />
    </button>
  );
}

function Row({
  label,
  text,
  highlight,
}: {
  label: string;
  text: string | null | undefined;
  highlight?: boolean;
}) {
  if (!text) return null;
  return (
    <div className={highlight ? styles.impactHi : ""}>
      <span className={styles.label}>{label}</span>
      <span dangerouslySetInnerHTML={{ __html: maybeHighlight(text, label) }} />
    </div>
  );
}

function maybeHighlight(text: string, label: string): string {
  if (label !== "IMPACT") return escapeHtml(text);
  // Bold-quote: numbers like '5' or '3' get terracotta highlight via <b>.
  // Keep it simple — wrap any backticked code as well.
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\b(\d+)\b/g, "<b>$1</b>");
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function shortTarget(target: string): string {
  if (target.startsWith("hunk:")) return target.slice("hunk:".length);
  if (target.startsWith("symbol:")) return target.slice("symbol:".length).split(".").slice(-3).join(".");
  return target;
}
