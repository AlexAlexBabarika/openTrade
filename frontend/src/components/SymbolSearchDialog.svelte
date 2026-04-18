<script lang="ts">
  import { untrack, tick } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Dialog from '$lib/components/ui/dialog';
  import ProviderBadges from './ProviderBadges.svelte';
  import {
    searchSymbols,
    type SymbolSearchResult,
    type SymbolProviders,
  } from '../lib/symbols';

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

  let query = $state('');
  let results = $state<SymbolSearchResult[]>([]);
  let highlighted = $state(0);
  let loading = $state(false);
  let errorMsg = $state<string | null>(null);
  let inputEl = $state<HTMLInputElement | null>(null);
  let activeController: AbortController | null = null;

  $effect(() => {
    if (open) {
      query = untrack(() => '');
      results = [];
      highlighted = 0;
      errorMsg = null;
      void tick().then(() => inputEl?.focus());
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
    loading = true;
    errorMsg = null;
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const id = setTimeout(() => {
      searchSymbols(q, 20, controller.signal)
        .then(list => {
          if (controller.signal.aborted) return;
          results = list;
          highlighted = 0;
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

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (results.length > 0) {
        highlighted = (highlighted + 1) % results.length;
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (results.length > 0) {
        highlighted = (highlighted - 1 + results.length) % results.length;
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results.length > 0) {
        const r = results[highlighted];
        submit(r.symbol, r.providers);
      } else if (showAddAnyway) {
        submit(normalizedQuery, null);
      }
    }
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
    <div class="mt-2">
      <Input
        bind:ref={inputEl}
        bind:value={query}
        placeholder="e.g. NVDA, BTCUSDT, NVIDIA"
        onkeydown={onKeydown}
        autocomplete="off"
        spellcheck={false}
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

    <div class="mt-3 max-h-72 overflow-y-auto rounded border border-border">
      {#if !normalizedQuery}
        <div class="px-3 py-6 text-center text-xs text-muted-foreground">
          Start typing to search the directory.
        </div>
      {:else if loading && results.length === 0}
        <div class="px-3 py-6 text-center text-xs text-muted-foreground">
          Searching…
        </div>
      {:else if results.length > 0}
        <ul class="divide-y divide-border">
          {#each results as r, i (r.symbol)}
            <li>
              <button
                type="button"
                class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm {i ===
                highlighted
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent/50'}"
                onmouseenter={() => (highlighted = i)}
                onclick={() => submit(r.symbol, r.providers)}
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
              </button>
            </li>
          {/each}
        </ul>
      {:else if showAddAnyway}
        <div class="px-3 py-4">
          <p class="text-xs text-muted-foreground">
            <span class="font-mono font-semibold text-foreground"
              >{normalizedQuery.toUpperCase()}</span
            > isn't in our directory. It may not be supported by any provider.
          </p>
          <Button
            variant="outline"
            size="sm"
            class="mt-2"
            onclick={() => submit(normalizedQuery, null)}
          >
            Add {normalizedQuery.toUpperCase()} anyway
          </Button>
        </div>
      {/if}
    </div>

    <Dialog.Footer class="mt-4">
      <Button variant="outline" type="button" onclick={() => onopenchange(false)}>
        Cancel
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
