<script lang="ts">
  import Pencil from '@lucide/svelte/icons/pencil';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import type { TickerNote } from '../lib/notes';

  let {
    notes,
    onedit,
    ondelete,
  }: {
    notes: TickerNote[];
    onedit: (note: TickerNote) => void;
    ondelete: (id: string) => void;
  } = $props();

  let expanded = $state(false);

  let visible = $derived(expanded ? notes : notes.slice(0, 2));
  let hiddenCount = $derived(Math.max(0, notes.length - 2));

  function formatRelative(ts: number): string {
    const diff = Date.now() - ts;
    const m = Math.floor(diff / 60_000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    if (d < 7) return `${d}d ago`;
    return new Date(ts).toLocaleDateString();
  }
</script>

<div class="mt-3 flex flex-col gap-1.5">
  {#if notes.length === 0}
    <div class="text-[11px] text-muted-foreground italic">No notes yet.</div>
  {:else}
    {#each visible as note (note.id)}
      <div
        class="group relative rounded-md bg-muted/60 border border-border/50 px-2.5 py-2"
      >
        <div class="flex items-start gap-2">
          <div class="min-w-0 flex-1">
            {#if note.title}
              <div class="text-xs font-semibold text-foreground truncate">
                {note.title}
              </div>
            {/if}
            <div
              class="text-xs text-foreground/90 whitespace-pre-wrap break-words"
            >
              {note.body}
            </div>
            <div class="mt-1 text-[10px] text-muted-foreground">
              {formatRelative(note.createdAt)}
              {#if note.updatedAt > note.createdAt}
                · edited
              {/if}
            </div>
          </div>
          <div
            class="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
          >
            <button
              type="button"
              class="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              aria-label="Edit note"
              onclick={() => onedit(note)}
            >
              <Pencil class="h-3 w-3" />
            </button>
            <button
              type="button"
              class="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              aria-label="Delete note"
              onclick={() => ondelete(note.id)}
            >
              <Trash2 class="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    {/each}
    {#if hiddenCount > 0}
      <button
        type="button"
        class="mt-0.5 inline-flex items-center justify-center gap-1 rounded px-2 py-1 text-[11px] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        onclick={() => (expanded = !expanded)}
      >
        <ChevronDown
          class="h-3 w-3 transition-transform {expanded ? 'rotate-180' : ''}"
        />
        {expanded ? 'Show less' : `Show ${hiddenCount} more`}
      </button>
    {/if}
  {/if}
</div>
