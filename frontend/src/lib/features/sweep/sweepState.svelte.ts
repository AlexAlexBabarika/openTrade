/**
 * Sweep dashboard state: the param schema/form, the running sweep's progress, the
 * trials seen so far, and the best trial. Mirrors `BacktestState`'s runes shape.
 *
 * `run()` starts a sweep and polls until it reaches a terminal status. The client
 * and poll interval are injectable so tests can stub the network and poll with no
 * delay.
 */
import { httpSweepClient } from './sweepClient';
import type {
  ParamSchema,
  SweepClient,
  SweepFormValues,
  SweepProgress,
  TrialRow,
} from './types';

type Status = 'idle' | 'running' | 'done' | 'error' | 'cancelled';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export class SweepState {
  schema = $state<ParamSchema>({});
  status = $state<Status>('idle');
  total = $state(0);
  done = $state(0);
  trials = $state<TrialRow[]>([]);
  bestTrialId = $state<number | null>(null);
  error = $state<string | null>(null);
  sweepId = $state<string | null>(null);

  #client: SweepClient;
  #interval: number;

  constructor(client: SweepClient = httpSweepClient, pollIntervalMs = 1000) {
    this.#client = client;
    this.#interval = pollIntervalMs;
  }

  async loadSchema(code: string): Promise<void> {
    this.schema = await this.#client.schema(code);
  }

  async run(form: SweepFormValues): Promise<void> {
    this.status = 'running';
    this.error = null;
    this.trials = [];
    this.done = 0;
    this.bestTrialId = null;
    try {
      const { sweep_id } = await this.#client.start(form);
      this.sweepId = sweep_id;
      for (;;) {
        const p: SweepProgress = await this.#client.poll(sweep_id);
        this.#apply(p);
        if (p.status !== 'running') break;
        if (this.#interval > 0) await sleep(this.#interval);
      }
    } catch (err) {
      this.status = 'error';
      this.error = err instanceof Error ? err.message : 'Sweep failed';
    }
  }

  async cancel(): Promise<void> {
    if (this.sweepId) await this.#client.cancel(this.sweepId);
  }

  #apply(p: SweepProgress): void {
    this.status = p.status;
    this.total = p.total;
    this.done = p.done;
    this.trials = p.trials;
    this.bestTrialId = p.best_trial_id;
    this.error = p.error;
  }
}
