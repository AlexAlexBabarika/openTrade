<script lang="ts">
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import Pencil from '@lucide/svelte/icons/pencil';
  import Copy from '@lucide/svelte/icons/copy';
  import Eraser from '@lucide/svelte/icons/eraser';
  import Plus from '@lucide/svelte/icons/plus';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import { DropdownMenu } from 'bits-ui';
  import type { TickerGroup, GroupActions } from '../lib/tickers';

  let {
    groups,
    selectedName,
    actions,
  }: {
    groups: TickerGroup[];
    selectedName: string;
    actions: GroupActions;
  } = $props();
</script>

<DropdownMenu.Root>
  <DropdownMenu.Trigger
    class="inline-flex items-center gap-1 rounded h-7 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors max-w-[140px] outline-none"
  >
    <span class="truncate">{selectedName}</span>
    <ChevronDown class="h-3.5 w-3.5 shrink-0" />
  </DropdownMenu.Trigger>
  <DropdownMenu.Portal>
    <DropdownMenu.Content
      align="start"
      sideOffset={4}
      class="z-50 w-56 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1 outline-none"
    >
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
      <DropdownMenu.Item
        onSelect={actions.add}
        class="flex w-full items-center gap-2 px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none"
      >
        <Plus class="h-3.5 w-3.5" /> Add new group
      </DropdownMenu.Item>
      {#if groups.length > 1}
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
            class="flex w-full items-center px-3 py-1.5 text-sm data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground cursor-default outline-none {group.name ===
            selectedName
              ? 'bg-accent/60 text-accent-foreground'
              : ''}"
          >
            <span class="truncate">{group.name}</span>
          </DropdownMenu.Item>
        {/each}
      </div>
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>
