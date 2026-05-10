import { useEffect } from "react";
import { useStore } from "../state/store";
import styles from "./CitationDrawer.module.css";

const TILE: Record<string, string> = {
  node: "⌥",
  edge: "↔",
  file_line: "¶",
  external_doc: "✱",
};

export function CitationDrawer() {
  const drawer = useStore((s) => s.drawer);
  const close = useStore((s) => s.closeDrawer);
  const select = useStore((s) => s.selectCitation);

  useEffect(() => {
    if (!drawer.open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawer.open, close]);

  if (!drawer.open) return null;
  const selected = drawer.cites[drawer.selectedIndex];

  return (
    <>
      <div className={styles.backdrop} onClick={close} />
      <aside className={styles.drawer} role="dialog" aria-label="Citations">
        <header className={styles.head}>
          <h3>Citations · {drawer.cites.length}</h3>
          <span className={styles.source}>{drawer.source}</span>
          <button className={styles.close} onClick={close} aria-label="Close">
            ✕
          </button>
        </header>
        <div className={styles.quote}>{drawer.source}</div>
        <div className={styles.list}>
          {drawer.cites.map((c, i) => {
            const isSel = i === drawer.selectedIndex;
            const llm = c.derivation === "llm";
            return (
              <button
                key={`${c.kind}:${c.ref}:${i}`}
                className={`${styles.row} ${isSel ? styles.rowSelected : ""}`}
                onClick={() => select(i)}
              >
                <span className={styles.tile}>{TILE[c.kind] ?? "?"}</span>
                <span className={styles.refLabel} title={c.ref}>
                  {c.ref}
                </span>
                <span
                  className={`${styles.derivChip} ${llm ? styles.derivChipLlm : ""}`}
                >
                  {c.derivation}
                  {llm ? " · AI" : ""}
                </span>
                <span className={styles.scoreBar}>
                  <div
                    className={styles.scoreBarFill}
                    style={{ width: `${Math.round((c.score ?? 1) * 100)}%` }}
                  />
                </span>
                {c.excerpt ? (
                  <span className={styles.excerpt}>{c.excerpt}</span>
                ) : null}
              </button>
            );
          })}
        </div>
        {selected && (
          <div className={styles.preview}>
            <h4>Targeted preview</h4>
            <div className={styles.previewBody}>
              <div>
                <strong>{selected.kind}</strong> · {selected.ref}
              </div>
              {selected.excerpt && (
                <div style={{ marginTop: 8, color: "var(--ink-3)" }}>
                  {selected.excerpt}
                </div>
              )}
            </div>
          </div>
        )}
        <footer className={styles.foot}>
          <button>↗ open in graph viewer</button>
          <button
            onClick={() =>
              navigator.clipboard?.writeText(selected?.ref ?? "")
            }
          >
            ⎘ copy ref
          </button>
        </footer>
      </aside>
    </>
  );
}
