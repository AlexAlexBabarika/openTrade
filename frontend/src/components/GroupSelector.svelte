<script lang="ts">
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import Pencil from '@lucide/svelte/icons/pencil';
  import Copy from '@lucide/svelte/icons/copy';
  import Eraser from '@lucide/svelte/icons/eraser';
  import Plus from '@lucide/svelte/icons/plus';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import Flag from '@lucide/svelte/icons/flag';
  import Check from '@lucide/svelte/icons/check';
  import { DropdownMenu } from 'bits-ui';
  import type {
    TickerGroup,
    GroupActions,
    FlaggedPriority,
  } from '$lib/features/market/tickers';
  import {
    FLAGGED_PRIORITIES,
    PRIORITY_COLOURS,
  } from '$lib/features/market/tickers';

  let {
    groups,
    selectedName,
    selectedPriority,
    priorityCounts,
    actions,
    onselectpriority,
  }: {
    groups: TickerGroup[];
    selectedName: string;
    selectedPriority: FlaggedPriority | null;
    priorityCounts: Record<FlaggedPriority, number>;
    actions: GroupActions;
    onselectpriority: (p: FlaggedPriority) => void;
  } = $props();
</script>

<DropdownMenu.Root>
  <DropdownMenu.Trigger
    class="inline-flex items-center gap-1 rounded h-7 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors max-w-[140px] outline-none"
  >
    {#if selectedPriority}
      {@const colour = PRIORITY_COLOURS[selectedPriority]}
      <Flag
        class="h-3 w-3 shrink-0"
        style="color: {colour}; fill: {colour};"
      />
      <span class="truncate capitalize">{selectedPriority}</span>
    {:else}
      <span class="truncate">{selectedName}</span>
    {/if}
    <ChevronDown class="h-3.5 w-3.5 shrink-0" />
  </DropdownMenu.Trigger>
  <DropdownMenu.Portal>
    <DropdownMenu.Content
      align="start"
      sideOffset={4}
      class="z-50 w-56 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1 outline-none"
    >
      {#if !selectedPriority}
        <DropdownMenu.Item
          onSelect={actions.rename}
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
        >
          <Pencil class="h-3.5 w-3.5" /> Rename current
        </DropdownMenu.Item>
        <DropdownMenu.Item
          onSelect={actions.duplicate}
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
        >
          <Copy class="h-3.5 w-3.5" /> Duplicate current
        </DropdownMenu.Item>
        <DropdownMenu.Item
          onSelect={actions.clear}
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
        >
          <Eraser class="h-3.5 w-3.5" /> Clear current
        </DropdownMenu.Item>
      {/if}
      <DropdownMenu.Item
        onSelect={actions.add}
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
      >
        <Plus class="h-3.5 w-3.5" /> Add new group
      </DropdownMenu.Item>
      {#if !selectedPriority && groups.length > 1}
        <DropdownMenu.Item
          onSelect={actions.delete}
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive data-[highlighted]:bg-destructive/10 cursor-default outline-none"
        >
          <Trash2 class="h-3.5 w-3.5" /> Delete current
        </DropdownMenu.Item>
      {/if}

      <DropdownMenu.Separator class="my-1 h-px bg-border" />

      <div class="max-h-60 overflow-y-auto">
        {#each groups as group (group.name)}
          <DropdownMenu.Item
            onSelect={() => actions.select(group.name)}
            class="flex w-full items-center px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none {!selectedPriority &&
            group.name === selectedName
              ? 'bg-accent/60 text-accent-foreground'
              : ''}"
          >
            <span class="truncate">{group.name}</span>
          </DropdownMenu.Item>
        {/each}
      </div>

      <DropdownMenu.Separator class="my-1 h-px bg-border" />
      <div
        class="px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground"
      >
        By priority
      </div>
      {#each FLAGGED_PRIORITIES as p (p)}
        {@const colour = PRIORITY_COLOURS[p]}
        <DropdownMenu.Item
          onSelect={() => onselectpriority(p)}
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none {selectedPriority ===
          p
            ? 'bg-accent/60 text-accent-foreground'
            : ''}"
        >
          <Flag
            class="h-3.5 w-3.5 shrink-0"
            style="color: {colour}; fill: {colour};"
          />
          <span class="flex-1 text-left capitalize">{p}</span>
          <span class="text-xs text-muted-foreground tabular-nums">
            {priorityCounts[p]}
          </span>
          {#if selectedPriority === p}
            <Check class="h-3.5 w-3.5" />
          {/if}
        </DropdownMenu.Item>
      {/each}
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>
