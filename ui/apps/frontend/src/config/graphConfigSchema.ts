import { z } from "zod";

// --- Enums ---
export const ChangeStateSchema = z.enum(["unchanged", "added", "modified", "removed"]);
export const ConfidenceSchema = z.enum(["exact", "ambiguous", "llm_inferred"]);
export const EdgeTypeSchema = z.enum(["contains", "defines", "touches", "calls", "references", "imports", "covers", "external"]);
export const ExternalRefKindSchema = z.enum(["db_table", "http_route", "grpc_method", "package", "other"]);
export const SymbolKindSchema = z.enum(["function", "method", "class", "type", "const", "test"]);
export const HunkChangeTypeSchema = z.enum(["added", "modified", "removed"]);

// --- Base Node Attributes ---
export const BaseNodeSchema = z.object({
  id: z.string(),
  confidence: ConfidenceSchema.default("exact"),
  change_state: ChangeStateSchema.default("unchanged"),
});

export const LineRangeSchema = z.object({
  start: z.number().min(1),
  end: z.number().min(1),
});

// --- Specific Node Types ---
export const ModuleNodeSchema = BaseNodeSchema.extend({
  kind: z.literal("module"),
  name: z.string(),
  path: z.string()
});

export const FileNodeSchema = BaseNodeSchema.extend({
  kind: z.literal("file"),
  path: z.string(),
  language: z.string(),
  generated: z.boolean().default(false).optional()
});

export const SymbolNodeSchema = BaseNodeSchema.extend({
  kind: z.literal("symbol"),
  symbol_kind: SymbolKindSchema,
  name: z.string(),
  qualified_name: z.string(),
  file_id: z.string(),
  line_range: LineRangeSchema,
  signature: z.string().nullable().optional(),
  public: z.boolean().default(false).optional()
});

export const HunkNodeSchema = BaseNodeSchema.extend({
  kind: z.literal("hunk"),
  file_id: z.string(),
  line_range: LineRangeSchema,
  change_type: HunkChangeTypeSchema,
  patch: z.string()
});

export const ExternalRefNodeSchema = BaseNodeSchema.extend({
  kind: z.literal("external_ref"),
  ref_kind: ExternalRefKindSchema,
  name: z.string(),
  detail: z.string().nullable().optional()
});

export const GraphNodeSchema = z.discriminatedUnion("kind", [
  ModuleNodeSchema,
  FileNodeSchema,
  SymbolNodeSchema,
  HunkNodeSchema,
  ExternalRefNodeSchema
]);

// --- Edge ---
export const EdgeSchema = z.object({
  id: z.string(),
  type: EdgeTypeSchema,
  source_id: z.string(),
  target_id: z.string(),
  confidence: ConfidenceSchema.default("exact"),
  change_state: ChangeStateSchema.default("unchanged"),
  note: z.string().nullable().optional()
});

// --- Graph Root & Metadata ---
export const PRMetadataSchema = z.object({
  url: z.string(),
  repo: z.string(),
  number: z.number().min(1),
  title: z.string(),
  author: z.string(),
  base_ref: z.string(),
  head_ref: z.string(),
  base_sha: z.string().min(7),
  head_sha: z.string().min(7),
  additions: z.number().min(0),
  deletions: z.number().min(0),
  changed_files: z.number().min(0)
});

export const DiagnosticSchema = z.object({
  level: z.enum(["info", "warn", "error"]),
  code: z.string(),
  message: z.string(),
  related_node_ids: z.array(z.string()).optional()
});

export const PRImpactGraphSchema = z.object({
  schema_version: z.string(),
  generated_at: z.string(),
  generator: z.string(),
  pr: PRMetadataSchema,
  nodes: z.array(GraphNodeSchema),
  edges: z.array(EdgeSchema),
  diagnostics: z.array(DiagnosticSchema).optional(),
  llm_enrichment_used: z.boolean().default(false).optional()
});

// --- Inferred Types ---
export type PRImpactGraph = z.infer<typeof PRImpactGraphSchema>;
export type GraphNodePayload = z.infer<typeof GraphNodeSchema>;
export type GraphEdgePayload = z.infer<typeof EdgeSchema>;
export type PRMetadata = z.infer<typeof PRMetadataSchema>;
export type ChangeState = z.infer<typeof ChangeStateSchema>;
export type GraphDiagnostic = z.infer<typeof DiagnosticSchema>;

// --- UI Boundary Config Schemas ---
export const GraphStyleConfigSchema = z.object({
  changeStates: z.record(z.string(), z.object({
    borderColor: z.string(),
    backgroundColor: z.string(),
    textColor: z.string(),
    icon: z.string()
  })),
  kinds: z.record(z.string(), z.object({
    icon: z.string(),
    shape: z.string().optional()
  }))
});

export const GraphPromptsConfigSchema = z.object({
  changeStates: z.record(z.string(), z.object({
    initialPrompt: z.string(),
    questions: z.array(z.string())
  })),
  kinds: z.record(z.string(), z.object({
    initialPrompt: z.string(),
    questions: z.array(z.string())
  }))
});

export type GraphStyleConfig = z.infer<typeof GraphStyleConfigSchema>;
export type GraphPromptsConfig = z.infer<typeof GraphPromptsConfigSchema>;
