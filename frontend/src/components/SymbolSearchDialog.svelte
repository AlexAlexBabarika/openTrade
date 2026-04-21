<script lang="ts">
  import { Command } from 'bits-ui';
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';
  import ProviderBadges from './ProviderBadges.svelte';
  import {
    searchSymbols,
    type SymbolSearchResult,
    type SymbolProviders,
  } from '$lib/features/market/symbols';

  let {
    open,
    onopenchange,
    existingSymbols = [],
    onsubmit,
  }: {
    open: boolean;
    onopenchange: (open: boolean) => void;
    existingSymbols?: string[];
    onsubmit: (symbol: string, providers: SymbolProviders | null) => void;
  } = $props();

  const DEBOUNCE_MS = 200;
  const ADD_ANYWAY_VALUE = '__add_anyway__';

  let query = $state('');
  let results = $state<SymbolSearchResult[]>([]);
  let loading = $state(false);
  let errorMsg = $state<string | null>(null);

  $effect(() => {
    if (open) {
      query = '';
      results = [];
      errorMsg = null;
    }
  });

  let normalizedQuery = $derived(query.trim());
  let existingSet = $derived(new Set(existingSymbols.map(s => s.toUpperCase())));
  let isDuplicate = $derived(
    normalizedQuery.length > 0 &&
      existingSet.has(normalizedQuery.toUpperCase()),
  );

  let showAddAnyway = $derived(
    !loading &&
      !isDuplicate &&
      normalizedQuery.length > 0 &&
      results.length === 0,
  );

  $effect(() => {
    const q = normalizedQuery;
    if (!open) return;
    if (!q) {
      results = [];
      loading = false;
      return;
    }
    const controller = new AbortController();
    const id = setTimeout(() => {
      loading = true;
      errorMsg = null;
      searchSymbols(q, 20, controller.signal)
        .then(list => {
          if (controller.signal.aborted) return;
          results = list;
        })
        .catch(e => {
          if (controller.signal.aborted) return;
          results = [];
          errorMsg = e instanceof Error ? e.message : 'Search failed';
        })
        .finally(() => {
          if (!controller.signal.aborted) loading = false;
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(id);
      controller.abort();
    };
  });

  function submit(sym: string, providers: SymbolProviders | null) {
    const cleaned = sym.trim().toUpperCase();
    if (!cleaned) return;
    if (existingSet.has(cleaned)) return;
    onsubmit(cleaned, providers);
    onopenchange(false);
  }
</script>

<Dialog.Root {open} onOpenChange={onopenchange}>
  <Dialog.Content class="sm:max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Add symbol</Dialog.Title>
      <Dialog.Description>
        Search by ticker or name. Badges show which providers support each symbol.
      </Dialog.Description>
    </Dialog.Header>

    <Command.Root shouldFilter={false} loop class="mt-2 flex flex-col gap-3">
      <div>
        <Command.Input
          bind:value={query}
          autofocus
          placeholder="e.g. NVDA, BTCUSDT, NVIDIA"
          autocomplete="off"
          spellcheck={false}
          class="border-input bg-background placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 flex h-9 w-full min-w-0 rounded-md border px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-[3px] md:text-sm"
        />
        {#if isDuplicate}
          <p class="mt-2 text-xs text-destructive">
            This symbol is already in the group.
          </p>
        {/if}
        {#if errorMsg}
          <p class="mt-2 text-xs text-destructive">{errorMsg}</p>
        {/if}
      </div>

      <Command.List class="max-h-72 overflow-y-auto rounded border border-border">
        {#if !normalizedQuery}
          <div class="px-3 py-6 text-center text-xs text-muted-foreground">
            Start typing to search the directory.
          </div>
        {:else if loading && results.length === 0}
          <div class="px-3 py-6 text-center text-xs text-muted-foreground">
            Searching…
          </div>
        {:else if results.length > 0}
          <div class="divide-y divide-border">
            {#each results as r (r.symbol)}
              <Command.Item
                value={r.symbol}
                onSelect={() => submit(r.symbol, r.providers)}
                class="flex w-full cursor-pointer items-center justify-between gap-3 px-3 py-2 text-left text-sm outline-none data-[selected]:bg-accent data-[selected]:text-accent-foreground"
              >
                <span class="min-w-0 flex-1">
                  <span class="font-mono font-semibold">{r.symbol}</span>
                  <span class="ml-2 truncate text-muted-foreground">{r.name}</span>
                  {#if r.exchange}
                    <span class="ml-2 text-[10px] uppercase text-muted-foreground/70">
                      {r.exchange}
                    </span>
                  {/if}
                </span>
                <ProviderBadges providers={r.providers} />
              </Command.Item>
            {/each}
          </div>
        {:else if showAddAnyway}
          <div class="px-3 py-4">
            <p class="text-xs text-muted-foreground">
              <span class="font-mono font-semibold text-foreground"
                >{normalizedQuery.toUpperCase()}</span
              > isn't in our directory. It may not be supported by any provider.
            </p>
            <Command.Item
              value={ADD_ANYWAY_VALUE}
              onSelect={() => submit(normalizedQuery, null)}
              class="mt-2 inline-block outline-none"
            >
              {#snippet child({ props })}
                <Button variant="outline" size="sm" {...props}>
                  Add {normalizedQuery.toUpperCase()} anyway
                </Button>
              {/snippet}
            </Command.Item>
          </div>
        {/if}
      </Command.List>
    </Command.Root>

    <Dialog.Footer class="mt-4">
      <Button variant="outline" type="button" onclick={() => onopenchange(false)}>
        Cancel
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
