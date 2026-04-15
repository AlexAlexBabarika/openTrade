<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Dialog from '$lib/components/ui/dialog';
  import * as Select from '$lib/components/ui/select';
  import CandlestickChart from '@lucide/svelte/icons/candlestick-chart';
  import LineChart from '@lucide/svelte/icons/line-chart';
  import AreaChart from '@lucide/svelte/icons/area-chart';
  import BarChart3 from '@lucide/svelte/icons/bar-chart-3';
  import TrendingUp from '@lucide/svelte/icons/trending-up';
  import ColourSwatch from './ColourSwatch.svelte';
  import type { ChartColours, ChartTemplate } from '../lib/chartColours';
  import {
    defaultChartColours,
    loadTemplates,
    saveTemplate,
    deleteTemplate,
  } from '../lib/chartColours';

  export type ChartType = 'candlestick' | 'line';

  export interface MovingAverageConfig {
    enabled: boolean;
    period: number;
    lineWidth: number;
  }

  export interface BollingerBandsConfig {
    enabled: boolean;
    period: number;
    stdDev: number;
    lineWidth: number;
  }

  let {
    chartType = $bindable('candlestick'),
    showArea = $bindable(true),
    showVolume = $bindable(true),
    smaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
    emaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
    bbandsConfig = $bindable({ enabled: false, period: 20, stdDev: 2, lineWidth: 1 }),
    colours = $bindable({} as ChartColours),
  }: {
    chartType: ChartType;
    showArea: boolean;
    showVolume: boolean;
    smaConfig: MovingAverageConfig;
    emaConfig: MovingAverageConfig;
    bbandsConfig: BollingerBandsConfig;
    colours: ChartColours;
  } = $props();

  let open = $state(false);

  let templates = $state<ChartTemplate[]>(loadTemplates());
  let selectedTemplateName = $state('');

  let saveDialogOpen = $state(false);
  let templateNameInput = $state('');

  function applyTemplate(name: string) {
    const tpl = templates.find((t) => t.name === name);
    if (!tpl) return;
    colours = { ...tpl.colours };
    smaConfig = { ...smaConfig, lineWidth: tpl.smaLineWidth };
    emaConfig = { ...emaConfig, lineWidth: tpl.emaLineWidth };
    if (tpl.chartType !== undefined) chartType = tpl.chartType;
    if (tpl.showArea !== undefined) showArea = tpl.showArea;
    if (tpl.showVolume !== undefined) showVolume = tpl.showVolume;
    if (tpl.smaEnabled !== undefined) smaConfig = { ...smaConfig, enabled: tpl.smaEnabled };
    if (tpl.emaEnabled !== undefined) emaConfig = { ...emaConfig, enabled: tpl.emaEnabled };
    if (tpl.bbandsLineWidth !== undefined) bbandsConfig = { ...bbandsConfig, lineWidth: tpl.bbandsLineWidth };
    if (tpl.bbandsEnabled !== undefined) bbandsConfig = { ...bbandsConfig, enabled: tpl.bbandsEnabled };
  }

  function openSaveDialog() {
    templateNameInput = selectedTemplateName || '';
    saveDialogOpen = true;
  }

  function confirmSave() {
    if (!templateNameInput.trim()) return;
    const tpl: ChartTemplate = {
      name: templateNameInput.trim(),
      colours: { ...colours },
      smaLineWidth: smaConfig.lineWidth,
      emaLineWidth: emaConfig.lineWidth,
      bbandsLineWidth: bbandsConfig.lineWidth,
      chartType,
      showArea,
      showVolume,
      smaEnabled: smaConfig.enabled,
      emaEnabled: emaConfig.enabled,
      bbandsEnabled: bbandsConfig.enabled,
    };
    saveTemplate(tpl);
    templates = loadTemplates();
    selectedTemplateName = tpl.name;
    saveDialogOpen = false;
  }

  function handleDelete() {
    if (!selectedTemplateName) return;
    deleteTemplate(selectedTemplateName);
    templates = loadTemplates();
    selectedTemplateName = '';
  }

  function handleReset() {
    colours = defaultChartColours();
    chartType = 'candlestick';
    showArea = true;
    showVolume = true;
    smaConfig = { enabled: false, period: 20, lineWidth: 2 };
    emaConfig = { enabled: false, period: 20, lineWidth: 2 };
    bbandsConfig = { enabled: false, period: 20, stdDev: 2, lineWidth: 1 };
    selectedTemplateName = '';
  }

