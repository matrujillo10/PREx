import { serve } from "@hono/node-server";
import { cors } from "hono/cors";
import {
  CopilotRuntime,
  createCopilotEndpoint,
} from "@copilotkit/runtime/v2";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";

const agent = new LangGraphAgent({
  deploymentUrl:
    process.env.LANGGRAPH_DEPLOYMENT_URL ?? "http://localhost:8133",
  graphId: "default",
  langsmithApiKey: process.env.LANGSMITH_API_KEY ?? "",
  assistantConfig: {
    recursion_limit: Number(process.env.LANGGRAPH_RECURSION_LIMIT ?? 60),
  },
});

const app = createCopilotEndpoint({
  basePath: "/api/copilotkit",
  runtime: new CopilotRuntime({
    identifyUser: () => ({ id: "default", name: "PREx User" }),
    licenseToken: process.env.COPILOTKIT_LICENSE_TOKEN,
    agents: { default: agent },
    openGenerativeUI: true,
  }),
});

// Allow the Next.js dev origin to call this BFF directly so SSE streams
// bypass the Next rewrite (which buffers under turbopack). FRONTEND_ORIGIN
// must be set when running outside http://localhost:3010.
app.use(
  "/api/copilotkit/*",
  cors({
    origin: process.env.FRONTEND_ORIGIN ?? "http://localhost:3010",
    credentials: true,
    allowMethods: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization", "X-CopilotKit-Runtime-Client-GQL-Version"],
  }),
);

// Rewrite known 5xx error bodies into structured `{ error, hint, command }`
// payloads the UI can render as actionable toasts. Conservative matching —
// we only remap when we can identify the failure from the body, so unknown
// 5xx errors fall through unchanged.
app.use("*", async (c, next) => {
  await next();
  const status = c.res.status;
  if (status < 500 || status > 599) return;
  const cloned = c.res.clone();
  const ctype = cloned.headers.get("content-type") || "";
  if (!ctype.includes("json") && !ctype.includes("text")) return;
  let body: string;
  try {
    body = await cloned.text();
  } catch {
    return;
  }
  const isThreadFkey =
    body.includes("threads_user_id_fkey") ||
    (body.includes("Failed to initialize thread") &&
      body.includes("user_id"));
  if (isThreadFkey) {
    const remapped = {
      error: "Postgres user seed missing",
      hint: "Run `npm run seed` to seed the default user, then retry.",
      command: "npm run seed",
    };
    c.res = new Response(JSON.stringify(remapped), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
    return;
  }

  // AgentThreadLockedError: a prior run errored mid-stream and the LangGraph
  // SDK's per-thread lock didn't release. The thread is unrecoverable; the
  // hint tells the user to start a new conversation.
  const isThreadLocked =
    body.includes("AgentThreadLockedError") ||
    /Thread\s+[0-9a-f-]{36}\s+is locked/i.test(body);
  if (isThreadLocked) {
    const remapped = {
      error: "Thread is locked",
      hint:
        "A previous turn errored mid-stream and didn't release the run " +
        "lock. Start a new conversation (sidebar → +) to continue.",
      command: "new-thread",
    };
    c.res = new Response(JSON.stringify(remapped), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
    return;
  }
});

const port = Number(process.env.PORT) || 4000;

serve({ fetch: app.fetch, port }, () => {
  console.log(`BFF ready at http://localhost:${port}`);
});
