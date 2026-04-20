// frontend/src/lib/drawables/registry.ts
import type { DrawableTool } from './types';
import { BUNDLED_TOOLS_BY_TYPE, type BundledToolType } from './toolCatalog';

/**
 * Registry is heterogeneous — each tool narrows Geo/Params/Style/Data. Values
 * are `AnyTool` so tests can register minimal fakes and Svelte `Component`
 * props stay ergonomic. For **bundled** tools, prefer `getBundledTool(type)` for
 * a `BundledTool` return type; `getTool` remains the generic lookup.
 */
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

export function getBundledTool<T extends BundledToolType>(
  type: T,
): (typeof BUNDLED_TOOLS_BY_TYPE)[T] | undefined {
  return BUNDLED_TOOLS_BY_TYPE[type];
}

export function listTools(): AnyTool[] {
  return order.map(t => tools.get(t)!);
}

/** Test-only helper. Not exported from index.ts. */
export function _resetRegistry(): void {
  tools.clear();
  order.length = 0;
}
