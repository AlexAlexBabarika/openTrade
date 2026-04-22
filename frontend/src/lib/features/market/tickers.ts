import { safeLocalStorageGet, safeLocalStorageSet } from '$lib/core/storage';
import type { SymbolProviders } from './symbols';

export enum TickerPriority {
  None = 'none',
  Ignore = 'ignore',
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical',
}

export type FlaggedPriority = Exclude<TickerPriority, TickerPriority.None>;

export enum TickerStance {
  None = 'none',
  Watch = 'watch',
  Hold = 'hold',
  Buy = 'buy',
  Sell = 'sell',
}

export type FlaggedStance = Exclude<TickerStance, TickerStance.None>;

export interface TrackedTicker {
  symbol: string;
  priority: TickerPriority;
  stance: TickerStance;
  /** Cached provider-support flags from the symbol directory. ``null`` means
   *  unlisted (user added an unknown symbol) — sidebar renders no badges. */
  providers?: SymbolProviders | null;
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

export const FLAGGED_PRIORITIES: readonly FlaggedPriority[] = [
  TickerPriority.Ignore,
  TickerPriority.Low,
  TickerPriority.Normal,
  TickerPriority.High,
  TickerPriority.Critical,
];

export const STANCE_COLOURS: Record<FlaggedStance, string> = {
  [TickerStance.Watch]: '#a78bfa',
  [TickerStance.Hold]: '#38bdf8',
  [TickerStance.Buy]: '#4ade80',
  [TickerStance.Sell]: '#fb7185',
};

export const STANCE_OPTIONS: readonly TickerStance[] = [
  TickerStance.None,
  TickerStance.Watch,
  TickerStance.Hold,
  TickerStance.Buy,
  TickerStance.Sell,
];

export const FLAGGED_STANCES: readonly FlaggedStance[] = [
  TickerStance.Watch,
  TickerStance.Hold,
  TickerStance.Buy,
  TickerStance.Sell,
];

function isFlaggedPriority(value: unknown): value is FlaggedPriority {
  return (
    typeof value === 'string' &&
    (FLAGGED_PRIORITIES as readonly string[]).includes(value)
  );
}

function isFlaggedStance(value: unknown): value is FlaggedStance {
  return (
    typeof value === 'string' &&
    (FLAGGED_STANCES as readonly string[]).includes(value)
  );
}

export function normalizeTicker(raw: unknown): TrackedTicker {
  const t = raw as Partial<TrackedTicker>;
  const stanceRaw = t.stance;
  const stance =
    typeof stanceRaw === 'string' &&
    (STANCE_OPTIONS as readonly string[]).includes(stanceRaw)
      ? (stanceRaw as TickerStance)
      : TickerStance.None;
  const priorityRaw = t.priority;
  const priority =
    typeof priorityRaw === 'string' &&
    (PRIORITY_OPTIONS as readonly string[]).includes(priorityRaw)
      ? (priorityRaw as TickerPriority)
      : TickerPriority.None;
  return {
    symbol: typeof t.symbol === 'string' ? t.symbol : '',
    priority,
    stance,
    providers: t.providers,
  };
}

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
const SELECTED_PRIORITY_STORAGE_KEY = 'opentrade:selectedPriority';
const SELECTED_STANCE_STORAGE_KEY = 'opentrade:selectedStance';

function isValidGroup(value: unknown): value is TickerGroup {
  if (!value || typeof value !== 'object') return false;
  const g = value as Partial<TickerGroup>;
  return typeof g.name === 'string' && Array.isArray(g.tickers);
}

/** Re-run validation/normalization on groups from the API. */
export function normalizeGroupsList(groups: TickerGroup[]): TickerGroup[] {
  return groups.map(g => ({
    ...g,
    tickers: g.tickers.map(normalizeTicker),
  }));
}

export function isDefaultTickerWorkspaceState(
  groups: TickerGroup[],
  selectedGroupName: string,
  selectedPriority: FlaggedPriority | null,
  selectedStance: FlaggedStance | null,
): boolean {
  if (groups.length !== 1) return false;
  const g0 = groups[0];
  if (g0.name !== 'All' || g0.tickers.length !== 0) return false;
  if (selectedGroupName !== 'All') return false;
  if (selectedPriority !== null || selectedStance !== null) return false;
  return true;
}

export function clearTickerLocalStorage(): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.removeItem(GROUPS_STORAGE_KEY);
    localStorage.removeItem(SELECTED_GROUP_STORAGE_KEY);
    localStorage.removeItem(SELECTED_PRIORITY_STORAGE_KEY);
    localStorage.removeItem(SELECTED_STANCE_STORAGE_KEY);
  } catch (e) {
    console.warn('[opentrade] Failed to clear ticker local storage', e);
  }
}

