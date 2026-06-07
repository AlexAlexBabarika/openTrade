<script lang="ts">
  import {
    RESULT_TABS,
    type BacktestState,
  } from '$lib/features/backtest/backtestState.svelte';
  import EquityTab from './tabs/EquityTab.svelte';
  import DrawdownTab from './tabs/DrawdownTab.svelte';
  import TradesTab from './tabs/TradesTab.svelte';
  import MonthlyTab from './tabs/MonthlyTab.svelte';
  import MetricsGrid from './MetricsGrid.svelte';

  let { backtest }: { backtest: BacktestState } = $props();

  const result = $derived(backtest.result);
</script>

{#if result}
  <div class="tabs">
    <div class="tabbar" role="tablist">
      {#each RESULT_TABS as t (t.id)}
        <button
          type="button"
          role="tab"
          class="tab"
          class:active={backtest.activeTab === t.id}
          aria-selected={backtest.activeTab === t.id}
          onclick={() => backtest.setTab(t.id)}
        >
          {t.label}
        </button>
      {/each}
    </div>

    <div class="pane">
      {#if backtest.activeTab === 'equity'}
        <EquityTab {result} />
      {:else if backtest.activeTab === 'drawdown'}
        <DrawdownTab {result} />
      {:else if backtest.activeTab === 'trades'}
        <TradesTab {result} {backtest} />
      {:else if backtest.activeTab === 'monthly'}
        <MonthlyTab {result} />
      {:else if backtest.activeTab === 'stats'}
        <MetricsGrid metrics={result.metrics} />
      {/if}
    </div>
  </div>
{/if}

<style>
  .tabs {
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
  }
  .tabbar {
    display: flex;
    gap: 2px;
    padding: 0 10px;
    border-bottom: 1px solid
      color-mix(in oklab, oklch(var(--border)) 100%, transparent);
  }
  .tab {
    position: relative;
    padding: 9px 14px;
    border: 0;
    background: transparent;
    color: oklch(var(--muted-foreground));
    font-family: inherit;
    font-size: 11.5px;
    letter-spacing: 0.06em;
    cursor: pointer;
    transition: color 120ms ease;
  }
  .tab:hover {
    color: oklch(var(--foreground));
  }
  .tab.active {
    color: oklch(var(--foreground));
  }
  .tab.active::after {
    content: '';
    position: absolute;
    left: 8px;
    right: 8px;
    bottom: -1px;
    height: 2px;
    background: oklch(var(--primary));
    border-radius: 2px 2px 0 0;
  }
  .pane {
    flex: 1 1 auto;
    min-height: 0;
  }

  :global(html:not(.dark)) .tabbar {
    border-bottom-color: #000;
  }
</style>
