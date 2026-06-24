import type { EquityOverlay } from './runTypes';

export function truncateRunId(id: string, n = 8): string {
  return id.length > n ? `${id.slice(0, n)}…` : id;
}

export function formatDelta(delta: number | null): string {
  if (delta === null || Number.isNaN(delta)) return '—';
  const s = String(delta);
  return delta >= 0 ? `+${s}` : s;
}

export interface LineSpec {
  data: { t: number; value: number }[];
  color: string;
  lineWidth?: number;
}

export function equityToLines(
  overlay: EquityOverlay,
  colorA: string,
  colorB: string,
): LineSpec[] {
  return [
    { data: overlay.a, color: colorA },
    { data: overlay.b, color: colorB },
  ];
}
