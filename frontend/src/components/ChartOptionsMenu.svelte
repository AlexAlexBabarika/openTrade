<script lang="ts">
  import { tick } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import {
    CandlestickChart,
    LineChart,
    AreaChart,
    BarChart3,
    TrendingUp,
  } from 'lucide-svelte';
  import ColourSwatch from './ColourSwatch.svelte';
  import type { ChartColours } from '../lib/chartColours';

  export type ChartType = 'candlestick' | 'line';

  export interface MovingAverageConfig {
    enabled: boolean;
    period: number;
    lineWidth: number;
  }

  let {
    chartType = $bindable('candlestick'),
    showArea = $bindable(true),
    showVolume = $bindable(true),
    smaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
    emaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
    colours = $bindable({} as ChartColours),
  }: {
    chartType: ChartType;
    showArea: boolean;
    showVolume: boolean;
    smaConfig: MovingAverageConfig;
    emaConfig: MovingAverageConfig;
    colours: ChartColours;
  } = $props();

  let open = $state(false);
  let dialogEl: HTMLDivElement | undefined = $state();

  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function getFocusableElements(container: HTMLElement): HTMLElement[] {
    return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
  }

  function trapFocus(e: KeyboardEvent) {
    if (e.key !== 'Tab' || !dialogEl) return;
    const target = e.target as Node;
    if (!dialogEl.contains(target)) return;
    const focusable = getFocusableElements(dialogEl);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  function close() {
    open = false;
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  $effect(() => {
    if (!open) return;
    const onKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
      trapFocus(e);
    };
    window.addEventListener('keydown', onKeydown);
    tick().then(() => {
      const first = dialogEl && getFocusableElements(dialogEl)[0];
      first?.focus();
    });
    return () => window.removeEventListener('keydown', onKeydown);
  });
</script>

<Button
  variant="secondary"
  class="fixed bottom-10 left-2 z-40"
  onclick={() => (open = true)}
>
  Chart Options
</Button>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    role="presentation"
    onclick={handleBackdropClick}
    onkeydown={e => {
      if (e.target !== e.currentTarget) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        close();
      }
    }}
  >
    <div
      bind:this={dialogEl}
      class="relative w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg"
      role="dialog"
      aria-modal="true"
      aria-label="Chart Options"
    >
      <button
        type="button"
        class="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
        onclick={close}
        aria-label="Close"
      >
        &#x2715;
      </button>

      <h2 class="mb-5 text-lg font-semibold text-card-foreground">
        Chart Options
      </h2>

      <div class="flex flex-col gap-4">
        <!-- Row 1: Chart Type + Overlay -->
        <div class="flex items-end justify-between gap-4">
          <fieldset>
            <legend class="text-sm font-medium text-card-foreground mb-2"
              >Chart Type</legend
            >
            <div class="flex gap-2">
              <button
                type="button"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {chartType ===
                'candlestick'
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted-foreground hover:text-foreground'}"
                onclick={() => (chartType = 'candlestick')}
              >
                <CandlestickChart class="size-4" />
                Candlestick
              </button>
              <button
                type="button"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {chartType ===
                'line'
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted-foreground hover:text-foreground'}"
                onclick={() => (chartType = 'line')}
              >
                <LineChart class="size-4" />
                Line
              </button>
            </div>
          </fieldset>

          <fieldset>
            <legend class="text-sm font-medium text-card-foreground mb-2"
              >Overlay</legend
            >
            <div class="flex gap-2">
              <button
                type="button"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {showArea
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted-foreground hover:text-foreground'}"
                onclick={() => (showArea = !showArea)}
              >
                <AreaChart class="size-4" />
                Area
              </button>
              <button
                type="button"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {showVolume
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted-foreground hover:text-foreground'}"
                onclick={() => (showVolume = !showVolume)}
              >
                <BarChart3 class="size-4" />
                Volume
              </button>
            </div>
          </fieldset>
        </div>

        {#if chartType === 'candlestick'}
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-card-foreground min-w-[50px]">Chart:</span>
            <ColourSwatch bind:colour={colours.candleUpBody} label="Up body" />
            <ColourSwatch bind:colour={colours.candleDownBody} label="Down body" />
            <ColourSwatch bind:colour={colours.candleUpWick} label="Up wick" />
            <ColourSwatch bind:colour={colours.candleDownWick} label="Down wick" />
          </div>
        {/if}

        {#if chartType === 'line'}
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-card-foreground min-w-[50px]">Chart:</span>
            <ColourSwatch bind:colour={colours.lineColour} label="Line" />
          </div>
        {/if}

        {#if showArea}
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-card-foreground min-w-[50px]">Area:</span>
            <ColourSwatch bind:colour={colours.areaTop} label="Area top" />
            <ColourSwatch bind:colour={colours.areaBottom} label="Area bottom" />
          </div>
        {/if}

        {#if showVolume}
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-card-foreground min-w-[50px]">Volume:</span>
            <ColourSwatch bind:colour={colours.volumeUp} label="Up volume" />
            <ColourSwatch bind:colour={colours.volumeDown} label="Down volume" />
          </div>
        {/if}

        <!-- Row 2: Moving Averages -->
        <fieldset>
          <legend class="text-sm font-medium text-card-foreground mb-2"
            >Moving Averages</legend
          >
          <div
            class="rounded-md bg-muted/50 border border-border p-3 flex flex-col gap-3"
          >
            <!-- SMA -->
            <div>
              <div class="text-xs font-medium text-muted-foreground mb-1.5">
                Simple Moving Average
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {smaConfig.enabled
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground'}"
                  onclick={() =>
                    (smaConfig = {
                      ...smaConfig,
                      enabled: !smaConfig.enabled,
                    })}
                >
                  <TrendingUp class="size-4" />
                  SMA
                </button>
                {#if smaConfig.enabled}
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Width
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={smaConfig.lineWidth}
                      oninput={e =>
                        (smaConfig = {
                          ...smaConfig,
                          lineWidth:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 2,
                        })}
                      class="w-14 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Period
                    <input
                      type="number"
                      min="1"
                      max="500"
                      value={smaConfig.period}
                      oninput={e =>
                        (smaConfig = {
                          ...smaConfig,
                          period:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 20,
                        })}
                      class="w-16 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <ColourSwatch bind:colour={colours.smaLine} label="Line" />
                {/if}
              </div>
            </div>

            <!-- EMA -->
            <div>
              <div class="text-xs font-medium text-muted-foreground mb-1.5">
                Exponential Moving Average
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {emaConfig.enabled
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground'}"
                  onclick={() =>
                    (emaConfig = {
                      ...emaConfig,
                      enabled: !emaConfig.enabled,
                    })}
                >
                  <TrendingUp class="size-4" />
                  EMA
                </button>
                {#if emaConfig.enabled}
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Width
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={emaConfig.lineWidth}
                      oninput={e =>
                        (emaConfig = {
                          ...emaConfig,
                          lineWidth:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 2,
                        })}
                      class="w-14 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Period
                    <input
                      type="number"
                      min="1"
                      max="500"
                      value={emaConfig.period}
                      oninput={e =>
                        (emaConfig = {
                          ...emaConfig,
                          period:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 20,
                        })}
                      class="w-16 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <ColourSwatch bind:colour={colours.emaLine} label="Line" />
                {/if}
              </div>
            </div>
          </div>
        </fieldset>
      </div>
    </div>
  </div>
{/if}
