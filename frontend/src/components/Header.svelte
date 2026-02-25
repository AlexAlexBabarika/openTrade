<script lang="ts">
  import StatusDot from './StatusDot.svelte';
  import type { ConnectionStatus } from '../lib/ws';

  type DataSource = 'yfinance' | 'csv';

  let {
    symbol = $bindable('AAPL'),
    period = $bindable('1mo'),
    interval = $bindable('1d'),
    source = $bindable('yfinance' as DataSource),
    autoRefresh = $bindable(false),
    connectionStatus = 'disconnected' as ConnectionStatus,
    onload = () => {},
    onstream = () => {},
    oncsvupload = (_file: File) => {},
  }: {
    symbol: string;
    period: string;
    interval: string;
    source: DataSource;
    autoRefresh: boolean;
    connectionStatus: ConnectionStatus;
    onload: () => void;
    onstream: () => void;
    oncsvupload: (file: File) => void;
  } = $props();

  let fileInput: HTMLInputElement;
  let fileName = $state('Choose CSV');

  function handleLoad() {
    if (source === 'csv') {
      fileInput.click();
    } else {
      onload();
    }
  }

  function handleFileChange() {
    const file = fileInput.files?.[0];
    if (!file) return;
    fileName = file.name;
    oncsvupload(file);
  }

  const inputClasses =
    'px-3 py-2 border border-border-custom rounded-md bg-bg text-text-primary text-sm font-[family-name:var(--font-family-lato)] focus:outline-none focus:border-accent';
  const btnClasses =
    'px-3 py-2 border rounded-md text-sm cursor-pointer font-medium font-[family-name:var(--font-family-lato)]';
</script>

<div
  class="flex items-center gap-4 px-4 py-3 bg-surface border-b border-border-custom flex-wrap"
>
  <input
    type="text"
    placeholder="Symbol (e.g. AAPL)"
    bind:value={symbol}
    class={inputClasses}
  />

  <select bind:value={period} class={inputClasses}>
    <option value="1d">1D</option>
    <option value="5d">5D</option>
    <option value="1mo">1M</option>
    <option value="3mo">3M</option>
    <option value="6mo">6M</option>
    <option value="1y">1Y</option>
  </select>

  <select bind:value={interval} class={inputClasses}>
    <option value="1d">1d</option>
    <option value="1h">1h</option>
    <option value="5m">5m</option>
  </select>

  <select bind:value={source} class={inputClasses}>
    <option value="yfinance">yfinance</option>
    <option value="csv">CSV</option>
  </select>

  {#if source === 'csv'}
    <div class="relative">
      <input
        type="file"
        accept=".csv"
        bind:this={fileInput}
        onchange={handleFileChange}
        class="absolute opacity-0 w-full h-full cursor-pointer"
      />
      <span
        class="inline-block px-3 py-2 border border-dashed border-border-custom rounded-md cursor-pointer text-text-muted text-sm hover:border-accent hover:text-text-primary transition-colors"
      >
        {fileName}
      </span>
    </div>
  {/if}

  <button
    class="{btnClasses} bg-accent border-accent text-white hover:brightness-110"
    onclick={handleLoad}
  >
    Load
  </button>

  <button
    class="{btnClasses} bg-surface border-border-custom text-text-primary hover:brightness-110"
    onclick={onstream}
  >
    Stream WS
  </button>

  <label class="inline-flex items-center gap-1.5 text-sm text-text-muted">
    <input
      type="checkbox"
      bind:checked={autoRefresh}
      title="Re-fetch yfinance every 60s"
    />
    Auto-refresh 60s
  </label>

  <StatusDot status={connectionStatus} />
</div>
