export const POSITION_LONG_TYPE = 'position-long' as const;
export const POSITION_SHORT_TYPE = 'position-short' as const;

export const POSITION_TOOL_TYPES = [
  POSITION_LONG_TYPE,
  POSITION_SHORT_TYPE,
] as const;

export type PositionToolType = (typeof POSITION_TOOL_TYPES)[number];

export function isPositionToolType(type: string): type is PositionToolType {
  return (POSITION_TOOL_TYPES as readonly string[]).includes(type);
}
