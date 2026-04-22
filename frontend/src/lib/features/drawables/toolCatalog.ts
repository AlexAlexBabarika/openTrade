// frontend/src/lib/drawables/toolCatalog.ts
import { rulerTool } from './tools/ruler/tool';
import { avpTool } from './tools/volume-profile/avp/tool';
import { positionLongTool, positionShortTool } from './tools/position/tool';

/** Shipped tools (order = toolbar). Used for registration loops in `index.ts`. */
export const BUNDLED_TOOLS = [
  rulerTool,
  avpTool,
  positionLongTool,
  positionShortTool,
] as const;

/** Narrow tool instance type for bundled tools (document-only; narrows at catalog boundary). */
export type BundledTool = (typeof BUNDLED_TOOLS)[number];

export type BundledToolType = BundledTool['type'];

/** Compile-time map for bundled tools (catalog-only; runtime uses `getTool` / registry). */
export const BUNDLED_TOOLS_BY_TYPE: Record<BundledToolType, BundledTool> = {
  [rulerTool.type]: rulerTool,
  [avpTool.type]: avpTool,
  [positionLongTool.type]: positionLongTool,
  [positionShortTool.type]: positionShortTool,
};

export function isBundledToolType(type: string): type is BundledToolType {
  return (BUNDLED_TOOLS as readonly { type: string }[]).some(
    t => t.type === type,
  );
}
