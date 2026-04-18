<script lang="ts">
  import { Popover } from 'bits-ui';
  import Crosshair from '@lucide/svelte/icons/crosshair';
  import Check from '@lucide/svelte/icons/check';
  import {
    CROSSHAIR_MODES,
    type CrosshairModeName,
  } from '../lib/crosshair';

  let {
    crosshairMode = $bindable<CrosshairModeName>('magnet'),
  }: {
    crosshairMode: CrosshairModeName;
  } = $props();

  let open = $state(false);

  function select(mode: CrosshairModeName) {
    crosshairMode = mode;
    open = false;
  }
</script>

<div
  class="flex flex-col items-center gap-1 py-1 border-r border-border bg-background w-10 shrink-0"
>
  <Popover.Root bind:open>
    <Popover.Trigger
      class="flex items-center justify-center w-8 h-8 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors outline-none"
      aria-label="Crosshair mode"
    >
      <Crosshair class="h-4 w-4" />
    </Popover.Trigger>
    <Popover.Portal>
      <Popover.Content
        side="right"
        align="start"
        sideOffset={10}
        class="z-[60] min-w-[180px] rounded-lg border border-border bg-popover p-1 shadow-xl outline-none"
      >
        {#each CROSSHAIR_MODES as mode (mode.value)}
          {@const Icon = mode.icon}
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-left hover:bg-accent outline-none"
            onclick={() => select(mode.value)}
          >
            <Icon class="h-4 w-4 text-muted-foreground shrink-0" />
            <span class="flex-1">{mode.label}</span>
            {#if crosshairMode === mode.value}
              <Check class="h-4 w-4 shrink-0" />
            {/if}
          </button>
        {/each}
      </Popover.Content>
    </Popover.Portal>
  </Popover.Root>
</div>
