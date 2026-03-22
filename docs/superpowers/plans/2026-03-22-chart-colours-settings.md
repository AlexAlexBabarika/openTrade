# Chart Colours Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-configurable colour settings to the Chart Options dialog, displayed as small coloured squares with labels that only appear for active chart elements.

**Architecture:** A `ChartColours` interface holds all colour values. `App.svelte` owns the state (initialized from current defaults). `ChartOptionsMenu.svelte` renders colour swatches with hidden native `<input type="color">` pickers. `Chart.svelte` and `chart.ts` consume the colours when creating/updating series.

**Tech Stack:** Svelte 5, TypeScript, Lightweight Charts v4, TailwindCSS

**Spec:** `docs/superpowers/specs/2026-03-22-chart-colours-settings-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/lib/chartColours.ts` | Create | `ChartColours` interface + `defaultChartColours()` factory |
| `frontend/src/components/ColourSwatch.svelte` | Create | Reusable swatch component (square + label + hidden input) |
| `frontend/src/components/ChartOptionsMenu.svelte` | Modify | Add colour swatch sections with conditional rendering |
| `frontend/src/lib/chart.ts` | Modify | Accept `ChartColours` in series creation and `syncChartTheme` |
| `frontend/src/lib/chartAdapters.ts` | Modify | Accept volume colours in `candleOHLCVtoVolumeData` |
| `frontend/src/components/Chart.svelte` | Modify | Accept and use `ChartColours` prop |
| `frontend/src/App.svelte` | Modify | Own `ChartColours` state, pass to children |

---

### Task 1: Create ChartColours interface and defaults

**Files:**
- Create: `frontend/src/lib/chartColours.ts`

- [ ] **Step 1: Create the ChartColours type and default factory**

```typescript
// frontend/src/lib/chartColours.ts
import { getCssVarColor } from './chart';

export interface ChartColours {
  candleUpBody: string;
  candleDownBody: string;
  candleUpWick: string;
  candleDownWick: string;
  lineColour: string;
  areaTop: string;
  areaBottom: string;
  volumeUp: string;
  volumeDown: string;
  smaLine: string;
  emaLine: string;
}

export function defaultChartColours(): ChartColours {
  const up = getCssVarColor('--up-color', '#5ea500');
  const down = getCssVarColor('--down-color', '#e7000b');
  return {
    candleUpBody: up,
    candleDownBody: down,
    candleUpWick: up,
    candleDownWick: down,
    lineColour: getCssVarColor('--foreground', '#d1d4dc'),
    areaTop: getCssVarColor('--area-top-color', 'rgba(56, 33, 110, 0.5)'),
    areaBottom: getCssVarColor('--area-bottom-color', 'rgba(56, 33, 110, 0.05)'),
    volumeUp: '#26a63130',
    volumeDown: '#c21a2a30',
    smaLine: '#2962FF',
    emaLine: '#FF6D00',
  };
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors related to `chartColours.ts`

---

### Task 2: Create ColourSwatch component

**Files:**
- Create: `frontend/src/components/ColourSwatch.svelte`

- [ ] **Step 1: Create the reusable swatch component**

This component renders a 24x24 coloured square with a label. Clicking it opens a hidden native `<input type="color">`. Since `<input type="color">` doesn't support alpha, we strip alpha for the picker value and reapply it on change.

```svelte
<!-- frontend/src/components/ColourSwatch.svelte -->
<script lang="ts">
  let {
    colour = $bindable('#000000'),
    label,
  }: {
    colour: string;
    label: string;
  } = $props();

  let inputEl: HTMLInputElement | undefined = $state();

  /** Extract hex RGB from any CSS colour string for the native picker */
  function toHex6(c: string): string {
    // Handle #RRGGBBAA or #RRGGBB
    if (c.startsWith('#')) {
      const hex = c.slice(1);
      if (hex.length >= 6) return '#' + hex.slice(0, 6);
    }
    // Handle rgb()/rgba() — parse via canvas
    const ctx = document.createElement('canvas').getContext('2d');
    if (ctx) {
      ctx.fillStyle = c;
      return ctx.fillStyle; // returns #rrggbb
    }
    return '#000000';
  }

  /** Get alpha suffix from original colour (if any) */
  function getAlphaSuffix(c: string): string {
    if (c.startsWith('#') && c.length === 9) {
      return c.slice(7, 9);
    }
    return '';
  }

  function handleInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    const alpha = getAlphaSuffix(colour);
    colour = val + alpha;
  }
