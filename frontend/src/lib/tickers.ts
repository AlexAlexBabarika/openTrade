import { safeLocalStorageGet, safeLocalStorageSet } from './storage';

export enum TickerPriority {
  None = 'none',
  Ignore = 'ignore',
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical',
}

export type FlaggedPriority = Exclude<TickerPriority, TickerPriority.None>;

export interface TrackedTicker {
  symbol: string;
  priority: TickerPriority;
}

export const PRIORITY_COLOURS: Record<FlaggedPriority, string> = {
  [TickerPriority.Ignore]: '#6b7280',
  [TickerPriority.Low]: '#60a5fa',
  [TickerPriority.Normal]: '#22c55e',
  [TickerPriority.High]: '#f59e0b',
  [TickerPriority.Critical]: '#ef4444',
};

export const PRIORITY_OPTIONS: readonly TickerPriority[] = [
  TickerPriority.None,
  TickerPriority.Ignore,
  TickerPriority.Low,
  TickerPriority.Normal,
  TickerPriority.High,
  TickerPriority.Critical,
];

export interface TickerGroup {
  name: string;
  tickers: TrackedTicker[];
}

export interface GroupActions {
  select: (name: string) => void;
  rename: () => void;
  duplicate: () => void;
  clear: () => void;
  add: () => void;
  delete: () => void;
}

const GROUPS_STORAGE_KEY = 'opentrade:groups';
const SELECTED_GROUP_STORAGE_KEY = 'opentrade:selectedGroup';
const PRIORITY_NONE_MIGRATION_KEY = 'opentrade:priorityNoneMigration.v1';

function isValidGroup(value: unknown): value is TickerGroup {
  if (!value || typeof value !== 'object') return false;
  const g = value as Partial<TickerGroup>;
  return typeof g.name === 'string' && Array.isArray(g.tickers);
}

// One-shot: pre-existing tickers defaulted to `Normal` back when that was the
// "no explicit priority" value. New default is `None`. Migrate once so legacy
// tickers don't suddenly show green flags; after this runs, explicit `Normal`
// selections made via the menu are preserved across reloads.
function migrateLegacyNormalToNone(groups: TickerGroup[]): TickerGroup[] {
  if (safeLocalStorageGet<boolean>(PRIORITY_NONE_MIGRATION_KEY) === true) {
    return groups;
  }
  const migrated = groups.map(g => ({
    ...g,
    tickers: g.tickers.map(t =>
      t.priority === TickerPriority.Normal
        ? { ...t, priority: TickerPriority.None }
        : t,
    ),
  }));
  safeLocalStorageSet(PRIORITY_NONE_MIGRATION_KEY, true);
  return migrated;
}

export function loadGroupsFromStorage(): TickerGroup[] {
  const raw = safeLocalStorageGet<unknown>(GROUPS_STORAGE_KEY);
  if (!Array.isArray(raw) || raw.length === 0 || !raw.every(isValidGroup)) {
    return [{ name: 'All', tickers: [] }];
  }
  return migrateLegacyNormalToNone(raw);
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

function uniqueDuplicateName(groups: TickerGroup[], base: string): string {
  const taken = new Set(groups.map(g => g.name));
  const candidate = `${base} copy`;
  if (!taken.has(candidate)) return candidate;
  let n = 2;
  while (taken.has(`${candidate} ${n}`)) n++;
  return `${candidate} ${n}`;
}

export function addGroup(groups: TickerGroup[], name: string): TickerGroup[] {
  return [...groups, { name, tickers: [] }];
}

export function renameGroup(
  groups: TickerGroup[],
  from: string,
  to: string,
): TickerGroup[] {
  return groups.map(g => (g.name === from ? { ...g, name: to } : g));
}

export function duplicateGroup(
  groups: TickerGroup[],
  source: string,
): { groups: TickerGroup[]; newName: string } | null {
  const src = groups.find(g => g.name === source);
  if (!src) return null;
  const newName = uniqueDuplicateName(groups, src.name);
  return {
    groups: [
      ...groups,
      { name: newName, tickers: src.tickers.map(t => ({ ...t })) },
    ],
    newName,
  };
}

export function deleteGroup(
  groups: TickerGroup[],
  target: string,
): TickerGroup[] | null {
  if (groups.length <= 1) return null;
  const next = groups.filter(g => g.name !== target);
  return next.length === groups.length ? null : next;
}

function updateGroup(
  groups: TickerGroup[],
  groupName: string,
  update: (g: TickerGroup) => TickerGroup,
): TickerGroup[] {
  return groups.map(g => (g.name === groupName ? update(g) : g));
}

export function clearGroup(
  groups: TickerGroup[],
  target: string,
): TickerGroup[] {
  return updateGroup(groups, target, g => ({ ...g, tickers: [] }));
}

export function addTickerToGroup(
  groups: TickerGroup[],
  groupName: string,
  symbol: string,
): TickerGroup[] {
  const ticker: TrackedTicker = { symbol, priority: TickerPriority.None };
  return updateGroup(groups, groupName, g =>
    g.tickers.some(t => t.symbol === symbol)
      ? g
      : { ...g, tickers: [...g.tickers, ticker] },
  );
}

export function removeTickerFromGroup(
  groups: TickerGroup[],
  groupName: string,
  symbol: string,
): TickerGroup[] {
  return updateGroup(groups, groupName, g => ({
    ...g,
    tickers: g.tickers.filter(t => t.symbol !== symbol),
  }));
}

export function setTickerPriority(
  groups: TickerGroup[],
  groupName: string,
  symbol: string,
  priority: TickerPriority,
): TickerGroup[] {
  return updateGroup(groups, groupName, g => ({
    ...g,
    tickers: g.tickers.map(t => (t.symbol === symbol ? { ...t, priority } : t)),
  }));
}
