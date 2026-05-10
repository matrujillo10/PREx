import type { ReviewBriefCardInputT } from "./schemas";
import { A2Card } from "./A2Card";

export function ReviewBriefCard({
  pr_type,
  pr_type_confidence,
  risk_tier,
  risk_score,
  blast_radius,
  novelty,
  headline,
  advisory_flags,
  source,
}: ReviewBriefCardInputT) {
  return (
    <A2Card componentName="ReviewBrief" title="PR briefing" source={source}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: "var(--accent-soft)",
            color: "var(--accent)",
            fontFamily: "var(--mono)",
            fontSize: 11,
            fontWeight: 600,
            padding: "4px 10px",
            borderRadius: 100,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              background: "var(--accent)",
              borderRadius: "50%",
              display: "inline-block",
            }}
          />
          RISK · {risk_tier}
        </span>
        <span
          style={{
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            fontFamily: "var(--mono)",
            fontSize: 11,
            padding: "3px 8px",
            borderRadius: 5,
            color: "var(--ink-3)",
          }}
        >
          type · {pr_type}
          {pr_type_confidence !== undefined && (
            <span style={{ color: "var(--muted-2)", marginLeft: 4 }}>
              {pr_type_confidence.toFixed(2)}
            </span>
          )}
        </span>
      </div>
      {headline && (
        <div style={{ fontSize: 16, fontWeight: 500, color: "var(--ink)", marginBottom: 12, lineHeight: 1.4 }}>
          {headline}
        </div>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14, fontFamily: "var(--mono)", fontSize: 11, color: "var(--muted)" }}>
        <span>risk_score</span>
        <span style={{ flex: 1, height: 4, maxWidth: 180, background: "var(--border-2)", borderRadius: 2, overflow: "hidden" }}>
          <span style={{ display: "block", height: "100%", background: "var(--accent)", width: `${Math.round(risk_score * 100)}%` }} />
        </span>
        <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>{risk_score.toFixed(2)}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 12 }}>
        <Stat n={blast_radius.caller_files} l="caller_files" />
        <Stat n={blast_radius.modules_crossed} l="modules_crossed" />
        <Stat n={blast_radius.public_symbols_modified} l="public_symbols_modified" hl />
        <Stat n={blast_radius.external_refs_added} l="external_refs_added" hl prefix="+" />
      </div>
      {novelty && (
        <div style={{ display: "flex", gap: 12, marginBottom: 12, fontFamily: "var(--mono)", fontSize: 11, color: "var(--muted)" }}>
          <span>new_files <b style={{ color: "var(--ink-2)" }}>{novelty.new_files}</b></span>
          <span>new_symbols <b style={{ color: "var(--ink-2)" }}>{novelty.new_symbols}</b></span>
          <span>new_external_refs <b style={{ color: "var(--ink-2)" }}>+{novelty.new_external_refs}</b></span>
        </div>
      )}
      {advisory_flags.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {advisory_flags.map((f) => (
            <span
              key={f}
              style={{
                display: "inline-block",
                border: "1px dashed var(--accent)",
                color: "var(--accent)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                padding: "3px 8px",
                borderRadius: 100,
              }}
            >
              ⚠ {f}
            </span>
          ))}
        </div>
      )}
    </A2Card>
  );
}

function Stat({ n, l, hl, prefix = "" }: { n: number; l: string; hl?: boolean; prefix?: string }) {
  return (
    <div
      style={{
        border: "1px solid",
        borderRadius: 6,
        padding: "10px 12px",
        background: hl ? "var(--accent-soft2)" : "var(--surface-2)",
        borderColor: hl ? "var(--accent-soft)" : "var(--border-2)",
      }}
    >
      <span style={{ display: "block", fontSize: 18, fontWeight: 600, color: hl ? "var(--accent)" : "var(--ink)" }}>
        {prefix}
        {n}
      </span>
      <span style={{ display: "block", fontFamily: "var(--mono)", fontSize: 10, color: "var(--muted)", marginTop: 2 }}>
        {l}
      </span>
    </div>
  );
}
