import { useEffect, useMemo, useRef } from "react";
import type { FileNode, HunkInsight, HunkNode } from "../api/types";
import { useStore } from "../state/store";
import { CitationLink } from "./CitationLink";
import styles from "./DiffColumn.module.css";

export function DiffColumn() {
  const brief = useStore((s) => s.brief)!;
  const graph = useStore((s) => s.graph);
  const activeFile = useStore((s) => s.activeFileTab);
  const setActiveFile = useStore((s) => s.setActiveFileTab);
  const activeHunk = useStore((s) => s.activeHunkId);

  const fileNodes = useMemo<FileNode[]>(
    () =>
      (graph?.nodes.filter(
        (n): n is FileNode => n.kind === "file" && n.change_state !== "unchanged",
      ) ?? []),
    [graph],
  );

  const hunksByFile = useMemo(() => {
    const m = new Map<string, HunkNode[]>();
    if (!graph) return m;
    for (const n of graph.nodes) {
      if (n.kind !== "hunk") continue;
      const file = graph.nodes.find((x) => x.id === n.file_id) as
        | FileNode
        | undefined;
      if (!file) continue;
      const arr = m.get(file.path) ?? [];
      arr.push(n);
      m.set(file.path, arr);
    }
    return m;
  }, [graph]);

  const insightByHunk = useMemo(() => {
    const m = new Map<string, (typeof brief.hunks)[number]>();
    for (const h of brief.hunks) m.set(h.hunk_id, h);
    return m;
  }, [brief.hunks]);

  const fileNodeByPath = useMemo(() => {
    const m = new Map<string, FileNode>();
    for (const f of fileNodes) m.set(f.path, f);
    return m;
  }, [fileNodes]);

  const visibleHunks = activeFile ? hunksByFile.get(activeFile) ?? [] : [];

  return (
    <div className={styles.col}>
      <div className={styles.tabs}>
        {fileNodes.map((f) => (
          <button
            key={f.path}
            className={`${styles.tab} ${activeFile === f.path ? styles.tabActive : ""} ${
              f.generated ? styles.tabGen : ""
            }`}
            onClick={() => setActiveFile(f.path)}
            title={f.path}
          >
            {f.generated && "⊝ "}
            {f.path.split("/").pop()}
          </button>
        ))}
      </div>
      <div className={styles.list}>
        {visibleHunks.map((h) => (
          <HunkBlock
            key={h.id}
            hunk={h}
            file={fileNodeByPath.get(activeFile!)!}
            insight={insightByHunk.get(h.id)}
            current={activeHunk === h.id}
          />
        ))}
        {!visibleHunks.length && (
          <div style={{ color: "var(--muted)", padding: 14, fontSize: 12 }}>
            (no hunks under this file — pick another tab)
          </div>
        )}
      </div>
    </div>
  );
}

function HunkBlock({
  hunk,
  file,
  insight,
  current,
}: {
  hunk: HunkNode;
  file: FileNode;
  insight: HunkInsight | undefined;
  current: boolean;
}) {
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
                <CitationLink cites={insight.cites} source={`hunks[${hunk.id}].one_liner`} />
              </div>
            )}
          </>
        )}
      </div>
      <div className={styles.body}>{renderPatch(hunk.patch)}</div>
    </div>
  );
}

function renderPatch(patch: string) {
  const lines = patch.split("\n");
  // Skip the leading @@ header from rendering as a line, instead make it a subtle row.
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
        <div key={i} className={styles.line} style={{ background: "var(--surface-3)", color: "var(--muted)" }}>
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
