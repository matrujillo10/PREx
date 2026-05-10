/** Registers the six A2GUI diagram components as CopilotKit frontend tools.
 *
 * Each tool is currently set to `available: "disabled"`. That keeps the tool
 * registered (so its `render` function fires when a synthesized assistant
 * message includes a tool call with this name) but prevents a real backend
 * agent from invoking it before we wire one up.
 *
 * Once the host LLM lands, flip `available: "enabled"` and consider switching
 * to `useFrontendTool` (which takes a Zod schema directly via its `parameters`
 * field). Today's `useCopilotAction` expects a plain Parameter[] descriptor
 * list, so we pass a single `args: object` blob and rely on the React
 * components' typed props to validate at the render boundary.
 */
import { useCopilotAction } from "@copilotkit/react-core";

import type {
  BlastRadiusInputT,
  ClassDiffInputT,
  CouplingMapInputT,
  DataFlowChainInputT,
  SequenceInputT,
  TreemapInputT,
} from "./schemas";
import { BlastRadius } from "./BlastRadius";
import { ClassDiff } from "./ClassDiff";
import { CouplingMap } from "./CouplingMap";
import { DataFlowChain } from "./DataFlowChain";
import { Sequence } from "./Sequence";
import { Treemap } from "./Treemap";

// Parameter[] from CopilotKit isn't exported in this version, so we use a
// minimal descriptor and rely on the React component's typed props for
// validation at the render boundary.
const PARAMS = [
  {
    name: "args",
    type: "object",
    description: "Validated A2GUI input shape (see schemas.ts).",
    required: true,
  },
] as Array<{
  name: string;
  type: "object";
  description: string;
  required: boolean;
}>;

/**
 * Mount this once inside <CopilotKit>. It registers all six diagrams so that
 * any assistant message containing a matching tool_call renders the diagram.
 */
export function RegisterA2GuiTools() {
  useCopilotAction({
    name: "render_treemap",
    description: "Render a treemap of changed files with size + sensitivity coding.",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: TreemapInputT } | undefined)?.args;
      return a ? <Treemap {...a} /> : <span>(awaiting args)</span>;
    },
  });
  useCopilotAction({
    name: "render_coupling_map",
    description: "Render a coupling map of related symbols/files; LLM-inferred edges are dashed accent.",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: CouplingMapInputT } | undefined)?.args;
      return a ? <CouplingMap {...a} /> : <span>(awaiting args)</span>;
    },
  });
  useCopilotAction({
    name: "render_class_diff",
    description: "Render a before/after class shape with added/removed fields.",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: ClassDiffInputT } | undefined)?.args;
      return a ? <ClassDiff {...a} /> : <span>(awaiting args)</span>;
    },
  });
  useCopilotAction({
    name: "render_blast_radius",
    description: "Render a 1-hop blast-radius around a target symbol; inferred edges dashed.",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: BlastRadiusInputT } | undefined)?.args;
      return a ? <BlastRadius {...a} /> : <span>(awaiting args)</span>;
    },
  });
  useCopilotAction({
    name: "render_data_flow_chain",
    description: "Render a horizontal data-flow chain of cards joined by arrows.",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: DataFlowChainInputT } | undefined)?.args;
      return a ? <DataFlowChain {...a} /> : <span>(awaiting args)</span>;
    },
  });
  useCopilotAction({
    name: "render_sequence",
    description: "Render a sequence diagram of actor lifelines + messages (sync/reply/sql).",
    parameters: PARAMS,
    available: "disabled",
    render: (props) => {
      const a = (props.args as { args: SequenceInputT } | undefined)?.args;
      return a ? <Sequence {...a} /> : <span>(awaiting args)</span>;
    },
  });
  return null;
}
