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
</script>

<div class="header">
  <input type="text" placeholder="Symbol (e.g. AAPL)" bind:value={symbol} />

  <select bind:value={period}>
    <option value="1d">1D</option>
    <option value="5d">5D</option>
    <option value="1mo">1M</option>
    <option value="3mo">3M</option>
    <option value="6mo">6M</option>
    <option value="1y">1Y</option>
  </select>

  <select bind:value={interval}>
    <option value="1d">1d</option>
    <option value="1h">1h</option>
    <option value="5m">5m</option>
  </select>

  <select bind:value={source}>
    <option value="yfinance">yfinance</option>
    <option value="csv">CSV</option>
  </select>

  {#if source === 'csv'}
    <div class="file-input-wrap">
      <input
        type="file"
        accept=".csv"
        bind:this={fileInput}
        onchange={handleFileChange}
      />
      <span class="file-label">{fileName}</span>
    </div>
  {/if}

  <button onclick={handleLoad}>Load</button>
  <button class="secondary" onclick={onstream}>Stream WS</button>

  <label class="refresh-label">
    <input
      type="checkbox"
      bind:checked={autoRefresh}
      title="Re-fetch yfinance every 60s"
    />
    Auto-refresh 60s
  </label>

  <StatusDot status={connectionStatus} />
</div>

<style>
  .header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }

  .header input,
  .header select,
  .header button {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
    font-size: 0.9rem;
    font-family: 'Lato', 'Segoe UI', system-ui, sans-serif;
  }

  .header input:focus,
  .header select:focus {
    outline: none;
    border-color: var(--accent);
  }

  .header button {
    cursor: pointer;
    background: var(--accent);
    border-color: var(--accent);
    font-weight: 500;
  }

  .header button:hover {
    filter: brightness(1.1);
  }

  .header button.secondary {
    background: var(--surface);
    border-color: var(--border);
  }

  .refresh-label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .file-input-wrap {
    position: relative;
  }

  .file-input-wrap input[type='file'] {
    position: absolute;
    opacity: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
  }

  .file-input-wrap .file-label {
    display: inline-block;
    padding: 0.5rem 0.75rem;
    border: 1px dashed var(--border);
    border-radius: 6px;
    cursor: pointer;
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .file-input-wrap:hover .file-label {
    border-color: var(--accent);
    color: var(--text);
  }
</style>