</script>

<button
  type="button"
  class="flex items-center gap-2 group"
  onclick={() => inputEl?.click()}
  aria-label="Pick colour for {label}"
>
  <span
    class="block w-6 h-6 rounded border border-border group-hover:border-foreground transition-colors cursor-pointer"
    style="background-color: {colour};"
  ></span>
  <span class="text-xs text-muted-foreground">{label}</span>
  <input
    bind:this={inputEl}
    type="color"
    value={toHex6(colour)}
    oninput={handleInput}
    class="sr-only"
    tabindex={-1}
  />
</button>
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

---

### Task 3: Add colour swatches to ChartOptionsMenu

**Files:**
- Modify: `frontend/src/components/ChartOptionsMenu.svelte`

- [ ] **Step 1: Add the colours bindable prop**

Add import and prop for `ChartColours`:

In the `<script>` tag, after the existing imports, add:
```typescript
import ColourSwatch from './ColourSwatch.svelte';
import type { ChartColours } from '../lib/chartColours';
```

Add `colours` to the destructured props:
```typescript
let {
  chartType = $bindable('candlestick'),
  showArea = $bindable(true),
  smaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
  emaConfig = $bindable({ enabled: false, period: 20, lineWidth: 2 }),
  colours = $bindable({} as ChartColours),
}: {
  chartType: ChartType;
  showArea: boolean;
  smaConfig: MovingAverageConfig;
  emaConfig: MovingAverageConfig;
  colours: ChartColours;
} = $props();
```

- [ ] **Step 2: Add candlestick colour swatches after chart type selector**

Insert after the closing `</fieldset>` of the Chart Type section (after `</div>` of the flex row, before `<!-- Row 2: Moving Averages -->`), a conditional candlestick colours section:

```svelte
{#if chartType === 'candlestick'}
  <div class="flex flex-wrap gap-3">
    <ColourSwatch bind:colour={colours.candleUpBody} label="Up body" />
    <ColourSwatch bind:colour={colours.candleDownBody} label="Down body" />
    <ColourSwatch bind:colour={colours.candleUpWick} label="Up wick" />
    <ColourSwatch bind:colour={colours.candleDownWick} label="Down wick" />
  </div>
{/if}

{#if chartType === 'line'}
  <div class="flex flex-wrap gap-3">
    <ColourSwatch bind:colour={colours.lineColour} label="Line" />
  </div>
{/if}
```

- [ ] **Step 3: Add area colour swatches after overlay section**

Insert after the overlay `</fieldset>`, conditionally:

```svelte
{#if showArea}
  <div class="flex flex-wrap gap-3">
    <ColourSwatch bind:colour={colours.areaTop} label="Area top" />
    <ColourSwatch bind:colour={colours.areaBottom} label="Area bottom" />
  </div>
{/if}
```

- [ ] **Step 4: Add volume colour swatches**

Insert before the Moving Averages fieldset (always visible):

```svelte
<div class="flex flex-wrap gap-3">
  <ColourSwatch bind:colour={colours.volumeUp} label="Up volume" />
  <ColourSwatch bind:colour={colours.volumeDown} label="Down volume" />
</div>
```

- [ ] **Step 5: Add SMA/EMA colour swatches inline with their controls**

Inside the SMA `{#if smaConfig.enabled}` block, after the Period input label, add:
```svelte
<ColourSwatch bind:colour={colours.smaLine} label="Line" />
```

Inside the EMA `{#if emaConfig.enabled}` block, after the Period input label, add:
```svelte
<ColourSwatch bind:colour={colours.emaLine} label="Line" />
```

- [ ] **Step 6: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

---

### Task 4: Update chart.ts to accept colour overrides

**Files:**
- Modify: `frontend/src/lib/chart.ts`

- [ ] **Step 1: Import ChartColours and update addCandlestickSeries**

Add import at top of `chart.ts`:
```typescript
import type { ChartColours } from './chartColours';
```

