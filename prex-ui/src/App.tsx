import { useEffect } from "react";
import { HashRouter, Route, Routes } from "react-router-dom";
import { fetchBrief, fetchGraph } from "./api/client";
import { AppFrame } from "./layout/AppFrame";
import { CitationDrawer } from "./layout/CitationDrawer";
import { useStore } from "./state/store";
import { GraphSurface } from "./surfaces/GraphSurface";
import { ReviewSurface } from "./surfaces/ReviewSurface";
import { StepSurface } from "./surfaces/StepSurface";

export function App() {
  const setData = useStore((s) => s.setData);
  const brief = useStore((s) => s.brief);

  useEffect(() => {
    Promise.all([fetchBrief(), fetchGraph()])
      .then(([b, g]) => setData(b, g))
      .catch((e) => console.error("Failed to load brief/graph", e));
  }, [setData]);

  // HashRouter must always wrap AppFrame because AppFrame's nav uses <Link>.
  return (
    <HashRouter>
      <AppFrame>
        {!brief ? (
          <div style={{ padding: 64, color: "var(--muted)" }}>
            Loading PREx briefing…
          </div>
        ) : (
          <>
            <Routes>
              <Route path="/" element={<ReviewSurface />} />
              <Route path="/step/:rank" element={<StepSurface />} />
              <Route path="/graph" element={<GraphSurface />} />
            </Routes>
            <CitationDrawer />
          </>
        )}
      </AppFrame>
    </HashRouter>
  );
}
