import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("PREx UI error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            margin: "32px auto",
            maxWidth: 880,
            padding: 22,
            background: "var(--surface)",
            border: "1px solid var(--accent)",
            borderRadius: 8,
            color: "var(--ink-2)",
            fontFamily: "var(--mono)",
            fontSize: 12,
            lineHeight: 1.5,
            whiteSpace: "pre-wrap",
          }}
        >
          <h2 style={{ marginTop: 0, color: "var(--accent)", fontSize: 14 }}>
            ⚠ PREx UI failed to render
          </h2>
          <div>{String(this.state.error?.message ?? this.state.error)}</div>
          {this.state.error?.stack && (
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: "pointer", color: "var(--muted)" }}>
                stack
              </summary>
              <pre style={{ marginTop: 8, fontSize: 11, color: "var(--muted)" }}>
                {this.state.error.stack}
              </pre>
            </details>
          )}
          <p style={{ color: "var(--muted)", marginTop: 16 }}>
            Hard refresh (cmd+shift+R) often fixes stale-bundle errors after a
            rebuild. If not, check the browser devtools console for details.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