</script>

<Button
  variant="secondary"
  class="fixed bottom-10 left-2 z-40"
  onclick={() => (open = true)}
>
  Chart Options
</Button>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Chart Options</Dialog.Title>
    </Dialog.Header>

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

        <div class="flex items-center gap-3">
          <span class="text-sm font-medium text-card-foreground min-w-[50px]">Background:</span>
          <ColourSwatch bind:colour={colours.chartBackground} label="Chart" />
          <ColourSwatch bind:colour={colours.gridLines} label="Grid" />
          <ColourSwatch bind:colour={colours.textColour} label="Text" />
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

            <!-- Bollinger Bands -->
            <div>
              <div class="text-xs font-medium text-muted-foreground mb-1.5">
                Bollinger Bands
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors {bbandsConfig.enabled
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:text-foreground'}"
                  onclick={() =>
                    (bbandsConfig = {
                      ...bbandsConfig,
                      enabled: !bbandsConfig.enabled,
                    })}
                >
                  <TrendingUp class="size-4" />
                  BB
                </button>
                {#if bbandsConfig.enabled}
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Width
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={bbandsConfig.lineWidth}
                      oninput={e =>
                        (bbandsConfig = {
                          ...bbandsConfig,
                          lineWidth:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 1,
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
                      value={bbandsConfig.period}
                      oninput={e =>
                        (bbandsConfig = {
                          ...bbandsConfig,
                          period:
                            parseInt(
                              (e.target as HTMLInputElement).value,
                              10,
                            ) || 20,
                        })}
                      class="w-16 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <label
                    class="flex items-center gap-1.5 text-sm text-muted-foreground"
                  >
                    Std
                    <input
                      type="number"
                      min="0.1"
                      max="5"
                      step="0.1"
                      value={bbandsConfig.stdDev}
                      oninput={e =>
                        (bbandsConfig = {
                          ...bbandsConfig,
                          stdDev:
                            parseFloat(
                              (e.target as HTMLInputElement).value,
                            ) || 2,
                        })}
                      class="w-16 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
                    />
                  </label>
                  <ColourSwatch bind:colour={colours.bbandsUpper} label="Upper" />
                  <ColourSwatch bind:colour={colours.bbandsMiddle} label="Mid" />
                  <ColourSwatch bind:colour={colours.bbandsLower} label="Lower" />
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

        <!-- Templates -->
        <fieldset>
          <legend class="text-sm font-medium text-card-foreground mb-2"
            >Templates</legend
          >
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <div class="flex items-center gap-2 flex-wrap">
              <Select.Root
                type="single"
                bind:value={selectedTemplateName}
                onValueChange={(name) => {
                  if (name) applyTemplate(name);
                }}
              >
                <Select.Trigger class="min-w-[160px]">
                  {selectedTemplateName || 'Select template'}
                </Select.Trigger>
                <Select.Content>
                  {#each templates as tpl (tpl.name)}
                    <Select.Item value={tpl.name}>{tpl.name}</Select.Item>
                  {/each}
                </Select.Content>
              </Select.Root>
              <Button variant="outline" size="sm" onclick={openSaveDialog}>
                Save
              </Button>
              {#if selectedTemplateName}
                <Button variant="outline" size="sm" class="text-red-400 hover:text-red-300 border-red-400/50 hover:border-red-400" onclick={handleDelete}>
                  Delete
                </Button>
              {/if}
            </div>
            <Button variant="outline" size="sm" onclick={handleReset}>
              Reset to Default
            </Button>
          </div>
        </fieldset>
      </div>
  </Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={saveDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Save Template</Dialog.Title>
      <Dialog.Description>Enter a name for your chart template.</Dialog.Description>
    </Dialog.Header>
    <form
      onsubmit={(e) => {
        e.preventDefault();
        confirmSave();
      }}
    >
      <Input
        bind:value={templateNameInput}
        placeholder="Template name"
        class="mt-2"
        autofocus
      />
      <Dialog.Footer class="mt-4">
        <Button variant="outline" type="button" onclick={() => (saveDialogOpen = false)}>
          Cancel
        </Button>
        <Button type="submit" disabled={!templateNameInput.trim()}>Save</Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
