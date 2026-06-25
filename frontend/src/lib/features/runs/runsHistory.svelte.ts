export interface RunHistoryEntry {
  run_id: string;
  kind: 'single' | 'portfolio';
  label: string;
  created_at: string;
}

export const MAX_RUNS = 50;
export const HISTORY_KEY = 'opentrade.runs.history';

function safeStorage(s?: Storage): Storage | null {
  if (s) return s;
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null;
  } catch {
    return null;
  }
}

export class RunsHistory {
  entries = $state<RunHistoryEntry[]>([]);
  #storage: Storage | null;

  constructor(storage?: Storage) {
    this.#storage = safeStorage(storage);
    this.#load();
  }

  #load(): void {
    try {
      const raw = this.#storage?.getItem(HISTORY_KEY);
      if (raw) this.entries = JSON.parse(raw) as RunHistoryEntry[];
    } catch {
      this.entries = [];
    }
  }

  #persist(): void {
    try {
      this.#storage?.setItem(HISTORY_KEY, JSON.stringify(this.entries));
    } catch {
      /* in-memory only */
    }
  }

  record(entry: RunHistoryEntry): void {
    this.entries = [
      entry,
      ...this.entries.filter(e => e.run_id !== entry.run_id),
    ].slice(0, MAX_RUNS);
    this.#persist();
  }

  remove(run_id: string): void {
    this.entries = this.entries.filter(e => e.run_id !== run_id);
    this.#persist();
  }
}

export const runsHistory = new RunsHistory();
