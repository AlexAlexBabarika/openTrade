/**
 * Distinct, high-contrast colours used for comparison overlays.
 * Order is the assignment priority when picking the next unused colour.
 */
export const COMPARISON_PALETTE: readonly string[] = [
  '#FF9800',
  '#E91E63',
  '#00BCD4',
  '#8BC34A',
  '#FFEB3B',
  '#2196F3',
  '#9C27B0',
  '#F44336',
];

/**
 * Pick the first palette colour not present in `used` (case-insensitive).
 * If all palette colours are taken, cycle back to index 0.
 */
export function nextUnusedColor(used: readonly string[]): string {
  const set = new Set(used.map(c => c.toLowerCase()));
  for (const c of COMPARISON_PALETTE) {
    if (!set.has(c.toLowerCase())) return c;
  }
  return COMPARISON_PALETTE[0];
}
