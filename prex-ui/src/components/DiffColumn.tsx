import { useMemo } from "react";
import type { FileNode, HunkNode } from "../api/types";
import { useStore } from "../state/store";
import { HunkBlock } from "./HunkBlock";
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

