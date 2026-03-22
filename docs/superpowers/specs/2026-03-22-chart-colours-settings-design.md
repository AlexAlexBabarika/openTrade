# Chart Colours Settings

## Summary

Add user-configurable colour settings to the Chart Options dialog. Colour swatches appear as small coloured squares with descriptive labels, only for currently active/enabled chart elements. Clicking a swatch opens the native browser colour picker. Changes are session-only (no persistence).

## Colour Elements

| Element | Colours | Visible When |
|---------|---------|-------------|
| Candlestick | Up body, Down body, Up wick, Down wick | `chartType === 'candlestick'` |
| Line chart | Line colour | `chartType === 'line'` |
| Area overlay | Top gradient, Bottom gradient | `showArea === true` |
| Volume | Up volume, Down volume | Always (volume always shown) |
| SMA | Line colour | `smaConfig.enabled === true` |
| EMA | Line colour | `emaConfig.enabled === true` |

## Data Model

```typescript
export interface ChartColours {
  // Candlestick
  candleUpBody: string;
  candleDownBody: string;
  candleUpWick: string;
  candleDownWick: string;
  // Line chart
  lineColour: string;
  // Area overlay
  areaTop: string;
  areaBottom: string;
  // Volume
  volumeUp: string;
  volumeDown: string;
  // Indicators
  smaLine: string;
  emaLine: string;
}
```

Default values:
- Candlestick up/down body and wick: read from CSS variables `--up-color` / `--down-color` via `getCssVarColor()`
- Line colour: read from CSS variable `--foreground` (theme-dependent; frozen at init for the session)
- Area top/bottom: read from CSS variables `--area-top-color` / `--area-bottom-color`
- Volume up/down: hardcoded hex with alpha (`#26a63130` up, `#c21a2a30` down) -- these are per-bar colours set in `chartAdapters.ts`, not per-series
- SMA: `#2962FF`, EMA: `#FF6D00`

## UI Design

Colour swatches are placed inline within the Chart Options dialog, grouped under each feature section:

- **Swatch**: 24x24px coloured square with rounded corners (4px) and subtle border
- **Label**: Small text next to the swatch describing what it colours (e.g. "Up body", "Down wick")
- **Picker**: Hidden `<input type="color">` triggered by clicking the swatch
- **Grouping**: Colour swatches appear in a flex-wrap row beneath each feature's existing controls
- **Conditional rendering**: Each group uses Svelte `{#if}` to only render when the parent feature is active

### Layout within dialog

```
Chart Type: [Candlestick] [Line]
  Candlestick Colours:  [green] Up body  [red] Down body  [green] Up wick  [red] Down wick

Overlay: [Area]
  Area Colours:  [purple] Top gradient  [purple] Bottom gradient

Volume Colours:  [green] Up volume  [red] Down volume

Moving Averages:
  SMA [enabled] Width 2 Period 20  [blue] Line
  EMA [disabled]  (no colour shown)
```

## Data Flow

1. `App.svelte` owns `ChartColours` state via `$state()`, initialized with defaults from CSS variables
2. `ChartOptionsMenu.svelte` receives `colours` as `$bindable` prop, renders swatches, updates on picker change
3. `Chart.svelte` receives `colours` as a prop, uses values when creating/updating series instead of reading CSS variables directly
4. On theme change (dark/light toggle), colours are NOT reset -- user's custom choices are preserved for the session

## Implementation Notes

- **Volume colours are per-bar**, not per-series. `candleOHLCVtoVolumeData()` in `chartAdapters.ts` sets colour on each data point. The volume colour overrides must be passed into this mapping function.
- **`syncChartTheme()`** currently re-reads CSS variables on theme toggle. With custom colours, it should use `ChartColours` as the single source of truth instead of re-reading CSS variables for series colours.

## Files Modified

- `frontend/src/components/ChartOptionsMenu.svelte` -- add ChartColours interface, colour swatch UI with conditional rendering
- `frontend/src/components/Chart.svelte` -- accept colours prop, use it in series creation and updates
- `frontend/src/lib/chart.ts` -- modify `addCandlestickSeries`, `addAreaSeries`, `addLineSeries`, `syncChartTheme` to accept colour overrides
- `frontend/src/lib/chartAdapters.ts` -- modify `candleOHLCVtoVolumeData` to accept volume colour overrides
- `frontend/src/App.svelte` -- initialize ChartColours state, pass to both components

## Scope Exclusions

- No colour persistence (localStorage, backend, etc.)
- No custom colour picker component (uses native `<input type="color">`)
- No colour presets or themes
