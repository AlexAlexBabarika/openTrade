<script lang="ts">
  import * as Dialog from '$lib/components/ui/dialog';
  import {
    getTool,
    drawables,
    saveToolDefaults,
    type Drawable,
  } from '../lib/drawables';
  import ModalFooter from '../lib/drawables/ui/ModalFooter.svelte';

  let {
    toolType,
    open = $bindable<boolean>(false),
  }: {
    toolType: string | null;
    open: boolean;
  } = $props();

  let tool = $derived(toolType ? getTool(toolType) : null);

  // Staged copies live for the lifetime of the open modal. Cleared on close.
  let stagedParams = $state<unknown>(null);
  let stagedStyle = $state<unknown>(null);
  let lastOpenedType: string | null = null;

  $effect(() => {
    if (open && tool && lastOpenedType !== tool.type) {
      stagedParams = JSON.parse(JSON.stringify(tool.defaults.params));
      stagedStyle = JSON.parse(JSON.stringify(tool.defaults.style));
      lastOpenedType = tool.type;
    }
    if (!open) {
      lastOpenedType = null;
    }
  });

  function applyAndClose(): void {
    if (!tool || !toolType) {
      open = false;
      return;
    }
    const nextParams = stagedParams;
    const nextStyle = stagedStyle;

    // Update registry defaults so new drawables use the latest.
    tool.defaults.params = nextParams as typeof tool.defaults.params;
    tool.defaults.style = nextStyle as typeof tool.defaults.style;

    saveToolDefaults(toolType, { params: nextParams, style: nextStyle });

    for (const d of drawables.items) {
      if (d.type === toolType) {
        drawables.update(d.id, {
          params: JSON.parse(JSON.stringify(nextParams)),
          style: JSON.parse(JSON.stringify(nextStyle)),
        } as Partial<Drawable>);
      }
    }

    open = false;
  }

  function cancel(): void {
    open = false;
  }
</script>

<Dialog.Root
  {open}
  onOpenChange={(v) => {
    open = v;
  }}
>
  <Dialog.Content class="sm:max-w-md" showCloseButton={false}>
    {#if tool && stagedParams !== null && stagedStyle !== null}
      {@const SettingsCmp = tool.Settings}
      <Dialog.Header>
        <Dialog.Title class="text-lg font-semibold"
          >{tool.label} settings</Dialog.Title
        >
      </Dialog.Header>
      <div class="mt-2">
        <SettingsCmp params={stagedParams} style={stagedStyle} />
      </div>
      <ModalFooter onCancel={cancel} onOk={applyAndClose} />
    {/if}
  </Dialog.Content>
</Dialog.Root>