export function loadGroupsFromStorage(): TickerGroup[] {
  const groups = safeLocalStorageGet<unknown>(GROUPS_STORAGE_KEY);
  if (
    !Array.isArray(groups) ||
    groups.length === 0 ||
    !groups.every(isValidGroup)
  ) {
    return [{ name: 'All', tickers: [] }];
  }
  return (groups as TickerGroup[]).map(g => ({
    ...g,
    tickers: g.tickers.map(normalizeTicker),
  }));
}

export function persistGroups(groups: TickerGroup[]): void {
  safeLocalStorageSet(GROUPS_STORAGE_KEY, groups);
}

/** Pick the active group name from storage, or fall back to the first group. */
export function loadSelectedGroupName(groups: TickerGroup[]): string {
  const stored = safeLocalStorageGet<string>(SELECTED_GROUP_STORAGE_KEY);
  if (typeof stored === 'string' && groups.some(g => g.name === stored)) {
    return stored;
  }
  return groups[0].name;
}

/** Use a known selection (e.g. from the server) without reading localStorage. */
export function resolveSelectedGroupName(
  groups: TickerGroup[],
  preferred: string,
): string {
  if (groups.some(g => g.name === preferred)) return preferred;
  return groups[0].name;
}

export function persistSelectedGroupName(name: string): void {
  safeLocalStorageSet(SELECTED_GROUP_STORAGE_KEY, name);
}

export function loadSelectedPriority(): FlaggedPriority | null {
  const stored = safeLocalStorageGet<unknown>(SELECTED_PRIORITY_STORAGE_KEY);
  return isFlaggedPriority(stored) ? stored : null;
}

export function persistSelectedPriority(
  priority: FlaggedPriority | null,
): void {
  safeLocalStorageSet(SELECTED_PRIORITY_STORAGE_KEY, priority);
}

export function loadSelectedStance(): FlaggedStance | null {
  const stored = safeLocalStorageGet<unknown>(SELECTED_STANCE_STORAGE_KEY);
  return isFlaggedStance(stored) ? stored : null;
}

export function persistSelectedStance(stance: FlaggedStance | null): void {
  safeLocalStorageSet(SELECTED_STANCE_STORAGE_KEY, stance);
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
  providers: SymbolProviders | null = null,
): TickerGroup[] {
  const ticker: TrackedTicker = {
    symbol,
    priority: TickerPriority.None,
    stance: TickerStance.None,
    providers,
  };
  return updateGroup(groups, groupName, g =>
    g.tickers.some(t => t.symbol === symbol)
      ? g
      : { ...g, tickers: [...g.tickers, ticker] },
  );
}

export function setTickerProvidersEverywhere(
  groups: TickerGroup[],
  symbol: string,
  providers: SymbolProviders,
): TickerGroup[] {
  return groups.map(g => ({
    ...g,
    tickers: g.tickers.map(t =>
      t.symbol === symbol ? { ...t, providers } : t,
    ),
  }));
}

