<script lang="ts">
  type Param = { name: string; type?: string; desc: string };
  type Helper = {
    name: string;
    sig: string;
    returns?: string;
    desc: string;
    params?: Param[];
  };

  const contract: Helper[] = [
    {
      name: 'on_bar',
      sig: 'def on_bar(ctx) -> None',
      desc: 'Required. Called once per closed bar, oldest to newest. All trading logic lives here; read the market through ctx and place orders with ctx.buy / ctx.sell.',
    },
    {
      name: 'params',
      sig: 'params = { "name": Int(...) | Float(...) | Choice(...) }',
      desc: 'Optional module-level dict declaring the parameter space. Drives the sweep form, and ctx.params at runtime. A single backtest uses the first value of each entry unless overridden.',
    },
  ];

  const space: Helper[] = [
    {
      name: 'Int',
      sig: 'Int(low: int, high: int, step=1)',
      desc: 'Inclusive integer grid: low, low+step, … up to high.',
    },
    {
      name: 'Float',
      sig: 'Float(low: float, high: float, step=1.0)',
      desc: "Inclusive float grid; values are rounded to the step's decimals to avoid float drift.",
    },
    {
      name: 'Choice',
      sig: 'Choice(options: list)',
      desc: 'An explicit set of values, e.g. Choice(["sma", "ema"]).',
    },
  ];

  const ctxApi: Helper[] = [
    {
      name: 'ctx.params',
      sig: 'ctx.params -> dict',
      desc: 'Concrete parameter values for this run, e.g. ctx.params["fast"]. Empty if the strategy declares no params.',
    },
    {
      name: 'ctx.bars',
      sig: 'ctx.bars -> BarsView',
      desc: 'Look-ahead-guarded bar history. ctx.bars[-1] is the current bar, ctx.bars[0] the first; len(ctx.bars) is the count revealed so far. Reading a future index raises. Integer indices only (no slices); iterable.',
    },
    {
      name: 'ctx.time',
      sig: 'ctx.time -> datetime',
      desc: "The current bar's close timestamp (UTC).",
    },
    {
      name: 'ctx.position',
      sig: 'ctx.position -> Position',
      desc: 'Signed position: .quantity (> 0 long, < 0 short, 0 flat) and .avg_price (average entry price of the open quantity).',
    },
    {
      name: 'ctx.cash',
      sig: 'ctx.cash -> float',
      desc: 'Cash after all fills so far.',
    },
    {
      name: 'ctx.equity',
      sig: 'ctx.equity -> float',
      desc: "Cash plus the position marked at the current bar's close.",
    },
    {
      name: 'ctx.state',
      sig: 'ctx.state -> dict',
      desc: 'Free-form scratch space that persists across bars within a run. Use it for rolling sums, flags, entry levels, etc.',
    },
    {
      name: 'ctx.random',
      sig: 'ctx.random -> random.Random',
      desc: "The run's seeded RNG. Use this — never the global random module — so runs stay deterministic and sweeps reproducible.",
    },
    {
      name: 'ctx.buy / ctx.sell',
      sig: 'ctx.buy(quantity: float) -> Order   ·   ctx.sell(quantity: float) -> Order',
      desc: "Submit a market order. An order placed on bar t fills at bar t+1's open (plus costs) — there is no same-bar fill, by design, so fills are free of look-ahead.",
    },
  ];

  const barFields: Param[] = [
    { name: 'bar.time', type: 'datetime', desc: "The bar's close timestamp (UTC)." },
    { name: 'bar.open', type: 'float', desc: 'Open price.' },
    { name: 'bar.high', type: 'float', desc: 'High price.' },
    { name: 'bar.low', type: 'float', desc: 'Low price.' },
    { name: 'bar.close', type: 'float', desc: 'Close price.' },
    { name: 'bar.volume', type: 'float', desc: 'Volume.' },
  ];

  const allowedImports = [
    'math', 'statistics', 'dataclasses', 'itertools',
    'functools', 'collections', 'typing', 'datetime',
  ];

  const limits = [
    'Runs AST-guarded in a spawned subprocess, one bar at a time.',
    'Wallclock timeout: ~30s per run.',
    'Memory cap: ~512 MB per run.',
    'No filesystem writes, no network access, no subprocesses.',
    'No dunder access (__class__, __subclasses__, __globals__, …).',
    'No df / np / pl and no whole-series reads — unlike indicator scripts, state is built bar by bar.',
    'print() output is captured into the run result (stdout/stderr).',
  ];

  const examples: { title: string; code: string }[] = [
    {
      title: 'Parameterized buy & hold (the seed strategy)',
      code: `params = {
    "fast": Int(5, 50, step=5),
    "slow": Int(20, 200, step=10),
}

def on_bar(ctx):
    if ctx.position.quantity == 0:
        ctx.buy(1)`,
    },
    {
      title: 'SMA crossover',
      code: `params = {
    "fast": Int(5, 50, step=5),
    "slow": Int(20, 200, step=10),
}

def sma(ctx, n):
    m = len(ctx.bars)
    if m < n:
        return None
    return sum(ctx.bars[i].close for i in range(m - n, m)) / n

def on_bar(ctx):
    fast = sma(ctx, ctx.params["fast"])
    slow = sma(ctx, ctx.params["slow"])
    if fast is None or slow is None:
        return
    if fast > slow and ctx.position.quantity == 0:
        ctx.buy(10)
    elif fast < slow and ctx.position.quantity > 0:
        ctx.sell(ctx.position.quantity)`,
    },
    {
      title: 'Trailing-drop exit with ctx.state',
      code: `params = {
    "warmup": Int(10, 60, step=10),
    "drop": Float(0.02, 0.10, step=0.02),
}

def on_bar(ctx):
    bar = ctx.bars[-1]
    hi = ctx.state.get("hi", 0.0)
    if bar.close > hi:
        ctx.state["hi"] = hi = bar.close

    if ctx.position.quantity == 0:
        if len(ctx.bars) >= ctx.params["warmup"]:
            ctx.buy(10)
    elif bar.close < hi * (1 - ctx.params["drop"]):
        ctx.sell(ctx.position.quantity)
        ctx.state["hi"] = 0.0`,
    },
  ];
