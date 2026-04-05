<script lang="ts">
  import AuthDialog from './AuthDialog.svelte';
  import ApiKeysModal from './ApiKeysModal.svelte';
  import type { ConnectionStatus } from '../lib/ws';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Select from '$lib/components/ui/select';
  import { authState, logout } from '$lib/auth';
  import {
    MARKET_DATA_PROVIDERS,
    type MarketDataProviderValue,
  } from '$lib/marketDataProviders';
  import {
    DEFAULT_MARKET_INTERVAL,
    MARKET_INTERVAL_OPTIONS,
  } from '$lib/marketIntervals';
  import {
    DEFAULT_MARKET_PERIOD,
    MARKET_PERIOD_OPTIONS,
  } from '$lib/marketPeriods';
  import LoaderCircle from '@lucide/svelte/icons/loader-circle';

  let {
    symbol = $bindable('AAPL'),
    period = $bindable(DEFAULT_MARKET_PERIOD),
    interval = $bindable(DEFAULT_MARKET_INTERVAL),
    source = $bindable('yfinance' as MarketDataProviderValue),
    autoRefresh = $bindable(false),
    connectionStatus = 'disconnected' as ConnectionStatus,
    isLoading = false,
    onload = () => {},
    onstream = () => {},
    oncsvupload = (_file: File) => {},
  }: {
    symbol: string;
    period: string;
    interval: string;
    source: MarketDataProviderValue;
    autoRefresh: boolean;
    connectionStatus: ConnectionStatus;
    isLoading: boolean;
    onload: () => void;
    onstream: () => void;
    oncsvupload: (file: File) => void;
  } = $props();

  let authDialogOpen = $state(false);
  let apiKeysModalOpen = $state(false);
  let currentUser = $derived($authState.user);

  async function handleLogout() {
    await logout();
  }

  let fileInput: HTMLInputElement | undefined = $state();
  let fileName = $state('Choose file');

  function handleLoad() {
    if (source === 'csv') {
      fileInput?.click();
    } else {
      onload();
    }
  }

  function handleFileChange() {
    const file = fileInput?.files?.[0];
    if (!file) return;
    fileName = file.name;
    oncsvupload(file);
  }
</script>

<div
  class="flex items-center gap-4 px-4 py-3 bg-background border-b border-border flex-wrap relative z-40"
>
  <div class="w-32">
    <Input type="text" placeholder="Symbol (e.g. AAPL)" bind:value={symbol} />
  </div>

  <Select.Root type="single" bind:value={period}>
    <Select.Trigger class="w-24">
      {MARKET_PERIOD_OPTIONS.find(p => p.value === period)?.label ?? period}
    </Select.Trigger>
    <Select.Content>
      {#each MARKET_PERIOD_OPTIONS as p (p.value)}
        <Select.Item value={p.value}>{p.label}</Select.Item>
      {/each}
    </Select.Content>
  </Select.Root>

  <Select.Root type="single" bind:value={interval}>
    <Select.Trigger class="w-20">
      {MARKET_INTERVAL_OPTIONS.find(i => i.value === interval)?.label ?? interval}
    </Select.Trigger>
    <Select.Content>
      {#each MARKET_INTERVAL_OPTIONS as i (i.value)}
        <Select.Item value={i.value}>{i.label}</Select.Item>
      {/each}
    </Select.Content>
  </Select.Root>

  <Select.Root type="single" bind:value={source}>
    <Select.Trigger class="w-36">
      {MARKET_DATA_PROVIDERS.find(p => p.value === source)?.label ?? source}
    </Select.Trigger>
    <Select.Content>
      {#each MARKET_DATA_PROVIDERS as p (p.value)}
        <Select.Item value={p.value}>{p.label}</Select.Item>
      {/each}
    </Select.Content>
  </Select.Root>

  <input
    type="file"
    accept=".csv,text/csv"
    class="hidden"
    bind:this={fileInput}
    onchange={handleFileChange}
  />
  <Button onclick={handleLoad} disabled={isLoading}>
    {#if isLoading}
      <LoaderCircle class="mr-1 h-4 w-4 animate-spin" />
    {/if}
    {isLoading ? 'Loading…' : source === 'csv' ? fileName : 'Load'}
  </Button>

  <Button
    variant="secondary"
    size="sm"
    onclick={onstream}
    disabled={source === 'csv' ? false : !symbol.trim()}
    title="Replay cached OHLCV over WebSocket (load data first unless using yfinance)"
  >
    Stream
    {#if connectionStatus === 'connecting'}
      <span class="ml-1 text-xs text-muted-foreground">…</span>
    {:else if connectionStatus === 'connected'}
      <span class="ml-1 h-2 w-2 rounded-full bg-green-500 inline-block" title="Connected"></span>
    {:else if connectionStatus === 'error'}
      <span class="ml-1 text-xs text-destructive">!</span>
    {/if}
  </Button>

  <div class="ml-auto flex items-center gap-2">
    {#if currentUser}
      <Button variant="outline" size="sm" onclick={() => (apiKeysModalOpen = true)}>
        API Keys
      </Button>
      <span class="text-sm text-muted-foreground truncate max-w-[160px]">
        {currentUser.email}
      </span>
      <Button variant="ghost" size="sm" onclick={handleLogout}>
        Sign out
      </Button>
    {:else}
      <Button variant="outline" size="sm" onclick={() => (authDialogOpen = true)}>
        Sign in
      </Button>
    {/if}
  </div>
</div>

<AuthDialog bind:open={authDialogOpen} />
<ApiKeysModal bind:open={apiKeysModalOpen} />
