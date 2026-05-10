import type { PlanCardInputT } from "./schemas";
import { A2Card } from "./A2Card";

const RISKY = new Set([
  "auth_or_authz_touched",
  "secret_like_string",
  "removes_assertion",
  "broad_except",
  "raises_swallowed",
]);

export function PlanCard({ overview, steps, source }: PlanCardInputT) {
  return (
    <A2Card componentName="ReviewPlan" title="Suggested reading plan" source={source}>
      {overview && (
        <div
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border-2)",
            borderRadius: 6,
            padding: "10px 12px",
            fontStyle: "italic",
            color: "var(--ink-2)",
            marginBottom: 10,
            fontSize: 13,
          }}
        >
          {overview}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {steps.map((s) => (
          <a
            key={s.rank}
            href={`#/step/${s.rank}`}
            style={{
              border: "1px solid var(--border-2)",
              borderRadius: 6,
              padding: "10px 12px",
              background: "var(--surface)",
              display: "flex",
              flexDirection: "column",
              gap: 6,
              textDecoration: "none",
              color: "var(--ink)",
            }}
          >
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span
                style={{
                  background: "var(--ink)",
                  color: "var(--surface)",
                  fontFamily: "var(--mono)",
                  fontSize: 11,
                  fontWeight: 600,
                  width: 22,
                  height: 22,
                  borderRadius: 4,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {s.rank}
              </span>
              <span style={{ flex: 1, fontWeight: 500, fontSize: 13.5 }}>
                {s.title ?? `Step ${s.rank}`}
              </span>
              {s.estimated_minutes !== undefined && (
                <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--muted)" }}>
                  {s.estimated_minutes}m
                </span>
              )}
            </div>
            {s.what && (
              <Row label="WHAT" text={s.what} />
            )}
            {s.why && <Row label="WHY" text={s.why} />}
            {s.impact && <Row label="IMPACT" text={s.impact} />}
            {s.risk_signals.length > 0 && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {s.risk_signals.map((sig) => (
                  <span
                    key={sig}
                    style={{
                      display: "inline-block",
                      fontFamily: "var(--mono)",
                      fontSize: 10,
                      padding: "2px 7px",
                      borderRadius: 3,
                      background: RISKY.has(sig) ? "var(--accent-soft)" : "var(--surface-2)",
                      color: RISKY.has(sig) ? "var(--accent)" : "var(--muted)",
                      border: "1px solid",
                      borderColor: RISKY.has(sig) ? "var(--accent-soft)" : "var(--border-2)",
                    }}
                  >
                    {sig}
                  </span>
                ))}
              </div>
            )}
          </a>
        ))}
      </div>
    </A2Card>
  );
}

function Row({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <span
        style={{
          display: "block",
          fontFamily: "var(--mono)",
          fontSize: 9.5,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "var(--muted)",
          marginBottom: 2,
        }}
      >
        {label}
      </span>
      <span style={{ fontSize: 12.5, lineHeight: 1.45, color: "var(--ink-2)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
        {text}
      </span>
    </div>
  );
}
