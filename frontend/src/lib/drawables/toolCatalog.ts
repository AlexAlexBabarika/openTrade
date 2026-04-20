// frontend/src/lib/drawables/toolCatalog.ts
import { rulerTool } from './tools/ruler/tool';
import { avpTool } from './tools/volume-profile/avp/tool';

/**
 * Canonical list of tools shipped with the app (registration order = toolbar order).
 * Use this for registration loops instead of repeating imports in `index.ts`.
 */
export const BUNDLED_TOOLS = [rulerTool, avpTool] as const;

/** Narrow tool instance type for bundled tools (document-only; narrows at catalog boundary). */
export type BundledTool = (typeof BUNDLED_TOOLS)[number];

export type BundledToolType = BundledTool['type'];

export function isBundledToolType(type: string): type is BundledToolType {
  return (BUNDLED_TOOLS as readonly { type: string }[]).some(
    t => t.type === type,
  );
}
