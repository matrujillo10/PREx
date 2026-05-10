import type { ClassDiffInputT } from "./schemas";
import { A2Card } from "./A2Card";

export function ClassDiff({ title, before, after, source }: ClassDiffInputT) {
  return (
    <A2Card componentName="ClassDiff" title={title ?? `${after.name} (before / after)`} source={source}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {[
          { label: "before", shape: before },
          { label: "after", shape: after },
        ].map(({ label, shape }) => (
          <div
            key={label}
            style={{
              border: "1px solid var(--border-2)",
              borderRadius: 6,
              background: "var(--surface-2)",
              padding: 12,
              fontFamily: "var(--mono)",
              fontSize: 12,
            }}
          >
            <div style={{ fontSize: 10, color: "var(--muted)", textTransform: "uppercase" }}>
              {label}
            </div>
            <div style={{ marginTop: 6, fontWeight: 600, color: "var(--ink-2)" }}>
              class {shape.name}
            </div>
            <ul style={{ margin: "8px 0 0", padding: "0 0 0 14px", color: "var(--ink-3)" }}>
              {shape.fields.map((f) => (
                <li
                  key={f.name + label}
                  style={{
                    color:
                      f.state === "added"
                        ? "var(--add)"
                        : f.state === "removed"
                          ? "var(--del)"
                          : f.state === "modified"
                            ? "var(--accent)"
                            : "var(--ink-3)",
                  }}
                >
                  {f.state === "added" ? "+ " : f.state === "removed" ? "- " : "  "}
                  {f.name}
                  {f.type && `: ${f.type}`}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </A2Card>
  );
}