</script>

<div class="docs">
  <article>
    <header class="hero">
      <span class="kicker">// reference</span>
      <h1>strategy scripting</h1>
      <p class="lede">
        Write Python that defines <code>on_bar(ctx)</code> (and optionally a
        <code>params</code> space). The engine replays the loaded OHLCV bar by
        bar; the same code drives single backtests and parameter sweeps.
      </p>
    </header>

    <section>
      <h2><span class="hash">§</span> contract</h2>
      <p class="dim">What the engine looks for at module level.</p>
      <ul class="defs">
        {#each contract as h (h.name)}
          <li class="block">
            <code class="sig">{h.sig}</code>
            <span class="desc">{h.desc}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section>
      <h2><span class="hash">§</span> parameter space</h2>
      <p class="dim">Available globally — no import required. Each declares the values a sweep may try.</p>
      <ul class="defs">
        {#each space as h (h.name)}
          <li class="block">
            <code class="sig">{h.sig}</code>
            <span class="desc">{h.desc}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section>
      <h2><span class="hash">§</span> ctx api</h2>
      <p class="dim">Everything a strategy can see and do, one bar at a time.</p>
      <ul class="defs">
        {#each ctxApi as h (h.name)}
          <li class="block">
            <code class="sig">{h.sig}</code>
            <span class="desc">{h.desc}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section>
      <h2><span class="hash">§</span> bar fields</h2>
      <p class="dim">Each element of ctx.bars is a closed OHLCV bar.</p>
      <ul class="defs">
        {#each barFields as g (g.name)}
          <li>
            <code class="name">{g.name}</code>
            {#if g.type}<span class="type">{g.type}</span>{/if}
            <span class="desc">{g.desc}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section>
      <h2><span class="hash">§</span> allowed imports</h2>
      <p class="dim">stdlib modules permitted by the AST guard.</p>
      <p class="tags">
        {#each allowedImports as m (m)}
          <span class="tag">{m}</span>
        {/each}
      </p>
    </section>

    <section>
      <h2><span class="hash">§</span> sandbox limits</h2>
      <ul class="bullets">
        {#each limits as l (l)}
          <li>{l}</li>
        {/each}
      </ul>
    </section>

    <section>
      <h2><span class="hash">§</span> examples</h2>
      {#each examples as ex (ex.title)}
        <div class="example">
          <div class="example-title">{ex.title}</div>
          <pre><code>{ex.code}</code></pre>
        </div>
      {/each}
    </section>
  </article>
</div>

<style>
  .docs {
    height: 100%;
    overflow-y: auto;
    background:
      linear-gradient(
        180deg,
        color-mix(in oklab, oklch(var(--popover)) 100%, black 4%),
        color-mix(in oklab, oklch(var(--popover)) 100%, black 10%)
      );
  }

  article {
    max-width: 880px;
    margin: 0 auto;
    padding: 28px 32px 64px;
    color: oklch(var(--foreground));
    font-family: 'Space Mono', ui-monospace, SFMono-Regular, monospace;
    font-size: 12.5px;
    line-height: 1.65;
  }

  .hero {
    margin-bottom: 28px;
    padding-bottom: 18px;
    border-bottom: 1px dashed
      color-mix(in oklab, oklch(var(--border)) 90%, transparent);
  }
  .kicker {
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: oklch(var(--muted-foreground));
  }
  h1 {
    margin: 4px 0 6px;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .lede {
    color: color-mix(in oklab, oklch(var(--foreground)) 70%, transparent);
    margin: 0;
  }
  .lede code {
    font-family: inherit;
    color: oklch(var(--primary));
  }

  section {
    margin-top: 26px;
  }
  h2 {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin: 0 0 6px;
    font-size: 13px;
    letter-spacing: 0.06em;
    text-transform: lowercase;
  }
  .hash {
    color: oklch(var(--primary));
    font-weight: 700;
  }
  .dim {
    margin: 0 0 10px;
    color: oklch(var(--muted-foreground));
    font-size: 11.5px;
  }

  .defs {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .defs li {
    display: grid;
    grid-template-columns: minmax(140px, max-content) auto 1fr;
    gap: 12px;
    align-items: baseline;
    padding: 6px 10px;
    border-left: 2px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    background: color-mix(in oklab, oklch(var(--foreground)) 3%, transparent);
    border-radius: 0 4px 4px 0;
  }
  .defs li.block {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .defs .name {
    color: oklch(var(--primary));
    font-weight: 700;
  }
  .defs .sig {
    color: oklch(var(--foreground));
    font-weight: 600;
    word-break: break-word;
  }
  .defs .type {
    font-size: 10.5px;
    padding: 1px 6px;
    border: 1px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    border-radius: 999px;
    color: oklch(var(--muted-foreground));
  }
  .defs .desc {
    color: color-mix(in oklab, oklch(var(--foreground)) 78%, transparent);
  }

  .tags { margin: 0; }
  .tag {
    display: inline-block;
    margin: 2px 6px 2px 0;
    padding: 2px 8px;
    border: 1px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    border-radius: 3px;
    font-size: 11px;
    color: oklch(var(--foreground));
    background: color-mix(in oklab, oklch(var(--foreground)) 4%, transparent);
  }

  .bullets {
    margin: 0;
    padding-left: 18px;
    color: color-mix(in oklab, oklch(var(--foreground)) 78%, transparent);
  }
  .bullets li { margin: 2px 0; }

  .example {
    margin-top: 12px;
  }
  .example-title {
    margin: 0 0 4px;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: oklch(var(--muted-foreground));
  }
  pre {
    margin: 0;
    padding: 12px 14px;
    border: 1px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
    border-radius: 4px;
    background: color-mix(in oklab, oklch(var(--background)) 70%, black 30%);
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.55;
  }
  pre code { color: oklch(var(--foreground)); }

  /* Light theme: pure white surfaces, black hairlines, no greys. */
  :global(html:not(.dark)) .docs { background: #ffffff; }
  :global(html:not(.dark)) .hero { border-bottom: 1px dashed #000; }
  :global(html:not(.dark)) .defs li {
    background: #ffffff;
    border-left: 2px solid #000;
  }
  :global(html:not(.dark)) .defs .type {
    background: #ffffff;
    border-color: #000;
    color: #000;
  }
  :global(html:not(.dark)) .tag {
    background: #ffffff;
    border-color: #000;
    color: #000;
  }
  :global(html:not(.dark)) pre {
    background: #ffffff;
    border-color: #000;
  }
</style>
