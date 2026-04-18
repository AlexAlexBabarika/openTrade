import { safeLocalStorageGet, safeLocalStorageSet } from './storage';

export type TickerNote = {
  id: string;
  symbol: string;
  title?: string;
  body: string;
  createdAt: number;
  updatedAt: number;
};

export type NotesBySymbol = Record<string, TickerNote[]>;

const NOTES_STORAGE_KEY = 'opentrade:notes';

function normalizeSymbol(s: string): string {
  return s.trim().toUpperCase();
}

function isValidNote(value: unknown): value is TickerNote {
  if (!value || typeof value !== 'object') return false;
  const n = value as Partial<TickerNote>;
  return (
    typeof n.id === 'string' &&
    typeof n.symbol === 'string' &&
    typeof n.body === 'string' &&
    typeof n.createdAt === 'number' &&
    typeof n.updatedAt === 'number' &&
    (n.title === undefined || typeof n.title === 'string')
  );
}

export function loadNotesFromStorage(): NotesBySymbol {
  const raw = safeLocalStorageGet<unknown>(NOTES_STORAGE_KEY);
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  const out: NotesBySymbol = {};
  for (const [sym, list] of Object.entries(raw as Record<string, unknown>)) {
    if (!Array.isArray(list)) continue;
    const valid = list.filter(isValidNote);
    if (valid.length > 0) out[normalizeSymbol(sym)] = valid;
  }
  return out;
}

export function persistNotes(notes: NotesBySymbol): void {
  safeLocalStorageSet(NOTES_STORAGE_KEY, notes);
}

export function notesForSymbol(
  notes: NotesBySymbol,
  symbol: string,
): TickerNote[] {
  const key = normalizeSymbol(symbol);
  const list = notes[key];
  if (!list) return [];
  return [...list].sort((a, b) => b.createdAt - a.createdAt);
}

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function addNote(
  notes: NotesBySymbol,
  symbol: string,
  body: string,
  title?: string,
): NotesBySymbol {
  const key = normalizeSymbol(symbol);
  const now = Date.now();
  const note: TickerNote = {
    id: newId(),
    symbol: key,
    body,
    createdAt: now,
    updatedAt: now,
  };
  if (title && title.trim()) note.title = title.trim();
  return { ...notes, [key]: [note, ...(notes[key] ?? [])] };
}

export function updateNote(
  notes: NotesBySymbol,
  id: string,
  patch: { title?: string; body: string },
): NotesBySymbol {
  const now = Date.now();
  const out: NotesBySymbol = {};
  for (const [sym, list] of Object.entries(notes)) {
    out[sym] = list.map(n => {
      if (n.id !== id) return n;
      const next: TickerNote = {
        ...n,
        body: patch.body,
        updatedAt: now,
      };
      const trimmed = patch.title?.trim();
      if (trimmed) next.title = trimmed;
      else delete next.title;
      return next;
    });
  }
  return out;
}

export function deleteNote(notes: NotesBySymbol, id: string): NotesBySymbol {
  const out: NotesBySymbol = {};
  for (const [sym, list] of Object.entries(notes)) {
    const filtered = list.filter(n => n.id !== id);
    if (filtered.length > 0) out[sym] = filtered;
  }
  return out;
}
