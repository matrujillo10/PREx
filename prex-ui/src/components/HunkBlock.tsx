import { useEffect, useRef } from "react";
import type { FileNode, HunkInsight, HunkNode } from "../api/types";
import { CitationLink } from "./CitationLink";
import styles from "./DiffColumn.module.css";

interface Props {
  hunk: HunkNode;
  file: FileNode;
  insight: HunkInsight | undefined;
  current: boolean;
}

/**
 * Single hunk render — header overlay (file:line · intent · risk chips ·
 * one-liner) + the diff body. Reused by Surface A's diff column and
 * Surface B's step focus.
 */
export function HunkBlock({ hunk, file, insight, current }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (current && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [current]);

  return (
    <div ref={ref} className={`${styles.hunk} ${current ? styles.hunkCurrent : ""}`}>
      <div className={styles.hunkHead}>
        <span className={styles.hunkLoc}>
          {file.path.split("/").pop()}:{hunk.line_range.start}-{hunk.line_range.end}
        </span>
        {insight && (
          <>
            <span className={styles.intentChip}>{insight.intent}</span>
            {insight.risk_signals.map((s) => (
              <span key={s} className={styles.signalChip}>
                {s}
              </span>
            ))}
            {insight.one_liner && (
              <div className={styles.oneLiner}>
                {insight.one_liner}
                <CitationLink
                  cites={insight.cites}
                  source={`hunks[${hunk.id}].one_liner`}
                />
              </div>
            )}
          </>
        )}
      </div>
      <div className={styles.body}>{renderPatch(hunk.patch)}</div>
    </div>
  );
}

function renderPatch(patch: string): JSX.Element[] {
  const lines = patch.split("\n");
  const out: JSX.Element[] = [];
  let leftLine = 0;
  let rightLine = 0;
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    if (ln.startsWith("@@")) {
      const m = /-(\d+),?\d* \+(\d+),?\d*/.exec(ln);
      if (m) {
        leftLine = parseInt(m[1], 10);
        rightLine = parseInt(m[2], 10);
      }
      out.push(
        <div
          key={i}
          className={styles.line}
          style={{ background: "var(--surface-3)", color: "var(--muted)" }}
        >
          <span className={styles.gutter} />
          <span className={styles.gutter} />
          <span className={styles.text}>{ln}</span>
        </div>,
      );
      continue;
    }
    if (ln.startsWith("+") && !ln.startsWith("+++")) {
      out.push(
        <div key={i} className={`${styles.line} ${styles.add}`}>
          <span className={styles.gutter} />
          <span className={styles.gutter}>{rightLine}</span>
          <span className={styles.text}>{ln}</span>
        </div>,
      );
      rightLine++;
      continue;
    }
    if (ln.startsWith("-") && !ln.startsWith("---")) {
      out.push(
        <div key={i} className={`${styles.line} ${styles.del}`}>
          <span className={styles.gutter}>{leftLine}</span>
          <span className={styles.gutter} />
          <span className={styles.text}>{ln}</span>
        </div>,
      );
      leftLine++;
      continue;
    }
    out.push(
      <div key={i} className={styles.line}>
        <span className={styles.gutter}>{leftLine}</span>
        <span className={styles.gutter}>{rightLine}</span>
        <span className={styles.text}>{ln || " "}</span>
      </div>,
    );
    leftLine++;
    rightLine++;
  }
  return out;
}
