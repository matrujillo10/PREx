import { lazy, Suspense } from "react";
import { DiffColumn } from "../components/DiffColumn";
import { useStore } from "../state/store";
import styles from "./ReviewSurface.module.css";

const ChatShell = lazy(() =>
  import("../components/ChatShell").then((m) => ({ default: m.ChatShell })),
);

/**
 * Simplified PR-review surface: a small PR header strip + diff + chat.
 * Everything else (briefing, plan, checklist) is rendered by the chat agent
 * via A2GUI cards on demand. The chat auto-greets with brief + plan +
 * checklist on first mount.
 */
export function ReviewSurface() {
  const brief = useStore((s) => s.brief)!;
  const pr = brief.pr;
  return (
    <>
      <div className={styles.prbar}>
        <div className={styles.prTop}>
          <span className={styles.num}>#{pr.number}</span>
          <span className={styles.pill}>Open</span>
          <span>
            {pr.author} · {pr.repo}
          </span>
        </div>
        <h1 className={styles.prTitle}>{pr.title}</h1>
        <div className={styles.prMeta}>
          +{pr.additions} / −{pr.deletions} across {pr.changed_files} files · {brief.generator}
        </div>
      </div>
      <div className={styles.body}>
        <div className={styles.diffPane}>
          <DiffColumn />
        </div>
        <div className={styles.chatPane}>
          <Suspense fallback={<ChatLoading />}>
            <ChatShell scope="pr" />
          </Suspense>
        </div>
      </div>
    </>
  );
}

function ChatLoading() {
  return (
    <div
      style={{
        border: "1px dashed var(--border)",
        borderRadius: 6,
        padding: "14px 16px",
        background: "var(--surface)",
        color: "var(--muted)",
        fontStyle: "italic",
        fontSize: 13,
      }}
    >
      Loading Copilot…
    </div>
  );
}
