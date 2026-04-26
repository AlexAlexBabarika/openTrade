const INDICATOR_DEBOUNCE_MS = 300;

export interface IndicatorEffectOptions<T> {
  enabled: () => boolean;
  hasCandles: () => boolean;
  symbol: () => string;
  version: () => number;
  args: () => readonly unknown[];
  fetch: (symbol: string, args: readonly unknown[]) => Promise<T[]>;
  onError: (message: string) => void;
  label: string;
}

export interface IndicatorResult<T> {
  readonly points: T[];
}

export function useIndicatorEffect<T>(
  opts: IndicatorEffectOptions<T>,
): IndicatorResult<T> {
  let points = $state<T[]>([]);

  $effect(() => {
    const enabled = opts.enabled();
    const hasCandles = opts.hasCandles();
    const sym = opts.symbol();
    opts.version();
    const args = opts.args();
    if (!enabled || !hasCandles) {
      points = [];
      return;
    }
    const id = setTimeout(() => {
      opts
        .fetch(sym, args)
        .then(p => (points = p))
        .catch(e => {
          points = [];
          opts.onError(
            e instanceof Error ? e.message : `Failed to load ${opts.label}`,
          );
        });
    }, INDICATOR_DEBOUNCE_MS);
    return () => clearTimeout(id);
  });

  return {
    get points() {
      return points;
    },
  };
}
