import type { TreemapInputT } from "./schemas";
import { A2Card } from "./A2Card";

export function Treemap({ title, files, source }: TreemapInputT) {
  // Naive 2-row grid — first row biggest two files, second row remainder.
  const sorted = [...files].sort(
    (a, b) => b.additions + b.deletions - (a.additions + a.deletions),
  );
  const total = sorted.reduce(
    (acc, f) => acc + f.additions + f.deletions || 1,
    0,
  );
  return (
    <A2Card componentName="Treemap" title={title ?? "Change density"} source={source}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: 6,
          minHeight: 160,
        }}
      >
        {sorted.map((f, i) => {
          const weight = (f.additions + f.deletions) / total;
          const cols = Math.max(1, Math.round(weight * 6));
          return (
            <div
              key={f.path + i}
              title={f.path}
              style={{
                gridColumn: `span ${Math.min(cols, 6)}`,
                background: f.generated
                  ? "repeating-linear-gradient(135deg,var(--surface-2) 0 4px,var(--surface-3) 4px 8px)"
                  : f.sensitive
                    ? "var(--accent-soft)"
                    : "var(--surface-2)",
                border: "1px solid var(--border-2)",
                borderRadius: 6,
                padding: 8,
                fontFamily: "var(--mono)",
                fontSize: 11.5,
                color: "var(--ink-2)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>{f.path.split("/").pop()}</div>
              <div style={{ fontSize: 10, color: "var(--muted)" }}>
                <span style={{ color: "var(--add)" }}>+{f.additions}</span> ·{" "}
                <span style={{ color: "var(--del)" }}>−{f.deletions}</span>
                {" · "}
                {f.hunkCount} hunks
                {f.generated ? " · gen" : ""}
              </div>
            </div>
          );
        })}
      </div>
    </A2Card>
  );
}
