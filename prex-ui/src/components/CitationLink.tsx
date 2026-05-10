import type { Citation } from "../api/types";
import { useStore } from "../state/store";

interface Props {
  cites: Citation[];
  source: string;
  title?: string;
}

/**
 * The `↳` affordance shown next to every prose field. Clicking opens the
 * citation drawer (Surface C) seeded with the prose source label and cites.
 */
export function CitationLink({ cites, source, title = "Citations" }: Props) {
  const open = useStore((s) => s.openDrawer);
  if (!cites?.length) return null;
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={(e) => {
        e.stopPropagation();
        open(source, cites);
      }}
      style={{
        background: "none",
        border: "none",
        padding: "0 4px",
        color: "var(--muted)",
        font: "inherit",
        lineHeight: 1,
        verticalAlign: "middle",
        cursor: "pointer",
      }}
    >
      ↳
    </button>
  );
}
