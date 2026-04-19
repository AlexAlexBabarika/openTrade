// frontend/src/lib/drawables/index.ts
import { registerTool, getTool } from './registry';
import { rulerTool } from './tools/ruler/tool';
import { avpTool } from './tools/volume-profile/avp/tool';
import { loadToolDefaults } from './toolDefaults';

export * from './types';
export { drawables, createDrawablesStore } from './store.svelte';
export { loadAll, saveAll, DRAWABLES_STORAGE_KEY } from './persistence';
export { registerTool, getTool, listTools } from './registry';
export { DEFAULT_POPUP_ACTIONS, resolvePopupActions } from './popupActions';
export {
  loadToolDefaults,
  saveToolDefaults,
  TOOL_DEFAULTS_STORAGE_KEY,
} from './toolDefaults';
export type { ActiveTool } from './activeTool';
export { CURSOR } from './activeTool';
export { buildCoordMap } from './coordMap';

let registered = false;

/** Idempotent. Call once from app bootstrap. */
export function ensureToolsRegistered(): void {
  if (registered) return;
  registerTool(rulerTool);
  registerTool(avpTool);
  // Apply persisted per-tool default overrides.
  for (const type of [rulerTool.type, avpTool.type]) {
    const stored = loadToolDefaults(type);
    const tool = getTool(type);
    if (stored && tool) {
      tool.defaults.params = stored.params as typeof tool.defaults.params;
      tool.defaults.style = stored.style as typeof tool.defaults.style;
    }
  }
  registered = true;
}
