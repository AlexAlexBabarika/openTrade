// frontend/src/lib/drawables/index.ts
import { registerTool, getTool } from './registry';
import { BUNDLED_TOOLS } from './toolCatalog';
import { loadToolDefaults } from './toolDefaults';

export * from './types';
export type { BundledTool, BundledToolType } from './toolCatalog';
export { BUNDLED_TOOLS, isBundledToolType } from './toolCatalog';
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

function applyPersistedToolDefaults(): void {
  for (const bundled of BUNDLED_TOOLS) {
    const stored = loadToolDefaults(bundled.type);
    const tool = getTool(bundled.type);
    if (stored && tool) {
      tool.defaults.params = stored.params as typeof tool.defaults.params;
      tool.defaults.style = stored.style as typeof tool.defaults.style;
    }
  }
}

/** Idempotent. Call once from app bootstrap. */
export function ensureToolsRegistered(): void {
  if (registered) return;
  for (const tool of BUNDLED_TOOLS) {
    registerTool(tool);
  }
  applyPersistedToolDefaults();
  registered = true;
}

// Register as soon as this module loads so any importer (e.g. LeftToolbar
// before App's script runs) sees a full `listTools()` — import order in App
// loads LeftToolbar before `./lib/drawables`.
ensureToolsRegistered();
