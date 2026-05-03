<script lang="ts">
  import PanelRight from '@lucide/svelte/icons/panel-right';
  import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
  import GitCompare from '@lucide/svelte/icons/git-compare';
  import { Button } from '$lib/components/ui/button';
  import ChartOptionsMenu from '../chart/ChartOptionsMenu.svelte';
  import BottomBarOptionsMenu from './BottomBarOptionsMenu.svelte';
  import type {
    MovingAverageConfig,
    BollingerBandsConfig,
  } from '../chart/ChartOptionsMenu.svelte';
  import type { ChartColours, ChartType } from '$lib/features/chart/chartColours';
  import type { Theme } from '$lib/features/theme/theme';
  import { MAX_COMPARISONS } from '$lib/features/chart/comparisonController.svelte';

  let {
    chartType = $bindable(),
    showArea = $bindable(),
    showVolume = $bindable(),
    smaConfig = $bindable(),
    emaConfig = $bindable(),
    bbandsConfig = $bindable(),
    colours = $bindable(),
    theme,
    onthemechange,
    sidebarVisible,
    ontogglesidebar,
    comparisonCount = 0,
    oncompare,
  }: {
    chartType: ChartType;
    showArea: boolean;
    showVolume: boolean;
    smaConfig: MovingAverageConfig;
    emaConfig: MovingAverageConfig;
    bbandsConfig: BollingerBandsConfig;
    colours: ChartColours;
    theme: Theme;
    onthemechange: (theme: Theme) => void;
    sidebarVisible: boolean;
    ontogglesidebar: () => void;
    comparisonCount?: number;
    oncompare?: () => void;
  } = $props();

  const atLimit = $derived(comparisonCount >= MAX_COMPARISONS);
</script>

<div
  class="relative flex items-center justify-between px-2 py-1 border-t border-border bg-background h-10 shrink-0"
>
  <div class="flex items-center gap-1">
    <ChartOptionsMenu
      bind:chartType
      bind:showArea
      bind:showVolume
      bind:smaConfig
      bind:emaConfig
      bind:bbandsConfig
      bind:colours
      {theme}
      {onthemechange}
    />
    {#if oncompare}
      <Button
        variant="outline"
        size="sm"
        disabled={atLimit}
        onclick={oncompare}
        aria-label="Add comparison symbol"
        title={atLimit
          ? `Maximum ${MAX_COMPARISONS} comparisons`
          : 'Add comparison symbol'}
      >
        <GitCompare class="h-4 w-4" />
      </Button>
    {/if}
  </div>

  <div class="flex items-center gap-1">
    <BottomBarOptionsMenu />
    <Button
      variant="outline"
      size="sm"
      aria-label={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
      onclick={ontogglesidebar}
    >
      {#if sidebarVisible}
        <PanelRightClose class="h-4 w-4" />
      {:else}
        <PanelRight class="h-4 w-4" />
      {/if}
    </Button>
  </div>
</div>
