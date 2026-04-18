// frontend/src/lib/drawables/index.ts
import { registerTool } from './registry';
import { rulerTool } from './tools/ruler/tool';

export * from './types';
export { drawables, createDrawablesStore } from './store.svelte';
export { loadAll, saveAll, DRAWABLES_STORAGE_KEY } from './persistence';
export { registerTool, getTool, listTools } from './registry';
export type { ActiveTool } from './activeTool';
export { CURSOR } from './activeTool';
export { buildCoordMap } from './coordMap';

let registered = false;

/** Idempotent. Call once from app bootstrap. */
export function ensureToolsRegistered(): void {
  if (registered) return;
  registerTool(rulerTool);
  registered = true;
}
