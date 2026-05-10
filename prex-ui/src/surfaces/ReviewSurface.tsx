import { ChatShell } from "../components/ChatShell";
import { ChecklistColumn } from "../components/ChecklistColumn";
import { DiffColumn } from "../components/DiffColumn";
import { Hero } from "../components/Hero";
import { PlanColumn } from "../components/PlanColumn";
import styles from "./ReviewSurface.module.css";

export function ReviewSurface() {
  return (
    <>
      <Hero />
      <div className={styles.body}>
        <PlanColumn />
        <DiffColumn />
        <ChecklistColumn />
      </div>
      <div className={styles.chat}>
        <ChatShell scope="pr" />
      </div>
    </>
  );
}
