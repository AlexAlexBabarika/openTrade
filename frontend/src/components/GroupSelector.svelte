<script lang="ts">
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import Pencil from '@lucide/svelte/icons/pencil';
  import Copy from '@lucide/svelte/icons/copy';
  import Eraser from '@lucide/svelte/icons/eraser';
  import Plus from '@lucide/svelte/icons/plus';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import type { TickerGroup } from '../lib/tickers';

  let {
    groups,
    selectedName,
    onselect,
    onrename,
    onduplicate,
    onclear,
    onadd,
    ondelete,
  }: {
    groups: TickerGroup[];
    selectedName: string;
    onselect: (name: string) => void;
    onrename: () => void;
    onduplicate: () => void;
    onclear: () => void;
    onadd: () => void;
    ondelete: () => void;
  } = $props();

  let open = $state(false);
  let rootEl: HTMLDivElement | undefined = $state();

  function close() {
    open = false;
  }

  $effect(() => {
    if (!open) return;
    const handleDown = (e: MouseEvent) => {
      if (rootEl && !rootEl.contains(e.target as Node)) close();
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('mousedown', handleDown);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleDown);
      document.removeEventListener('keydown', handleKey);
    };
  });

  function runAction(fn: () => void) {
    close();
    fn();
  }

  function pickGroup(name: string) {
    onselect(name);
    close();
  }
</script>

<div bind:this={rootEl} class="relative">
  <button
    type="button"
    class="inline-flex items-center gap-1 rounded h-7 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors max-w-[140px]"
    aria-haspopup="menu"
    aria-expanded={open}
    onclick={() => (open = !open)}
  >
    <span class="truncate">{selectedName}</span>
    <ChevronDown class="h-3.5 w-3.5 shrink-0" />
  </button>

  {#if open}
    <div
      class="absolute left-0 top-full mt-1 z-50 w-56 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1"
      role="menu"
    >
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        onclick={() => runAction(onrename)}
      >
        <Pencil class="h-3.5 w-3.5" /> Rename current
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        onclick={() => runAction(onduplicate)}
      >
        <Copy class="h-3.5 w-3.5" /> Duplicate current
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        onclick={() => runAction(onclear)}
      >
        <Eraser class="h-3.5 w-3.5" /> Clear current
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        onclick={() => runAction(onadd)}
      >
        <Plus class="h-3.5 w-3.5" /> Add new group
      </button>
      {#if groups.length > 1}
        <button
          type="button"
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10"
          onclick={() => runAction(ondelete)}
        >
          <Trash2 class="h-3.5 w-3.5" /> Delete current
        </button>
      {/if}

      <div class="my-1 h-px bg-border"></div>

      <div class="max-h-60 overflow-y-auto">
        {#each groups as group (group.name)}
          <button
            type="button"
            class="flex w-full items-center px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground {group.name ===
            selectedName
              ? 'bg-accent/60 text-accent-foreground'
              : ''}"
            onclick={() => pickGroup(group.name)}
          >
            <span class="truncate">{group.name}</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>
