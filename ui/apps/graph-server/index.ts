import { serve } from "bun";
import { parseArgs } from "util";
import { readFileSync, existsSync } from "fs";

// Simple argument parsing, requiring --file
const { values } = parseArgs({
  args: Bun.argv,
  options: {
    file: {
      type: "string",
    },
    port: {
      type: "string",
      default: "8080",
    },
  },
  strict: true,
  allowPositionals: true,
});

if (!values.file) {
  console.error("❌ Error: --file argument is strictly required. Provide a valid path to a JSON graph structure.");
  process.exit(1);
}

if (!existsSync(values.file)) {
  console.error(`❌ Error: File not found at path: ${values.file}`);
  process.exit(1);
}

console.log(`✅ Loaded graph layout from: ${values.file}`);

// Basic Bun server
const port = parseInt(values.port as string, 10);
serve({
  port,
  async fetch(req) {
    const url = new URL(req.url);

    // Standard CORS headers
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (url.pathname === "/graph" && req.method === "GET") {
      try {
        const fileContent = readFileSync(values.file as string, "utf-8");
        // Ensure it's valid JSON before sending
        JSON.parse(fileContent); 
        return new Response(fileContent, {
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders,
          },
        });
      } catch (error: any) {
        return new Response(JSON.stringify({ error: "Failed to parse json file.", details: error?.message }), {
          status: 500,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      }
    }

    return new Response("Not Found", { status: 404 });
  },
});

console.log(`🚀 Ingestion server running at http://localhost:${port}`);
console.log(`➡️  Graph Endpoint: http://localhost:${port}/graph`);
