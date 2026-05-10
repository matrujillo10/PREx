import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useStore } from "../state/store";
import styles from "./AppFrame.module.css";

interface Props {
  children: ReactNode;
}

export function AppFrame({ children }: Props) {
  const brief = useStore((s) => s.brief);
  return (
    <div className={styles.page}>
      <header className={styles.docHead}>
        <span className={styles.logo}>Px</span>
        <span className={styles.title}>PREx</span>
        {brief ? (
          <span className={styles.crumb}>
            {brief.pr.repo} · pull request <b>#{brief.pr.number}</b> · review
          </span>
        ) : (
          <span className={styles.crumb}>loading…</span>
        )}
        <nav style={{ marginLeft: "auto", display: "flex", gap: 12, fontFamily: "var(--mono)", fontSize: 11 }}>
          <Link to="/" style={{ color: "var(--ink-3)" }}>review</Link>
          <Link to="/graph" style={{ color: "var(--ink-3)" }}>graph</Link>
        </nav>
      </header>
      <div className={styles.frame}>{children}</div>
      {brief && (
        <footer className={styles.footer}>
          <span>
            <b>{brief.generator}</b>
          </span>
          <span>·</span>
          <span>
            graph @ <b>{brief.pr.head_sha.slice(0, 7)}</b>
          </span>
          <span>·</span>
          <span>{brief.plan.steps.length} plan steps</span>
          <span>·</span>
          <span>LLM enrichment: <b>{brief.llm_used ? "on" : "off"}</b></span>
        </footer>
      )}
    </div>
  );
}
