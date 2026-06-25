import { runsClient, type RunsClient } from './runsClient';
import type { RunDiff } from './runTypes';

export class CompareState {
  a = $state<string | null>(null);
  b = $state<string | null>(null);
  diff = $state<RunDiff | null>(null);
  loading = $state(false);
  error = $state<string | null>(null);
  #client: RunsClient;

  constructor(client: RunsClient = runsClient) {
    this.#client = client;
  }

  async load(a: string, b: string): Promise<void> {
    this.a = a;
    this.b = b;
    this.loading = true;
    this.error = null;
    try {
      this.diff = await this.#client.compareRuns(a, b);
    } catch (e) {
      this.diff = null;
      this.error = e instanceof Error ? e.message : String(e);
    } finally {
      this.loading = false;
    }
  }

  setDiff(a: string, b: string, diff: RunDiff): void {
    this.a = a;
    this.b = b;
    this.diff = diff;
    this.error = null;
    this.loading = false;
  }
}

export const compareState = new CompareState();