Change `addCandlestickSeries` signature and body:
```typescript
export function addCandlestickSeries(
  chart: IChartApi,
  colours?: ChartColours,
): ISeriesApi<'Candlestick'> {
  const upColor = colours?.candleUpBody ?? getCssVarColor('--up-color', '#5ea500');
  const downColor = colours?.candleDownBody ?? getCssVarColor('--down-color', '#e7000b');
  const wickUpColor = colours?.candleUpWick ?? upColor;
  const wickDownColor = colours?.candleDownWick ?? downColor;

  const series = chart.addCandlestickSeries({
    upColor,
    downColor,
    borderDownColor: downColor,
    borderUpColor: upColor,
    wickDownColor,
    wickUpColor,
  });
  return series;
}
```

- [ ] **Step 2: Update addAreaSeries**

```typescript
export function addAreaSeries(
  chart: IChartApi,
  colours?: ChartColours,
): ISeriesApi<'Area'> {
  const topColor = colours?.areaTop ?? getCssVarColor('--area-top-color', 'rgba(56, 33, 110, 0.5)');
  const bottomColor = colours?.areaBottom ?? getCssVarColor('--area-bottom-color', 'rgba(56, 33, 110, 0.05)');

  const series = chart.addAreaSeries({
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    lineColor: 'transparent',
    topColor,
    bottomColor,
  });
  return series;
}
```

- [ ] **Step 3: Update syncChartTheme to use ChartColours**

Change signature to accept colours:
```typescript
export function syncChartTheme(
  chart: IChartApi,
  candleSeries?: ISeriesApi<'Candlestick'> | null,
  areaSeries?: ISeriesApi<'Area'> | null,
  lineSeries?: ISeriesApi<'Line'> | null,
  colours?: ChartColours,
) {
```

In the candleSeries block, use colours if provided:
```typescript
if (candleSeries) {
  const upColor = colours?.candleUpBody ?? getCssVarColor('--up-color', '#5ea500');
  const downColor = colours?.candleDownBody ?? getCssVarColor('--down-color', '#e7000b');
  const wickUpColor = colours?.candleUpWick ?? upColor;
  const wickDownColor = colours?.candleDownWick ?? downColor;
  candleSeries.applyOptions({
    upColor,
    downColor,
    borderDownColor: downColor,
    borderUpColor: upColor,
    wickDownColor,
    wickUpColor,
  });
}
```

In the areaSeries block:
```typescript
if (areaSeries) {
  const topColor = colours?.areaTop ?? getCssVarColor('--area-top-color', 'rgba(56, 33, 110, 0.5)');
  const bottomColor = colours?.areaBottom ?? getCssVarColor('--area-bottom-color', 'rgba(56, 33, 110, 0.05)');
  areaSeries.applyOptions({ topColor, bottomColor });
}
```

In the lineSeries block:
```typescript
if (lineSeries) {
  const lineColor = colours?.lineColour ?? textColor;
  lineSeries.applyOptions({ color: lineColor });
}
```

- [ ] **Step 4: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

---

### Task 5: Update chartAdapters.ts for volume colours

**Files:**
- Modify: `frontend/src/lib/chartAdapters.ts`

- [ ] **Step 1: Add optional colour params to candleOHLCVtoVolumeData**

