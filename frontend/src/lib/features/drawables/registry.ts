// frontend/src/lib/drawables/registry.ts
import type { DrawableTool } from './types';
import { BUNDLED_TOOLS_BY_TYPE, type BundledToolType } from './toolCatalog';

/**
 * Heterogeneous `DrawableTool` registry (`AnyTool` for fakes and wide `compute`).
 * - `getTool` — runtime map. `getRegisteredBundledTool` — narrow bundled id + cast to catalog shape.
 * Catalog-only lookups: use `BUNDLED_TOOLS_BY_TYPE` from `toolCatalog`.
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

/** Bundled id → catalog-typed tool from the registry (cast; fakes under bundled ids break typing). */
export function getRegisteredBundledTool<T extends BundledToolType>(
  type: T,
): (typeof BUNDLED_TOOLS_BY_TYPE)[T] | undefined {
  return tools.get(type) as (typeof BUNDLED_TOOLS_BY_TYPE)[T] | undefined;
}

export function listTools(): AnyTool[] {
  return order.map(t => tools.get(t)!);
}

/** Test-only helper. Not exported from index.ts. */
export function _resetRegistry(): void {
  tools.clear();
  order.length = 0;
}
