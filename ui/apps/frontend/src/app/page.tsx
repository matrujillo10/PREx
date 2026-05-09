import { loadGraphStyleConfig, loadGraphPromptsConfig } from "../config";
import { GraphPageClient } from "./GraphPageClient";

export default async function HomePage() {
  const styleConfig = loadGraphStyleConfig();
  const promptsConfig = loadGraphPromptsConfig();

  return (
    <div className="w-full h-screen bg-gray-50 flex flex-col">
      <header className="px-6 py-4 bg-white border-b shadow-sm z-10 flex items-center justify-between">
        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-500 to-blue-600">
          Agentic Graph Diff Viewer
        </h1>
      </header>
      <main className="flex-1 relative">
        <GraphPageClient initialStyleConfig={styleConfig} initialPromptsConfig={promptsConfig} />
      </main>
    </div>
  );
}
