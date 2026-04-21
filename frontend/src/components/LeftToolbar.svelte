<script lang="ts">
  import { Popover } from 'bits-ui';
  import Crosshair from '@lucide/svelte/icons/crosshair';
  import Check from '@lucide/svelte/icons/check';
  import Settings from '@lucide/svelte/icons/settings';
  import X from '@lucide/svelte/icons/x';
  import {
    CROSSHAIR_MODES,
    type CrosshairModeName,
  } from '$lib/features/chart/crosshair';
  import {
    listTools,
    CURSOR,
    type ActiveTool,
    type DrawableToolbarCommands,
  } from '$lib/features/drawables';

  let {
    chartSymbol = '',
    crosshairMode = $bindable<CrosshairModeName>('magnet'),
    activeTool = $bindable<ActiveTool>(CURSOR),
    onToolSettings,
    drawableCommands,
  }: {
    /** Current chart ticker — drawables cleared for this symbol only. */
    chartSymbol?: string;
    crosshairMode: CrosshairModeName;
    activeTool: ActiveTool;
    onToolSettings: (toolType: string) => void;
    /** Injected drawable actions (use `toolbarCommandsFromStore(drawables)` in App; pass fakes in tests). */
    drawableCommands: DrawableToolbarCommands;
  } = $props();

  /** Snapshot at mount; bundled tool list is fixed after `ensureToolsRegistered()`. */
  const tools = listTools();
  let crosshairOpen = $state(false);
  /** Popover open state per tool type — keys must exist for bind:open. */
  let toolPopoverOpen = $state<Record<string, boolean>>(
    Object.fromEntries(tools.map(t => [t.type, false])),
  );

  function selectCrosshair(mode: CrosshairModeName) {
    crosshairMode = mode;
    crosshairOpen = false;
  }

  function activateTool(type: string) {
    activeTool = activeTool === type ? CURSOR : type;
    toolPopoverOpen = { ...toolPopoverOpen, [type]: false };
  }

  function openSettings(type: string) {
    toolPopoverOpen = { ...toolPopoverOpen, [type]: false };
    onToolSettings(type);
  }

  function clearDrawablesForChart() {
    if (!chartSymbol) return;
    drawableCommands.removeAllForSymbol(chartSymbol);
  }
</script>

<div
  class="flex flex-col items-center gap-1 py-1 border-r border-border bg-background w-10 shrink-0 h-full min-h-0"
>
  <Popover.Root bind:open={crosshairOpen}>
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
            onclick={() => selectCrosshair(mode.value)}
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

  {#each tools as tool (tool.type)}
    {@const Icon = tool.icon}
    <Popover.Root bind:open={toolPopoverOpen[tool.type]!}>
      <Popover.Trigger
        type="button"
        class="flex items-center justify-center w-8 h-8 rounded hover:bg-accent transition-colors outline-none {activeTool ===
        tool.type
          ? 'bg-accent text-foreground'
          : 'text-muted-foreground'}"
        aria-label={tool.label}
        aria-pressed={activeTool === tool.type}
      >
        <Icon class="h-4 w-4" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="right"
          align="start"
          sideOffset={10}
          class="z-[60] min-w-[200px] rounded-lg border border-border bg-popover p-1 shadow-xl outline-none"
        >
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="flex flex-1 items-center gap-2 rounded px-2 py-1.5 text-sm text-left hover:bg-accent outline-none"
              onclick={() => activateTool(tool.type)}
            >
              <Icon class="h-4 w-4 text-muted-foreground shrink-0" />
              <span class="flex-1">{tool.label}</span>
              {#if activeTool === tool.type}
                <Check class="h-4 w-4 shrink-0" />
              {/if}
            </button>
            <button
              type="button"
              class="flex items-center justify-center w-8 h-8 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors outline-none"
              aria-label="{tool.label} settings"
              title="{tool.label} settings"
              onclick={() => openSettings(tool.type)}
            >
              <Settings class="h-4 w-4" />
            </button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  {/each}

  <div class="mt-auto flex flex-col items-center pt-2">
    <button
      type="button"
      class="flex items-center justify-center w-8 h-8 rounded-sm bg-destructive hover:bg-destructive/90 transition-colors outline-none shrink-0"
      aria-label="Clear all drawables on chart"
      title="Clear all drawables"
      onclick={clearDrawablesForChart}
    >
      <X
        class="h-4 w-4 text-white dark:text-zinc-950"
        strokeWidth={2.5}
      />
    </button>
  </div>
</div>
