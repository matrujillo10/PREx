import { lazy, Suspense } from "react";
import { ChecklistColumn } from "../components/ChecklistColumn";
import { DiffColumn } from "../components/DiffColumn";
import { Hero } from "../components/Hero";
import { PlanColumn } from "../components/PlanColumn";
import styles from "./ReviewSurface.module.css";

const ChatShell = lazy(() =>
  import("../components/ChatShell").then((m) => ({ default: m.ChatShell })),
);

export function ReviewSurface() {
  return (
    <>
      <Hero />
      <div className={styles.body}>
        <PlanColumn />
        <DiffColumn />
        <ChecklistColumn />
        <aside className={styles.chatCol}>
          <div className={styles.chatColInner}>
            <Suspense fallback={<ChatLoading />}>
              <ChatShell scope="pr" />
            </Suspense>
          </div>
        </aside>
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
