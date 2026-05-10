import type { ChecklistItem, ChecklistStatus } from "../api/types";
import { useStore } from "../state/store";
import styles from "./ChecklistColumn.module.css";

const ICONS: Record<ChecklistStatus, string> = {
  pass: "✓",
  fail: "✗",
  unknown: "?",
};

const ICON_CLASS: Record<ChecklistStatus, string> = {
  pass: "iconPass",
  fail: "iconFail",
  unknown: "iconUnknown",
};

const ORDER: ChecklistStatus[] = ["fail", "pass", "unknown"];
const LABEL: Record<ChecklistStatus, string> = {
  fail: "Failed · attention required",
  pass: "Passed · auto-verified",
  unknown: "Unknown · not applicable",
};

export function ChecklistColumn() {
  const brief = useStore((s) => s.brief)!;
  const open = useStore((s) => s.openDrawer);

  const items = brief.checklist.flatMap((b) => b.checklist_items);
  const grouped: Record<ChecklistStatus, ChecklistItem[]> = {
    pass: [],
    fail: [],
    unknown: [],
  };
  for (const it of items) {
    const k = (it.auto_status ?? "unknown") as ChecklistStatus;
    grouped[k].push(it);
  }

  return (
    <aside className={styles.col}>
      <div className={styles.colH}>Checklist</div>
      <div className={styles.list}>
        {ORDER.map((g) =>
          grouped[g].length ? (
            <div key={g} className={styles.group}>
              <span className={styles.groupH}>{LABEL[g]}</span>
              {grouped[g].map((it) => (
                <div key={it.id} className={styles.row}>
                  <span
                    className={`${styles.icon} ${
                      styles[ICON_CLASS[it.auto_status ?? "unknown"]]
                    }`}
                  >
                    {ICONS[it.auto_status ?? "unknown"]}
                  </span>
                  <span className={styles.text}>{it.text}</span>
                  <span className={styles.meta}>
                    <span>{it.targets.length} targets</span>
                    {it.required && <span className={styles.metaPill}>required</span>}
                    {it.auto_evidence && (
                      <button
                        className={styles.evidenceLink}
                        onClick={() =>
                          open(
                            `checklist · ${it.id}`,
                            it.auto_evidence ? [it.auto_evidence] : [],
                          )
                        }
                      >
                        evidence ↳
                      </button>
                    )}
                  </span>
                </div>
              ))}
            </div>
          ) : null,
        )}
      </div>
    </aside>
  );
}
