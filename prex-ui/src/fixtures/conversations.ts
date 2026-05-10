/** Scripted Copilot conversations matching the Hi-Fi prototype.
 *
 * Each entry is a list of "turns": a user message followed by an assistant
 * message that may emit one or more A2GUI tool calls. We render these as
 * lightweight static placeholders today (the real CopilotKit chat-loading
 * path will be wired when an agent runtime lands).
 */
import type {
  BlastRadiusInputT,
  ClassDiffInputT,
  CouplingMapInputT,
  DataFlowChainInputT,
  SequenceInputT,
  TreemapInputT,
} from "../a2gui/schemas";

export interface ToolCall {
  name: string;
  args:
    | { args: TreemapInputT }
    | { args: CouplingMapInputT }
    | { args: ClassDiffInputT }
    | { args: BlastRadiusInputT }
    | { args: DataFlowChainInputT }
    | { args: SequenceInputT };
}

export interface AssistantTurn {
  role: "assistant";
  text: string;
  tools?: ToolCall[];
  cites?: { kind: string; ref: string; derivation: string }[];
}

export interface UserTurn {
  role: "user";
  text: string;
}

export type Turn = UserTurn | AssistantTurn;

export const PR_SCOPE_FIXTURE: Turn[] = [
  {
    role: "user",
    text: "Anything sneaky here?",
  },
  {
    role: "assistant",
    text: "Yes — the new `min_csat_score` field on `EvaluatedSessionsFilter` is also reused by the unrelated **Export** endpoint via `service_pb2_grpc.AgentEvaluationServiceServicer.ExportEvaluatedSessions`. Adding the filter here silently extends Export, which the PR description does not mention.",
    tools: [
      {
        name: "render_coupling_map",
        args: {
          args: {
            title: "Hidden coupling: Filter ↔ Export",
            source: "graph.json#references",
            nodes: [
              { id: "filter", label: "EvaluatedSessionsFilter", sensitive: true },
              { id: "query", label: "QueryEvaluatedSessions", sensitive: false },
              { id: "export", label: "ExportEvaluatedSessions", sensitive: true },
            ],
            edges: [
              { from: "filter", to: "query", derivation: "ast", label: "uses" },
              { from: "filter", to: "export", derivation: "llm", label: "implicit reuse" },
            ],
          },
        },
      },
    ],
    cites: [
      { kind: "node", ref: "symbol:python.agent_evaluation.agent_evaluation.models.models.EvaluatedSessionsFilter", derivation: "ast" },
      {
        kind: "node",
        ref: "symbol:idl.gen.python.idl.services.agent_evaluation.v1.service_pb2_grpc.AgentEvaluationServiceServicer.ExportEvaluatedSessions",
        derivation: "ast",
      },
    ],
  },
  {
    role: "user",
    text: "Show me where the change is densest.",
  },
  {
    role: "assistant",
    text: "Repository SQL changes dominate. `repository.py` carries 3 hunks (the new joins + materialise paths) — the rest are field-only plumbing through models / mappers / controller. Generated proto files are collapsed.",
    tools: [
      {
        name: "render_treemap",
        args: {
          args: {
            title: "Change density · 8 files",
            source: "graph.json#nodes:file",
            files: [
              { path: "python/agent_evaluation/agent_evaluation/repository/repository.py", additions: 58, deletions: 9, hunkCount: 3, generated: false, sensitive: true },
              { path: "python/agent_evaluation/agent_evaluation/models/models.py", additions: 12, deletions: 1, hunkCount: 1, generated: false, sensitive: false },
              { path: "python/agent_evaluation/agent_evaluation/controller/controller.py", additions: 9, deletions: 0, hunkCount: 1, generated: false, sensitive: false },
              { path: "python/agent_evaluation/agent_evaluation/mappers/mappers.py", additions: 9, deletions: 5, hunkCount: 2, generated: false, sensitive: false },
              { path: "idl/gen/python/.../dto_pb2.py +4", additions: 33, deletions: 0, hunkCount: 4, generated: true, sensitive: false },
            ],
          },
        },
      },
    ],
    cites: [
      { kind: "external_doc", ref: "graph.json#nodes:file", derivation: "ast" },
    ],
  },
];

export const STEP_SCOPE_FIXTURE: Record<number, Turn[]> = {
  1: [
    {
      role: "user",
      text: "Walk me through this filter.",
    },
    {
      role: "assistant",
      text: "`EvaluatedSessionsFilter` gains one optional field `min_csat_score`. The downstream `service.py` apex caller picks it up via the existing pb-to-model mapper. The field also leaks into `Export` (see Hidden coupling).",
      tools: [
        {
          name: "render_class_diff",
          args: {
            args: {
              title: "EvaluatedSessionsFilter (before / after)",
              source: "graph.json#symbol:EvaluatedSessionsFilter",
              before: {
                name: "EvaluatedSessionsFilter",
                fields: [
                  { name: "session_ids", type: "list[str]", state: "unchanged" },
                  { name: "tag_names", type: "list[str]", state: "unchanged" },
                  { name: "human_verdict", type: "str | None", state: "unchanged" },
                ],
              },
              after: {
                name: "EvaluatedSessionsFilter",
                fields: [
                  { name: "session_ids", type: "list[str]", state: "unchanged" },
                  { name: "tag_names", type: "list[str]", state: "unchanged" },
                  { name: "human_verdict", type: "str | None", state: "unchanged" },
                  { name: "min_csat_score", type: "int | None", state: "added" },
                ],
              },
            },
          },
        },
        {
          name: "render_blast_radius",
          args: {
            args: {
              title: "1-hop blast radius of EvaluatedSessionsFilter",
              source: "graph.json",
              target: { id: "filter", label: "EvaluatedSessionsFilter", inferred: false },
              neighborhood: [
                { id: "svc", label: "service.py · QueryEvaluatedSessions", inferred: false },
                { id: "models_init", label: "models/__init__.py", inferred: false },
                { id: "export", label: "service_pb2_grpc · ExportEvaluatedSessions", inferred: true },
              ],
              edges: [
                { from: "filter", to: "svc", derivation: "crossref_text" },
                { from: "filter", to: "models_init", derivation: "crossref_text" },
                { from: "filter", to: "export", derivation: "llm" },
              ],
            },
          },
        },
      ],
      cites: [
        { kind: "node", ref: "symbol:...EvaluatedSessionsFilter", derivation: "ast" },
      ],
    },
  ],
};
