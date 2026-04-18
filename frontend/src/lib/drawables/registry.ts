// frontend/src/lib/drawables/registry.ts
import type { DrawableTool } from './types';

// Registry is heterogeneous — each tool narrows <Geo,Params,Style,Data> to its
// own types. A typed registry would fight Svelte's invariant Component<Props>.
// Tool-specific typing lives in each tool module's exported `*Drawable` alias.
type AnyTool = DrawableTool<any, any, any, any>;

const tools = new Map<string, AnyTool>();
const order: string[] = [];

export function registerTool(tool: AnyTool): void {
  if (tools.has(tool.type)) {
    throw new Error(`Drawable tool '${tool.type}' is already registered`);
  }
  tools.set(tool.type, tool);
  order.push(tool.type);
}

export function getTool(type: string): AnyTool | undefined {
  return tools.get(type);
}

export function listTools(): AnyTool[] {
  return order.map(t => tools.get(t)!);
}

/** Test-only helper. Not exported from index.ts. */
export function _resetRegistry(): void {
  tools.clear();
  order.length = 0;
}
