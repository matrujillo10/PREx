import { ReactNode } from "react";
import styles from "./A2Card.module.css";

interface Props {
  componentName: string;
  title?: string;
  source?: string;
  action?: { label: string; onClick: () => void };
  children: ReactNode;
}

export function A2Card({
  componentName,
  title,
  source,
  action,
  children,
}: Props) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <span className={styles.tag}>A2GUI</span>
        <span className={styles.title}>{title ?? componentName}</span>
        <span className={styles.meta}>component · {componentName}</span>
      </div>
      <div className={styles.body}>{children}</div>
      <div className={styles.foot}>
        <span>derived from {source ?? "graph.json"}</span>
        {action && (
          <button className={styles.action} onClick={action.onClick}>
            {action.label}
          </button>
        )}
      </div>
    </div>
  );
}