```typescript
export function candleOHLCVtoVolumeData(
  c: OHLCVCandle,
  volumeUpColor?: string,
  volumeDownColor?: string,
): HistogramData {
  return {
    time: isoToChartTime(c.timestamp),
    value: c.volume,
    color: c.close > c.open
      ? (volumeUpColor ?? '#26a63130')
      : (volumeDownColor ?? '#c21a2a30'),
  };
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

---

### Task 6: Update Chart.svelte to consume colours

**Files:**
- Modify: `frontend/src/components/Chart.svelte`

- [ ] **Step 1: Add colours prop**

Add import:
```typescript
import type { ChartColours } from '../lib/chartColours';
```

Add to props destructure:
```typescript
colours = undefined as ChartColours | undefined,
```

And to the type annotation:
```typescript
colours?: ChartColours;
```

- [ ] **Step 2: Pass colours to series creation functions**

In `applySeries()`, change the candlestick branch:
```typescript
if (type === 'candlestick') {
  candleSeries = addCandlestickSeries(chart, colours);
} else {
  const lineColor = colours?.lineColour ?? getCssVarColor('--foreground', '#d1d4dc');
  lineSeries = addLineSeries(chart, lineColor);
}
```

In `applyArea()`, change the creation branch:
```typescript
if (enabled && !areaSeries) {
  areaSeries = addAreaSeries(chart, colours);
}
```

- [ ] **Step 3: Pass volume colours to data mapping**

In `updateChartData()`, change the volume line:
```typescript
volumeSeries.setData(
  data.map(c => candleOHLCVtoVolumeData(c, colours?.volumeUp, colours?.volumeDown))
);
```

- [ ] **Step 4: Pass colours to syncChartTheme**

In the MutationObserver callback:
```typescript
syncChartTheme(chart, candleSeries, areaSeries, lineSeries, colours);
```

- [ ] **Step 5: Use colours for SMA/EMA series creation**

In the SMA effect, change the addLineSeries call:
```typescript
smaSeries = addLineSeries(chart, colours?.smaLine ?? '#2962FF');
```

In the EMA effect:
```typescript
emaSeries = addLineSeries(chart, colours?.emaLine ?? '#FF6D00');
```

- [ ] **Step 6: Add effect to reapply colours when they change**

Add a new `$effect` that watches `colours` and reapplies to existing series:
```typescript
$effect(() => {
  if (!chart || !colours) return;
  const c = colours;

  if (candleSeries) {
    candleSeries.applyOptions({
      upColor: c.candleUpBody,
      downColor: c.candleDownBody,
      borderUpColor: c.candleUpBody,
      borderDownColor: c.candleDownBody,
      wickUpColor: c.candleUpWick,
      wickDownColor: c.candleDownWick,
    });
  }

  if (lineSeries) {
    lineSeries.applyOptions({ color: c.lineColour });
  }

  if (areaSeries) {
    areaSeries.applyOptions({
      topColor: c.areaTop,
      bottomColor: c.areaBottom,
    });
  }

  if (smaSeries) {
    smaSeries.applyOptions({ color: c.smaLine });
  }

  if (emaSeries) {
    emaSeries.applyOptions({ color: c.emaLine });
  }

  // Volume is per-bar, re-map data
  if (volumeSeries && candles.length > 0) {
    volumeSeries.setData(
      candles.map(d => candleOHLCVtoVolumeData(d, c.volumeUp, c.volumeDown))
    );
  }
});
```

- [ ] **Step 7: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

---

### Task 7: Wire up App.svelte

**Files:**
- Modify: `frontend/src/App.svelte`

- [ ] **Step 1: Add imports and state**

Add import:
```typescript
import type { ChartColours } from './lib/chartColours';
import { defaultChartColours } from './lib/chartColours';
```

Add state after existing state declarations:
```typescript
let colours = $state<ChartColours>(defaultChartColours());
```

- [ ] **Step 2: Pass colours to Chart and ChartOptionsMenu**

Add `{colours}` prop to Chart:
```svelte
<Chart
  {candles}
  {symbol}
  {chartType}
  {showArea}
  {smaPoints}
  {emaPoints}
  smaLineWidth={smaConfig.lineWidth}
  emaLineWidth={emaConfig.lineWidth}
  {colours}
/>
```

Add `bind:colours` to ChartOptionsMenu:
```svelte
<ChartOptionsMenu
  bind:chartType
  bind:showArea
  bind:smaConfig
  bind:emaConfig
  bind:colours
/>
```

- [ ] **Step 3: Verify it compiles and runs**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

Run: `cd frontend && npm run dev`
Expected: App loads, chart displays, Chart Options dialog shows colour swatches for active elements. Clicking a swatch opens the native colour picker. Changing a colour updates the chart in real-time.

---

### Task 8: Manual verification

- [ ] **Step 1: Verify conditional visibility**
  - With candlestick selected: 4 candlestick colour swatches visible
  - Switch to line: candlestick swatches gone, 1 line colour swatch visible
  - Toggle area off: area swatches disappear
  - Toggle area on: area swatches appear
  - Enable SMA: SMA line colour swatch appears inline
  - Disable SMA: swatch disappears
  - Same for EMA
  - Volume swatches always visible

- [ ] **Step 2: Verify colour changes apply**
  - Pick a new candlestick up body colour, confirm chart updates
  - Pick a new wick colour, confirm wicks change independently
  - Change volume colour, confirm volume bars update
  - Change SMA/EMA line colour, confirm indicator lines update
  - Toggle dark/light theme, confirm custom colours are preserved
