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
  import { LoaderCircle } from 'lucide-svelte';

  let {
    symbol = $bindable('AAPL'),
    period = $bindable('1mo'),
    interval = $bindable('1d'),
    source = $bindable('yfinance' as MarketDataProviderValue),
    autoRefresh = $bindable(false),
    isLoading = false,
    onload = () => {},
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
      {period}
    </Select.Trigger>
    <Select.Content>
      <Select.Item value="1d">1D</Select.Item>
      <Select.Item value="5d">5D</Select.Item>
      <Select.Item value="1mo">1M</Select.Item>
      <Select.Item value="3mo">3M</Select.Item>
      <Select.Item value="6mo">6M</Select.Item>
      <Select.Item value="1y">1Y</Select.Item>
    </Select.Content>
  </Select.Root>

  <Select.Root type="single" bind:value={interval}>
    <Select.Trigger class="w-20">
      {interval}
    </Select.Trigger>
    <Select.Content>
      <Select.Item value="1d">1d</Select.Item>
      <Select.Item value="1h">1h</Select.Item>
      <Select.Item value="5m">5m</Select.Item>
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
