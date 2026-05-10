import type { FileNode } from "../api/types";
import { useStore } from "../state/store";
import { CitationLink } from "./CitationLink";
import styles from "./Hero.module.css";

export function Hero() {
  const brief = useStore((s) => s.brief)!;
  const graph = useStore((s) => s.graph);
  const review = brief.review;
  const pr = brief.pr;
  const initials = pr.author
    .split(/[^a-z]+/i)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

  const blast = review.blast_radius;
  const novelty = review.novelty;
  const fileNodes: FileNode[] =
    graph?.nodes.filter(
      (n): n is FileNode => n.kind === "file" && n.change_state !== "unchanged",
    ) ?? [];

  const treemap = buildTreemapTiles(fileNodes);

  return (
    <>
      <div className={styles.prbar}>
        <div className={styles.top}>
          <span className={styles.num}>#{pr.number}</span>
          <span className={styles.pill}>Open</span>
          <span className={styles.author}>
            <span className={styles.av}>{initials || "??"}</span>
            {pr.author} wants to merge into{" "}
            <span className={styles.branch}>{pr.base_ref}</span> from{" "}
            <span className={styles.branch}>{pr.head_ref.slice(0, 28)}</span>
          </span>
        </div>
        <h1 className={styles.h1}>{pr.title}</h1>
        <div className={styles.metaRow}>
          <span>
            +{pr.additions} / −{pr.deletions} across {pr.changed_files} files
          </span>
          <span style={{ marginLeft: "auto" }} className={styles.anno}>
            {brief.generator}
          </span>
        </div>
      </div>
      <div className={styles.hero}>
        <div className={styles.heroLeft}>
          <div className={styles.riskRow}>
            <span className={styles.riskBadge}>
              <span className={styles.dot} />
              RISK · {review.risk_tier.toUpperCase()}
            </span>
            <span className={`${styles.chip} ${styles.chipMono}`}>
              type · {review.pr_type}{" "}
              <span className={styles.anno}>
                {review.pr_type_confidence.toFixed(2)}
              </span>
            </span>
            {brief.llm_used && review.headline && (
              <span className={`${styles.chip} ${styles.chipAi}`}>
                inferred headline
              </span>
            )}
          </div>
          <div className={styles.headline}>
            {review.headline ?? (
              <em style={{ color: "var(--muted)" }}>
                (LLM headline not generated — falling back to pr.title)
              </em>
            )}
            <CitationLink cites={review.cites} source="review.headline" />
          </div>
          <div className={styles.riskScore}>
            <span>risk_score</span>
            <span className={styles.bar}>
              <span
                className={styles.fill}
                style={{ width: `${Math.round(review.risk_score * 100)}%` }}
              />
            </span>
            <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>
              {review.risk_score.toFixed(2)}
            </span>
            <span className={styles.anno}>/ 1.00</span>
          </div>
          <div className={styles.blast}>
            <Stat n={blast.caller_files} l="caller_files" />
            <Stat n={blast.modules_crossed} l="modules_crossed" />
            <Stat n={blast.public_symbols_modified} l="public_symbols_modified" hl />
            <Stat
              n={blast.external_refs_added}
              l="external_refs_added"
              hl
              prefix="+"
            />
          </div>
          <div className={styles.flagsRow}>
            {review.advisory_flags.map((f) => (
              <span key={f} className={styles.flagChip}>
                ⚠ {f}
              </span>
            ))}
          </div>
        </div>
        <div className={styles.heroRight}>
          <div className={styles.tmH}>
            <span className={styles.ttl}>
              Change density · {pr.changed_files} files
            </span>
            <span style={{ marginLeft: "auto" }} className={styles.anno}>
              +{pr.additions} / −{pr.deletions}
            </span>
          </div>
          <div className={styles.treemap}>
            {treemap.map((t) => (
              <div
                key={t.label}
                className={`${styles.tm} ${t.hot ? styles.tmHot : ""} ${
                  t.gen ? styles.tmGen : ""
                }`}
              >
                <div>
                  <div className={styles.nm}>{t.label}</div>
                  <div className={styles.sub}>{t.sub}</div>
                </div>
                <div className={styles.delta}>
                  <span className={styles.add}>+{t.additions}</span> ·{" "}
                  <span className={styles.del}>−{t.deletions}</span>
                </div>
              </div>
            ))}
          </div>
          <div className={styles.novelty}>
            <div className={styles.nv}>
              <span className={styles.n}>{novelty.new_files}</span>
              <span className={styles.l}>new_files</span>
            </div>
            <span className={styles.sep} />
            <div className={styles.nv}>
              <span className={styles.n}>{novelty.new_symbols}</span>
              <span className={styles.l}>new_symbols</span>
            </div>
            <span className={styles.sep} />
            <div className={styles.nv}>
              <span className={styles.n}>+{novelty.new_external_refs}</span>
              <span className={styles.l}>new_external_refs</span>
            </div>
            <span className={styles.sep} />
            <div className={styles.nv}>
              <span className={styles.n}>{brief.plan.steps.length}</span>
              <span className={styles.l}>plan_steps</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function Stat({
  n,
  l,
  hl,
  prefix = "",
}: {
  n: number;
  l: string;
  hl?: boolean;
  prefix?: string;
}) {
  return (
    <div className={`${styles.stat} ${hl ? styles.statHl : ""}`}>
      <span className={styles.n}>
        {prefix}
        {n}
      </span>
      <span className={styles.l}>{l}</span>
    </div>
  );
}

interface Tile {
  label: string;
  sub: string;
  additions: number;
  deletions: number;
  hot: boolean;
  gen: boolean;
}

function buildTreemapTiles(files: FileNode[]): Tile[] {
  const nonGen = files.filter((f) => !f.generated);
  const gen = files.filter((f) => f.generated);
  const tiles: Tile[] = [];
  for (const f of nonGen.slice(0, 3)) {
    tiles.push({
      label: f.path.split("/").pop() ?? f.path,
      sub: f.path.split("/").slice(-2, -1).join("/"),
      additions: 0,
      deletions: 0,
      hot: tiles.length === 0,
      gen: false,
    });
  }
  if (nonGen.length > 3) {
    tiles.push({
      label: `${nonGen[3].path.split("/").pop()} +${nonGen.length - 4}`,
      sub: `${nonGen.length - 3} files`,
      additions: 0,
      deletions: 0,
      hot: false,
      gen: false,
    });
  }
  if (gen.length) {
    tiles.push({
      label: `…_pb2.py +${gen.length - 1}`,
      sub: "generated · collapsed",
      additions: 0,
      deletions: 0,
      hot: false,
      gen: true,
    });
  }
  return tiles.slice(0, 4);
}
