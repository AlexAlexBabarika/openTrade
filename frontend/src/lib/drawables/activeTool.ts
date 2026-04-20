// frontend/src/lib/drawables/activeTool.ts
/**
 * The active drawing tool. 'cursor' means no drawing; any other string must
 * match a registered tool's `type`.
 */
export type ActiveTool = 'cursor' | string;

export const CURSOR: ActiveTool = 'cursor';
