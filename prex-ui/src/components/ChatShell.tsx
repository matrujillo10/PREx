import { useEffect, useMemo, useRef, useState } from "react";

import { BlastRadius } from "../a2gui/BlastRadius";
import { ChecklistCard } from "../a2gui/ChecklistCard";
import { ClassDiff } from "../a2gui/ClassDiff";
import { CouplingMap } from "../a2gui/CouplingMap";
import { DataFlowChain } from "../a2gui/DataFlowChain";
import { PlanCard } from "../a2gui/PlanCard";
import { ReviewBriefCard } from "../a2gui/ReviewBriefCard";
import { Sequence } from "../a2gui/Sequence";
import { Treemap } from "../a2gui/Treemap";
import { useStore } from "../state/store";
import styles from "./ChatShell.module.css";

interface Props {
  scope: "pr" | `step:${number}`;
}

const RENDERERS: Record<string, (args: any) => JSX.Element> = {
  render_treemap: (a) => <Treemap {...a} />,
  render_coupling_map: (a) => <CouplingMap {...a} />,
  render_class_diff: (a) => <ClassDiff {...a} />,
  render_blast_radius: (a) => <BlastRadius {...a} />,
  render_data_flow_chain: (a) => <DataFlowChain {...a} />,
  render_sequence: (a) => <Sequence {...a} />,
  render_review_brief: (a) => <ReviewBriefCard {...a} />,
  render_review_plan: (a) => <PlanCard {...a} />,
  render_checklist: (a) => <ChecklistCard {...a} />,
};

interface ToolCall {
  id?: string | null;
  name: string;
  args: any;
}

interface Turn {
  role: "user" | "assistant";
  text: string;
  tools?: ToolCall[];
  error?: string;
}

/**
 * Inline chat region.
 *
 * Wired to the local /api/chat SSE endpoint, which proxies to Anthropic Claude
 * with the brief + condensed graph as context. Tool-use events from Claude
 * map 1:1 to our six A2GUI diagram components (treemap, coupling map, class
 * diff, blast radius, data flow chain, sequence).
 */
export function ChatShell({ scope }: Props) {
  const setScope = useStore((s) => s.setChatScope);
  useEffect(() => {
    setScope(scope);
  }, [scope, setScope]);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const greetedRef = useRef<string | null>(null);

  // Reset conversation when scope changes.
  useEffect(() => {
    abortRef.current?.abort();
    setTurns([]);
    setBusy(false);
    greetedRef.current = null;
  }, [scope]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // Auto-greet on first mount of a scope so the chat opens with the brief +
  // plan + checklist already rendered as A2GUI cards.
  useEffect(() => {
    if (greetedRef.current === scope) return;
    greetedRef.current = scope;
    sendInternal("__GREETING__");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  const send = async () => {
    const trimmed = draft.trim();
    if (!trimmed || busy) return;
    setDraft("");
    await sendInternal(trimmed);
  };

  const sendInternal = async (userText: string) => {
    if (busy) return;
    const isGreeting = userText === "__GREETING__";
    // For the silent greeting we still want the assistant turn to render, but
    // we skip showing the literal '__GREETING__' user bubble.
    const next: Turn[] = isGreeting
      ? [...turns]
      : [...turns, { role: "user", text: userText }];
    setTurns([...next, { role: "assistant", text: "" }]);
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const wireMessages = isGreeting
        ? [...next.map((t) => ({ role: t.role, content: t.text })), { role: "user", content: "__GREETING__" }]
        : next.map((t) => ({ role: t.role, content: t.text }));
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scope, messages: wireMessages }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`server replied ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const ev of events) {
          handleEvent(ev);
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setTurns((cur) => {
        const copy = [...cur];
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant") {
          copy[copy.length - 1] = { ...last, error: message };
        }
        return copy;
      });
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const handleEvent = (raw: string) => {
    const lines = raw.split("\n");
    let event = "";
    let data = "";
    for (const ln of lines) {
      if (ln.startsWith("event:")) event = ln.slice(6).trim();
      else if (ln.startsWith("data:")) data += ln.slice(5).trim();
    }
    if (!event) return;
    let payload: any = {};
    try {
      payload = JSON.parse(data || "{}");
    } catch {
      return;
    }
    setTurns((cur) => {
      const copy = [...cur];
      const idx = copy.length - 1;
      if (idx < 0 || copy[idx].role !== "assistant") return copy;
      const last = { ...copy[idx] };
      if (event === "text") {
        last.text = (last.text ?? "") + (payload.text ?? "");
      } else if (event === "tool") {
        last.tools = [
          ...(last.tools ?? []),
          { id: payload.id ?? null, name: payload.name, args: payload.args ?? {} },
        ];
      } else if (event === "error") {
        last.error = payload.message ?? "agent error";
      }
      copy[idx] = last;
      return copy;
    });
  };

  const placeholder = useMemo(
    () =>
      scope === "pr"
        ? "Ask about this PR…  e.g. 'anything sneaky?'  or 'show me where the change is densest'"
        : "Ask about this step…  e.g. 'walk me through this filter'",
    [scope],
  );

  return (
    <div className={styles.shell}>
      <div className={styles.label}>
        Copilot · {scope === "pr" ? "PR scope" : `step ${scope.split(":")[1]}`}
      </div>
      {turns.length === 0 && (
        <div className={styles.assistant}>
          <span style={{ fontStyle: "italic", color: "var(--muted)" }}>
            Ask anything about this PR. Claude has the brief + a condensed graph
            and may render diagrams (treemap, coupling map, class diff, blast
            radius, data flow chain, sequence) when they help.
          </span>
        </div>
      )}
      {turns.map((t, i) =>
        t.role === "user" ? (
          <div key={i} className={`${styles.turn} ${styles.user}`}>
            {t.text}
          </div>
        ) : (
          <AssistantBubble key={i} turn={t} />
        ),
      )}
      <div className={styles.composer}>
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          disabled={busy}
        />
        <button
          className={styles.secondary}
          type="button"
          onClick={() => setTurns([])}
          disabled={busy || turns.length === 0}
          title="Reset conversation"
        >
          reset
        </button>
        <button type="button" onClick={send} disabled={busy || !draft.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

function AssistantBubble({ turn }: { turn: Turn }) {
  return (
    <div className={styles.assistant}>
      {turn.text ? (
        <div
          className={styles.assistantText}
          dangerouslySetInnerHTML={{ __html: renderText(turn.text) }}
        />
      ) : turn.error ? null : (
        <div style={{ color: "var(--muted)", fontStyle: "italic" }}>…</div>
      )}
      {turn.tools?.map((tc, i) => {
        const renderer = RENDERERS[tc.name];
        if (!renderer) return null;
        try {
          return <div key={i}>{renderer(tc.args)}</div>;
        } catch (err) {
          return (
            <div key={i} style={{ color: "var(--accent)", fontFamily: "var(--mono)", fontSize: 11 }}>
              ⚠ failed to render {tc.name}: {String(err)}
            </div>
          );
        }
      })}
      {turn.error && (
        <div style={{ color: "var(--accent)", fontSize: 12 }}>⚠ {turn.error}</div>
      )}
    </div>
  );
}

function renderText(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}
