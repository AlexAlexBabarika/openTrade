<script lang="ts">
  import PanelRight from '@lucide/svelte/icons/panel-right';
  import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
  import { Button } from '$lib/components/ui/button';
  import ChartOptionsMenu from './ChartOptionsMenu.svelte';
  import type {
    MovingAverageConfig,
    BollingerBandsConfig,
  } from './ChartOptionsMenu.svelte';
  import type { ChartColours, ChartType } from '../lib/chartColours';

  let {
    chartType = $bindable(),
    showArea = $bindable(),
    showVolume = $bindable(),
    smaConfig = $bindable(),
    emaConfig = $bindable(),
    bbandsConfig = $bindable(),
    colours = $bindable(),
    sidebarVisible,
    ontogglesidebar,
  }: {
    chartType: ChartType;
    showArea: boolean;
    showVolume: boolean;
    smaConfig: MovingAverageConfig;
    emaConfig: MovingAverageConfig;
    bbandsConfig: BollingerBandsConfig;
    colours: ChartColours;
    sidebarVisible: boolean;
    ontogglesidebar: () => void;
  } = $props();
</script>

<div
  class="flex items-center justify-between px-2 py-1 border-t border-border bg-background h-10 shrink-0"
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
    />
  </div>
  <div class="flex items-center gap-1">
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
