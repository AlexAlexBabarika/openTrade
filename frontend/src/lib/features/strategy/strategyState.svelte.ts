/**
 * Strategy editor state: the live strategy source (`draftCode`) that feeds both
 * the single-run backtest path and the sweep panel, plus saved-strategy CRUD.
 * Runes-based, mirroring `IndicatorState`; the HTTP client is injectable so
 * tests stub the network, mirroring `SweepState`.
 */
import { BacktestState } from '$lib/features/backtest/backtestState.svelte';
import {
  httpStrategyClient,
  type BacktestRunParams,
  type StrategyClient,
  type StrategyInfo,
} from './strategies';

export const SEED_CODE = `params = {
    "fast": Int(5, 50, step=5),
    "slow": Int(20, 200, step=10),
}

def on_bar(ctx):
    if ctx.position.quantity == 0:
        ctx.buy(1)
`;

export type RunContext = Omit<BacktestRunParams, 'code'>;

export class StrategyState {
  scripts = $state<StrategyInfo[]>([]);
  loading = $state(false);
  loadError = $state<string | null>(null);

  activeId = $state<string | null>(null);
  draftName = $state('Untitled strategy');
  draftCode = $state(SEED_CODE);
  dirty = $state(false);

  isSaving = $state(false);
  saveError = $state<string | null>(null);

  /** Result of the latest `runBacktest()`, rendered by `BacktestPanel`. */
  backtest = $state<BacktestState | null>(null);
  isRunning = $state(false);
  runError = $state<string | null>(null);

  #client: StrategyClient;

  constructor(client: StrategyClient = httpStrategyClient) {
    this.#client = client;
  }

  active = $derived.by(() =>
    this.activeId
      ? (this.scripts.find(s => s.id === this.activeId) ?? null)
      : null,
  );

  async load(): Promise<void> {
    this.loading = true;
    this.loadError = null;
    try {
      this.scripts = await this.#client.list();
    } catch (err) {
      this.loadError =
        err instanceof Error ? err.message : 'Failed to load strategies';
    } finally {
      this.loading = false;
    }
  }

  newDraft(): void {
    this.activeId = null;
    this.draftName = 'Untitled strategy';
    this.draftCode = SEED_CODE;
    this.dirty = false;
    this.saveError = null;
  }

  select(id: string): void {
    const s = this.scripts.find(x => x.id === id);
    if (!s) return;
    this.activeId = id;
    this.draftName = s.name;
    this.draftCode = s.code;
    this.dirty = false;
    this.saveError = null;
  }

  setName(name: string): void {
    if (this.draftName === name) return;
    this.draftName = name;
    this.dirty = true;
  }

  setCode(code: string): void {
    if (this.draftCode === code) return;
    this.draftCode = code;
    this.dirty = true;
  }

  async save(): Promise<StrategyInfo | null> {
    const name = this.draftName.trim();
    if (!name) {
      this.saveError = 'Name is required';
      return null;
    }
    this.isSaving = true;
    this.saveError = null;
    try {
      let saved: StrategyInfo;
      if (this.activeId) {
        saved = await this.#client.update(this.activeId, {
          name,
          code: this.draftCode,
        });
      } else {
        saved = await this.#client.create(name, this.draftCode);
      }
      const idx = this.scripts.findIndex(s => s.id === saved.id);
      if (idx >= 0) this.scripts[idx] = saved;
      else this.scripts = [saved, ...this.scripts];
      this.activeId = saved.id;
      this.dirty = false;
      return saved;
    } catch (err) {
      this.saveError = err instanceof Error ? err.message : 'Failed to save';
      return null;
    } finally {
      this.isSaving = false;
    }
  }

  async remove(id: string): Promise<void> {
    await this.#client.remove(id);
    this.scripts = this.scripts.filter(s => s.id !== id);
    if (this.activeId === id) this.newDraft();
  }

  /**
   * Run the current draft through `POST /backtests/run` into a fresh
   * `BacktestState` (so `BacktestPanel` renders a real run, not the fixture).
   * A non-ok sandbox status is surfaced as `runError` with the run's stderr.
   */
  async runBacktest(ctx: RunContext): Promise<BacktestState> {
    const code = this.draftCode;
    this.isRunning = true;
    this.runError = null;
    const bt = new BacktestState(async () => {
      const res = await this.#client.runBacktest({ code, ...ctx });
      if (res.status !== 'ok') {
        throw new Error(res.stderr.trim() || `Backtest ${res.status}`);
      }
      return res;
    });
    this.backtest = bt;
    try {
      await bt.load();
    } finally {
      this.isRunning = false;
      this.runError = bt.error;
    }
    return bt;
  }
}
