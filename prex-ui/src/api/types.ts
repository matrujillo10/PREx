// TypeScript types mirroring prex/schemas/{_shared,graph,brief}.py.
// Hand-maintained for v0.1; switch to a generator off prex/schemas/dist/*.json
// once the schema stabilises further.

// ---------- shared ----------

export type Derivation =
  | "ast"
  | "diff"
  | "crossref_text"
  | "llm"
  | "manifest"
  | "heuristic";

export type ChangeState = "unchanged" | "added" | "modified" | "removed";

export interface LineRange {
  start: number;
  end: number;
}

export interface Citation {
  kind: "node" | "edge" | "file_line" | "external_doc";
  ref: string;
  excerpt?: string | null;
  derivation: Derivation;
  score?: number | null;
}

export interface Diagnostic {
  level: "info" | "warn" | "error";
  code: string;
  message: string;
  related_node_ids: string[];
}

// ---------- graph ----------

export type NodeKind =
  | "module"
  | "file"
  | "symbol"
  | "caller_stub"
  | "hunk"
  | "external_ref";

export type SymbolKind =
  | "function"
  | "method"
  | "class"
  | "type"
  | "const"
  | "test";

export type EdgeType =
  | "contains"
  | "defines"
  | "touches"
  | "calls"
  | "references"
  | "imports"
  | "covers"
  | "external";

export interface PRMetadata {
  url: string;
  repo: string;
  number: number;
  title: string;
  body?: string | null;
  author: string;
  base_ref: string;
  head_ref: string;
  base_sha: string;
  head_sha: string;
  additions: number;
  deletions: number;
  changed_files: number;
}

interface NodeBase {
  id: string;
  derivation: Derivation;
  score: number;
  change_state: ChangeState;
  cites: Citation[];
}

export interface ModuleNode extends NodeBase {
  kind: "module";
  name: string;
  path: string;
}

export interface FileNode extends NodeBase {
  kind: "file";
  path: string;
  language: string;
  generated: boolean;
}

export interface SymbolNode extends NodeBase {
  kind: "symbol";
  symbol_kind: SymbolKind;
  name: string;
  qualified_name: string;
  file_id: string;
  line_range: LineRange;
  signature?: string | null;
  public: boolean;
}

export interface CallerStub extends NodeBase {
  kind: "caller_stub";
  qualified_name: string;
  file_id: string;
  symbol_kind?: SymbolKind | null;
}

export interface HunkNode extends NodeBase {
  kind: "hunk";
  file_id: string;
  line_range: LineRange;
  change_type: "added" | "modified" | "removed";
  patch: string;
}

export interface ExternalRefNode extends NodeBase {
  kind: "external_ref";
  ref_kind: "db_table" | "http_route" | "grpc_method" | "package" | "other";
  name: string;
  detail?: string | null;
}

export type GraphNode =
  | ModuleNode
  | FileNode
  | SymbolNode
  | CallerStub
  | HunkNode
  | ExternalRefNode;

export interface Edge {
  id: string;
  type: EdgeType;
  source_id: string;
  target_id: string;
  derivation: Derivation;
  score: number;
  change_state: ChangeState;
  cites: Citation[];
  note?: string | null;
}

export interface Graph {
  schema_version: string;
  generated_at: string;
  generator: string;
  pr: PRMetadata;
  nodes: GraphNode[];
  edges: Edge[];
  diagnostics: Diagnostic[];
}

// ---------- brief ----------

export type PRType = "feat" | "fix" | "chore" | "unknown";
export type RiskTier = "trivial" | "standard" | "sensitive";

export type RiskSignal =
  | "auth_or_authz_touched"
  | "sql_in_changed_lines"
  | "external_io"
  | "removes_assertion"
  | "weakens_validation"
  | "raises_swallowed"
  | "broad_except"
  | "feature_flag_added"
  | "feature_flag_removed"
  | "secret_like_string"
  | "numeric_constant_changed_in_hot_loop";

export type HunkIntent =
  | "adds_capability"
  | "fixes_bug"
  | "renames"
  | "extracts"
  | "inlines"
  | "reorders"
  | "tightens_types"
  | "weakens_test"
  | "adds_test"
  | "removes_dead"
  | "comments_only"
  | "style_only"
  | "unknown";

export type AdvisoryFlag =
  | "scope_creep_5plus_areas"
  | "test_lines_removed"
  | "generated_files_only"
  | "secret_like_string_added"
  | "no_test_coverage_changed"
  | "ai_authorship_undisclosed"
  | "no_docs_for_public_api"
  | "removes_assertion"
  | "broad_except_added";

export interface BlastRadius {
  caller_files: number;
  modules_crossed: number;
  public_symbols_modified: number;
  external_refs_added: number;
}

export interface Novelty {
  new_files: number;
  new_symbols: number;
  new_external_refs: number;
}

export interface ReviewBrief {
  pr_type: PRType;
  pr_type_confidence: number;
  pr_type_evidence: Citation[];
  risk_tier: RiskTier;
  risk_score: number;
  blast_radius: BlastRadius;
  novelty: Novelty;
  headline?: string | null;
  advisory_flags: AdvisoryFlag[];
  cites: Citation[];
}

export interface ReviewStep {
  rank: number;
  target: string;
  title?: string | null;
  what?: string | null;
  why?: string | null;
  impact?: string | null;
  estimated_minutes: number;
  risk_signals: RiskSignal[];
  related_targets: string[];
  cites: Citation[];
}

export interface ReviewPlan {
  overview?: string | null;
  steps: ReviewStep[];
  cites: Citation[];
}

export interface HunkInsight {
  hunk_id: string;
  one_liner?: string | null;
  intent: HunkIntent;
  risk_signals: RiskSignal[];
  affects_public_symbol_ids: string[];
  cites: Citation[];
  score: number;
}

export type ChecklistStatus = "pass" | "fail" | "unknown";

export interface ChecklistItem {
  id: string;
  text: string;
  required: boolean;
  targets: string[];
  auto_status?: ChecklistStatus | null;
  auto_evidence?: Citation | null;
}

export interface ChecklistBinding {
  type?: PRType | null;
  checklist_items: ChecklistItem[];
}

export interface Brief {
  schema_version: string;
  generated_at: string;
  generator: string;
  pr: PRMetadata;
  review: ReviewBrief;
  plan: ReviewPlan;
  hunks: HunkInsight[];
  checklist: ChecklistBinding[];
  graph_ref: string;
  diagnostics: Diagnostic[];
  llm_used: boolean;
}
