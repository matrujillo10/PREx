/** Zod schemas for the A2GUI diagram catalog.
 *
 * The host LLM must emit one of these shapes when calling the corresponding
 * frontend tool. They double as the runtime input contract for each diagram
 * component.
 */
import { z } from "zod";

const NodeId = z.string().min(1);
const Derivation = z.enum([
  "ast",
  "diff",
  "crossref_text",
  "llm",
  "manifest",
  "heuristic",
]);

// --- Treemap ---
export const TreemapFile = z.object({
  path: z.string(),
  additions: z.number().int().nonnegative(),
  deletions: z.number().int().nonnegative(),
  hunkCount: z.number().int().nonnegative().default(0),
  generated: z.boolean().default(false),
  sensitive: z.boolean().default(false),
});
export const TreemapInput = z.object({
  title: z.string().optional(),
  files: z.array(TreemapFile).min(1),
  source: z.string().optional(),
});
export type TreemapInputT = z.infer<typeof TreemapInput>;

// --- CouplingMap ---
export const CouplingNode = z.object({
  id: NodeId,
  label: z.string(),
  kind: z
    .enum(["symbol", "file", "external_ref", "module"])
    .optional(),
  sensitive: z.boolean().default(false),
});
export const CouplingEdge = z.object({
  from: NodeId,
  to: NodeId,
  derivation: Derivation,
  label: z.string().optional(),
});
export const CouplingMapInput = z.object({
  title: z.string().optional(),
  nodes: z.array(CouplingNode).min(2),
  edges: z.array(CouplingEdge).min(1),
  source: z.string().optional(),
});
export type CouplingMapInputT = z.infer<typeof CouplingMapInput>;

// --- ClassDiff ---
const ClassField = z.object({
  name: z.string(),
  type: z.string().optional(),
  state: z.enum(["unchanged", "added", "removed", "modified"]).default("unchanged"),
});
const ClassShape = z.object({
  name: z.string(),
  fields: z.array(ClassField),
});
export const ClassDiffInput = z.object({
  title: z.string().optional(),
  before: ClassShape,
  after: ClassShape,
  source: z.string().optional(),
});
export type ClassDiffInputT = z.infer<typeof ClassDiffInput>;

// --- BlastRadius ---
const BlastNode = z.object({
  id: NodeId,
  label: z.string(),
  inferred: z.boolean().default(false),
});
const BlastEdge = z.object({
  from: NodeId,
  to: NodeId,
  derivation: Derivation,
});
export const BlastRadiusInput = z.object({
  title: z.string().optional(),
  target: BlastNode,
  neighborhood: z.array(BlastNode),
  edges: z.array(BlastEdge),
  source: z.string().optional(),
});
export type BlastRadiusInputT = z.infer<typeof BlastRadiusInput>;

// --- DataFlowChain ---
const FlowCard = z.object({
  label: z.string(),
  fileLoc: z.string().optional(),
  role: z.enum(["source", "transform", "sink"]).default("transform"),
});
export const DataFlowChainInput = z.object({
  title: z.string().optional(),
  cards: z.array(FlowCard).min(2),
  source: z.string().optional(),
});
export type DataFlowChainInputT = z.infer<typeof DataFlowChainInput>;

// --- Sequence ---
const SequenceMessage = z.object({
  from: NodeId,
  to: NodeId,
  label: z.string(),
  kind: z.enum(["sync", "reply", "sql"]).default("sync"),
});
const SequenceActor = z.object({ id: NodeId, name: z.string() });
export const SequenceInput = z.object({
  title: z.string().optional(),
  actors: z.array(SequenceActor).min(2),
  messages: z.array(SequenceMessage).min(1),
  source: z.string().optional(),
});
export type SequenceInputT = z.infer<typeof SequenceInput>;
