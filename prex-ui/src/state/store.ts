import { create } from "zustand";
import type { Brief, Citation, Graph } from "../api/types";

interface DrawerState {
  open: boolean;
  source: string; // e.g. "step 1 / impact"
  cites: Citation[];
  selectedIndex: number;
}

interface AppState {
  brief: Brief | null;
  graph: Graph | null;
  selectedStep: number; // 1-indexed
  activeFileTab: string | null;
  activeHunkId: string | null;
  drawer: DrawerState;
  chatScope: "pr" | `step:${number}`;

  setData: (brief: Brief, graph: Graph) => void;
  selectStep: (rank: number) => void;
  setActiveFileTab: (path: string | null) => void;
  setActiveHunk: (id: string | null) => void;
  openDrawer: (source: string, cites: Citation[]) => void;
  selectCitation: (i: number) => void;
  closeDrawer: () => void;
  setChatScope: (scope: "pr" | `step:${number}`) => void;
}

export const useStore = create<AppState>((set) => ({
  brief: null,
  graph: null,
  selectedStep: 1,
  activeFileTab: null,
  activeHunkId: null,
  drawer: { open: false, source: "", cites: [], selectedIndex: 0 },
  chatScope: "pr",

  setData: (brief, graph) =>
    set({
      brief,
      graph,
      activeFileTab: defaultActiveFile(graph),
      activeHunkId: defaultActiveHunk(brief),
    }),
  selectStep: (rank) => set({ selectedStep: rank, chatScope: `step:${rank}` }),
  setActiveFileTab: (path) => set({ activeFileTab: path }),
  setActiveHunk: (id) => set({ activeHunkId: id }),
  openDrawer: (source, cites) =>
    set({ drawer: { open: true, source, cites, selectedIndex: 0 } }),
  selectCitation: (i) =>
    set((s) => ({ drawer: { ...s.drawer, selectedIndex: i } })),
  closeDrawer: () =>
    set((s) => ({ drawer: { ...s.drawer, open: false } })),
  setChatScope: (scope) => set({ chatScope: scope }),
}));

function defaultActiveFile(graph: Graph | null): string | null {
  if (!graph) return null;
  for (const n of graph.nodes) {
    if (
      n.kind === "file" &&
      n.change_state !== "unchanged" &&
      !n.generated
    ) {
      return n.path;
    }
  }
  return null;
}

function defaultActiveHunk(brief: Brief | null): string | null {
  if (!brief) return null;
  // First hunk under the rank-1 step
  const step = brief.plan.steps.find((s) => s.rank === 1);
  if (!step) return null;
  if (step.target.startsWith("hunk:")) return step.target;
  return null;
}
