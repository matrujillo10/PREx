import type { Brief, Graph } from "./types";

async function fetchJson<T>(url: string, fallback?: () => Promise<T>): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`fetch ${url}: ${res.status}`);
    return (await res.json()) as T;
  } catch (err) {
    if (fallback) {
      console.warn(`API ${url} unreachable, using fixture.`, err);
      return fallback();
    }
    throw err;
  }
}

export async function fetchBrief(): Promise<Brief> {
  return fetchJson<Brief>("/api/brief", async () => {
    const mod = await import("../fixtures/pr-19858.brief.json");
    return mod.default as unknown as Brief;
  });
}

export async function fetchGraph(): Promise<Graph> {
  return fetchJson<Graph>("/api/graph", async () => {
    const mod = await import("../fixtures/pr-19858.graph.json");
    return mod.default as unknown as Graph;
  });
}
