/**
 * Portfolio backtest state: the universe symbol list built in the UI plus the
 * latest run of `POST /portfolio-backtests/run`. Runes-based, mirroring
 * `StrategyState`; the HTTP client is injectable so tests stub the network.
 */
import {
  httpPortfolioClient,
  type IngestReport,
  type PortfolioClient,
  type PortfolioConstraintsBody,
  type PortfolioRunParams,
  type PortfolioRunResponse,
} from './portfolioClient';
import { mergeSymbols } from './universe';

export type PortfolioRunContext = Omit<
  PortfolioRunParams,
  'code' | 'symbols' | 'constraints'
>;

export class PortfolioState {
  /** The universe, in insertion order (uppercase, unique, capped). */
  symbols = $state<string[]>([]);

  /** Optional hard constraints sent with the next run. */
  constraints = $state<PortfolioConstraintsBody | null>(null);

  isRunning = $state(false);
  runError = $state<string | null>(null);
  /** Last successful run's full blob (canonical result + sandbox envelope). */
  response = $state<PortfolioRunResponse | null>(null);

  isIngesting = $state(false);
  ingestError = $state<string | null>(null);
  /** Report from the last successful ingest of the current universe. */
  ingestReport = $state<IngestReport | null>(null);

  #client: PortfolioClient;

  constructor(client: PortfolioClient = httpPortfolioClient) {
    this.#client = client;
  }

  /** Merge free-form pasted/typed ticker text into the universe. */
  add(text: string): void {
    this.symbols = mergeSymbols(this.symbols, text);
  }

  remove(symbol: string): void {
    this.symbols = this.symbols.filter(s => s !== symbol);
  }

  clear(): void {
    this.symbols = [];
  }

  /**
   * Run `code` against the current universe. A non-ok sandbox status is
   * surfaced as `runError` with the run's stderr; the previous successful
   * response is kept so its dashboard stays readable.
   */
  async run(code: string, ctx: PortfolioRunContext): Promise<void> {
    if (this.symbols.length === 0) {
      this.runError = 'Add at least one symbol to the universe';
      return;
    }
    this.isRunning = true;
    this.runError = null;
    try {
      const res = await this.#client.run({
        code,
        symbols: [...this.symbols],
        ...ctx,
        ...(this.constraints ? { constraints: this.constraints } : {}),
      });
      if (res.status !== 'ok') {
        this.runError = res.stderr.trim() || `Backtest ${res.status}`;
        return;
      }
      this.response = res;
    } catch (err) {
      this.runError =
        err instanceof Error ? err.message : 'Portfolio backtest failed';
    } finally {
      this.isRunning = false;
    }
  }

  /**
   * Populate the datastore for the current universe so a subsequent run finds
   * bars. Failures surface as `ingestError`; success exposes the report.
   */
  async ingest(interval = '1d'): Promise<void> {
    if (this.symbols.length === 0) {
      this.ingestError = 'Add at least one symbol to the universe';
      return;
    }
    this.isIngesting = true;
    this.ingestError = null;
    try {
      this.ingestReport = await this.#client.ingest(
        [...this.symbols],
        interval,
      );
    } catch (err) {
      this.ingestError = err instanceof Error ? err.message : 'Ingest failed';
    } finally {
      this.isIngesting = false;
    }
  }
}
