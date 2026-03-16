<script lang="ts">
  import StatusDot from './StatusDot.svelte';
  import AuthDialog from './AuthDialog.svelte';
  import ApiKeysModal from './ApiKeysModal.svelte';
  import type { ConnectionStatus } from '../lib/ws';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import * as Select from '$lib/components/ui/select';
  import { authState, logout } from '$lib/auth';
  import { LoaderCircle } from 'lucide-svelte';

  type DataSource = 'yfinance' | 'csv';

  let {
    symbol = $bindable('AAPL'),
    period = $bindable('1mo'),
    interval = $bindable('1d'),
    source = $bindable('yfinance' as DataSource),
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
    source: DataSource;
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
  let fileName = $state('Choose CSV');

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
    <Select.Trigger class="w-32">
      {source}
    </Select.Trigger>
    <Select.Content>
      <Select.Item value="yfinance">yfinance</Select.Item>
      <Select.Item value="csv">CSV</Select.Item>
    </Select.Content>
  </Select.Root>

  {#if source === 'csv'}
    <div class="relative">
      <input
        type="file"
        accept=".csv"
        bind:this={fileInput}
        onchange={handleFileChange}
        class="absolute opacity-0 w-full h-full cursor-pointer z-10"
      />
      <Button variant="outline" class="pointer-events-none">
        {fileName}
      </Button>
    </div>
  {/if}

  <Button onclick={handleLoad} disabled={isLoading}>
    {#if isLoading}
      <LoaderCircle class="mr-1 h-4 w-4 animate-spin" />
    {/if}
    {isLoading ? 'Loading…' : 'Load'}
  </Button>
  <Button variant="secondary" onclick={onstream}>Stream WS</Button>

  <div class="flex items-center space-x-2">
    <Checkbox id="auto-refresh" bind:checked={autoRefresh} />
    <Label
      for="auto-refresh"
      class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    >
      Auto-refresh 60s
    </Label>
  </div>

  <StatusDot status={connectionStatus} />

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
