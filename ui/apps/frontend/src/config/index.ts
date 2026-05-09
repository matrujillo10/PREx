import * as fs from "fs";
import * as path from "path";
import { 
  GraphStyleConfigSchema, 
  GraphPromptsConfigSchema,
  GraphStyleConfig,
  GraphPromptsConfig 
} from "./graphConfigSchema";

export function loadGraphStyleConfig(): GraphStyleConfig {
  const filePath = path.join(process.cwd(), "src/config/graphStyleConfig.json");
  const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  return GraphStyleConfigSchema.parse(data);
}

export function loadGraphPromptsConfig(): GraphPromptsConfig {
  const filePath = path.join(process.cwd(), "src/config/graphPromptsConfig.json");
  const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  return GraphPromptsConfigSchema.parse(data);
}