export function findTickerProviders(
  groups: TickerGroup[],
  symbol: string,
): SymbolProviders | null {
  for (const g of groups) {
    for (const t of g.tickers) {
      if (t.symbol === symbol) return t.providers ?? null;
    }
  }
  return null;
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

export function collectTickersByPriority(
  groups: TickerGroup[],
  priority: FlaggedPriority,
): TrackedTicker[] {
  const seen = new Set<string>();
  const out: TrackedTicker[] = [];
  for (const g of groups) {
    for (const t of g.tickers) {
      if (t.priority === priority && !seen.has(t.symbol)) {
        seen.add(t.symbol);
        out.push({ symbol: t.symbol, priority, stance: t.stance });
      }
    }
  }
  return out;
}

export function priorityCounts(
  groups: TickerGroup[],
): Record<FlaggedPriority, number> {
  const seen: Record<FlaggedPriority, Set<string>> = {
    [TickerPriority.Ignore]: new Set(),
    [TickerPriority.Low]: new Set(),
    [TickerPriority.Normal]: new Set(),
    [TickerPriority.High]: new Set(),
    [TickerPriority.Critical]: new Set(),
  };
  for (const g of groups) {
    for (const t of g.tickers) {
      if (t.priority !== TickerPriority.None) {
        seen[t.priority as FlaggedPriority].add(t.symbol);
      }
    }
  }
  return {
    [TickerPriority.Ignore]: seen[TickerPriority.Ignore].size,
    [TickerPriority.Low]: seen[TickerPriority.Low].size,
    [TickerPriority.Normal]: seen[TickerPriority.Normal].size,
    [TickerPriority.High]: seen[TickerPriority.High].size,
    [TickerPriority.Critical]: seen[TickerPriority.Critical].size,
  };
}

export function setTickerStance(
  groups: TickerGroup[],
  groupName: string,
  symbol: string,
  stance: TickerStance,
): TickerGroup[] {
  return updateGroup(groups, groupName, g => ({
    ...g,
    tickers: g.tickers.map(t => (t.symbol === symbol ? { ...t, stance } : t)),
  }));
}

export function collectTickersByStance(
  groups: TickerGroup[],
  stance: FlaggedStance,
): TrackedTicker[] {
  const seen = new Set<string>();
  const out: TrackedTicker[] = [];
  for (const g of groups) {
    for (const t of g.tickers) {
      if (t.stance === stance && !seen.has(t.symbol)) {
        seen.add(t.symbol);
        out.push({ symbol: t.symbol, priority: t.priority, stance });
      }
    }
  }
  return out;
}

export function stanceCounts(
  groups: TickerGroup[],
): Record<FlaggedStance, number> {
  const seen: Record<FlaggedStance, Set<string>> = {
    [TickerStance.Watch]: new Set(),
    [TickerStance.Hold]: new Set(),
    [TickerStance.Buy]: new Set(),
    [TickerStance.Sell]: new Set(),
  };
  for (const g of groups) {
    for (const t of g.tickers) {
      if (t.stance !== TickerStance.None) {
        seen[t.stance as FlaggedStance].add(t.symbol);
      }
    }
  }
  return {
    [TickerStance.Watch]: seen[TickerStance.Watch].size,
    [TickerStance.Hold]: seen[TickerStance.Hold].size,
    [TickerStance.Buy]: seen[TickerStance.Buy].size,
    [TickerStance.Sell]: seen[TickerStance.Sell].size,
  };
}

export function setStanceEverywhere(
  groups: TickerGroup[],
  symbol: string,
  stance: TickerStance,
): TickerGroup[] {
  return groups.map(g => ({
    ...g,
    tickers: g.tickers.map(t => (t.symbol === symbol ? { ...t, stance } : t)),
  }));
}

export function setPriorityEverywhere(
  groups: TickerGroup[],
  symbol: string,
  priority: TickerPriority,
): TickerGroup[] {
  return groups.map(g => ({
    ...g,
    tickers: g.tickers.map(t => (t.symbol === symbol ? { ...t, priority } : t)),
  }));
}

export function removeTickerEverywhere(
  groups: TickerGroup[],
  symbol: string,
): TickerGroup[] {
  return groups.map(g => ({
    ...g,
    tickers: g.tickers.filter(t => t.symbol !== symbol),
  }));
}

export interface PriorityConflict {
  symbol: string;
  existingPriority: FlaggedPriority;
  groups: string[];
}

export function findPriorityConflict(
  groups: TickerGroup[],
  symbol: string,
  desired: TickerPriority,
  excludeGroup: string,
): PriorityConflict | null {
  if (desired === TickerPriority.None) return null;
  let existing: FlaggedPriority | null = null;
  const conflictingGroups: string[] = [];
  for (const g of groups) {
    if (g.name === excludeGroup) continue;
    for (const t of g.tickers) {
      if (t.symbol !== symbol) continue;
      if (t.priority !== TickerPriority.None && t.priority !== desired) {
        if (existing === null) existing = t.priority as FlaggedPriority;
        if (t.priority === existing) conflictingGroups.push(g.name);
      }
    }
  }
  if (existing === null) return null;
  return { symbol, existingPriority: existing, groups: conflictingGroups };
}

export interface StanceConflict {
  symbol: string;
  existingStance: FlaggedStance;
  groups: string[];
}

export function findStanceConflict(
  groups: TickerGroup[],
  symbol: string,
  desired: TickerStance,
  excludeGroup: string,
): StanceConflict | null {
  if (desired === TickerStance.None) return null;
  let existing: FlaggedStance | null = null;
  const conflictingGroups: string[] = [];
  for (const g of groups) {
    if (g.name === excludeGroup) continue;
    for (const t of g.tickers) {
      if (t.symbol !== symbol) continue;
      if (t.stance !== TickerStance.None && t.stance !== desired) {
        if (existing === null) existing = t.stance as FlaggedStance;
        if (t.stance === existing) conflictingGroups.push(g.name);
      }
    }
  }
  if (existing === null) return null;
  return { symbol, existingStance: existing, groups: conflictingGroups };
}
