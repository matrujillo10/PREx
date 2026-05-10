import type { ChecklistCardInputT } from "./schemas";
import { A2Card } from "./A2Card";

const ICON: Record<string, string> = { pass: "✓", fail: "✗", unknown: "?" };
const ICON_COLOR: Record<string, { bg: string; fg: string; border: string; style?: string }> = {
  pass: { bg: "var(--surface)", fg: "var(--add)", border: "var(--add)" },
  fail: { bg: "var(--accent)", fg: "var(--surface)", border: "var(--accent)" },
  unknown: { bg: "var(--surface)", fg: "var(--muted)", border: "var(--muted-2)", style: "dashed" },
};

const ORDER = ["fail", "pass", "unknown"] as const;
const LABEL: Record<string, string> = {
  fail: "Failed · attention required",
  pass: "Passed · auto-verified",
  unknown: "Unknown · not applicable",
};

export function ChecklistCard({ items, source }: ChecklistCardInputT) {
  const grouped: Record<string, typeof items> = { pass: [], fail: [], unknown: [] };
  for (const it of items) grouped[it.status]?.push(it);

  return (
    <A2Card componentName="Checklist" title="Manifest checklist" source={source}>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {ORDER.map((g) =>
          grouped[g] && grouped[g].length > 0 ? (
            <div key={g}>
              <div
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--muted)",
                  marginBottom: 6,
                }}
              >
                {LABEL[g]}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {grouped[g].map((it) => {
                  const c = ICON_COLOR[it.status];
                  return (
                    <div
                      key={it.id}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "18px 1fr",
                        columnGap: 10,
                        rowGap: 4,
                        padding: "8px 10px",
                        background: "var(--surface)",
                        border: "1px solid var(--border-2)",
                        borderRadius: 6,
                        fontSize: 12.5,
                      }}
                    >
                      <span
                        style={{
                          width: 18,
                          height: 18,
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: "50%",
                          background: c.bg,
                          color: c.fg,
                          border: `1px ${c.style ?? "solid"} ${c.border}`,
                          fontSize: 11,
                          fontFamily: "var(--mono)",
                        }}
                      >
                        {ICON[it.status]}
                      </span>
                      <span style={{ color: "var(--ink-2)" }}>{it.text}</span>
                      <span
                        style={{
                          gridColumn: 2,
                          fontFamily: "var(--mono)",
                          fontSize: 10.5,
                          color: "var(--muted)",
                          display: "flex",
                          gap: 6,
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <span>{it.targets_count} targets</span>
                        {it.required && (
                          <span
                            style={{
                              background: "var(--accent-soft)",
                              color: "var(--accent)",
                              borderRadius: 3,
                              padding: "1px 6px",
                              border: "1px solid var(--accent-soft)",
                            }}
                          >
                            required
                          </span>
                        )}
                        {it.evidence && (
                          <span style={{ color: "var(--ink-3)", overflowWrap: "anywhere", wordBreak: "break-word" }}>
                            {it.evidence}
                          </span>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null,
        )}
      </div>
    </A2Card>
  );
}
