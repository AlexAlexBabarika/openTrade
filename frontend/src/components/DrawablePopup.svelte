<script lang="ts">
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import Settings from '@lucide/svelte/icons/settings';
  import type { PopupAction, ScreenPoint } from '../lib/drawables';

  let {
    anchor,
    actions,
    onAction,
  }: {
    anchor: ScreenPoint;
    actions: PopupAction[];
    onAction: (id: PopupAction['id'], action: PopupAction) => void;
  } = $props();

  const ICONS: Record<string, typeof Trash2> = {
    settings: Settings,
    delete: Trash2,
  };

  // Place the popup 8px below and a few px left of the anchor corner.
  const OFFSET_X = -8;
  const OFFSET_Y = 8;
</script>

<div
  class="absolute z-20 flex items-center gap-0.5 rounded-md border border-border bg-popover px-1 py-1 shadow-lg"
  style:left="{anchor.x + OFFSET_X}px"
  style:top="{anchor.y + OFFSET_Y}px"
  role="toolbar"
  aria-label="Drawable actions"
  onpointerdown={(e) => e.stopPropagation()}
>
  {#each actions as action (action.id)}
    {@const Icon = ICONS[action.id] ?? Settings}
    <button
      type="button"
      class="flex items-center justify-center w-7 h-7 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors outline-none"
      aria-label={action.label}
      title={action.label}
      onclick={(e) => { e.stopPropagation(); onAction(action.id, action); }}
    >
      <Icon class="h-4 w-4" />
    </button>
  {/each}
</div>
