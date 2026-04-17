import { safeLocalStorageGet, safeLocalStorageSet } from './storage';

export enum TickerPriority {
  Ignore = 'ignore',
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical',
}

export interface TrackedTicker {
  symbol: string;
  priority: TickerPriority;
}

export const PRIORITY_COLOURS: Record<TickerPriority, string> = {
  [TickerPriority.Ignore]: '#6b7280',
  [TickerPriority.Low]: '#60a5fa',
  [TickerPriority.Normal]: '#22c55e',
  [TickerPriority.High]: '#f59e0b',
  [TickerPriority.Critical]: '#ef4444',
};

export function getPriorityColour(priority: TickerPriority): string {
  return PRIORITY_COLOURS[priority];
}

export interface TickerGroup {
  name: string;
  tickers: TrackedTicker[];
}

const GROUPS_STORAGE_KEY = 'opentrade:groups';
const SELECTED_GROUP_STORAGE_KEY = 'opentrade:selectedGroup';

function isValidGroup(value: unknown): value is TickerGroup {
  if (!value || typeof value !== 'object') return false;
  const g = value as Partial<TickerGroup>;
  return typeof g.name === 'string' && Array.isArray(g.tickers);
}

export function loadGroupsFromStorage(): TickerGroup[] {
  const raw = safeLocalStorageGet<unknown>(GROUPS_STORAGE_KEY);
  if (!Array.isArray(raw) || raw.length === 0 || !raw.every(isValidGroup)) {
    return [{ name: 'All', tickers: [] }];
  }
  return raw;
}

export function persistGroups(groups: TickerGroup[]): void {
  safeLocalStorageSet(GROUPS_STORAGE_KEY, groups);
}

export function loadSelectedGroupName(groups: TickerGroup[]): string {
  const stored = safeLocalStorageGet<string>(SELECTED_GROUP_STORAGE_KEY);
  if (typeof stored === 'string' && groups.some(g => g.name === stored)) {
    return stored;
  }
  return groups[0].name;
}

export function persistSelectedGroupName(name: string): void {
  safeLocalStorageSet(SELECTED_GROUP_STORAGE_KEY, name);
}

export function uniqueDuplicateName(
  groups: TickerGroup[],
  base: string,
): string {
  const taken = new Set(groups.map(g => g.name));
  const candidate = `${base} copy`;
  if (!taken.has(candidate)) return candidate;
  let n = 2;
  while (taken.has(`${candidate} ${n}`)) n++;
  return `${candidate} ${n}`;
}

export function updateGroup(
  groups: TickerGroup[],
  index: number,
  patch: Partial<TickerGroup>,
): TickerGroup[] {
  return groups.map((g, i) => (i === index ? { ...g, ...patch } : g));
}
