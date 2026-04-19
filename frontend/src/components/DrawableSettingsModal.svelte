<script lang="ts" generics="Geo, Params, Style">
  import * as Dialog from '$lib/components/ui/dialog';
  import { getTool, type Drawable } from '../lib/drawables';
  import ModalFooter from '../lib/drawables/ui/ModalFooter.svelte';

  let {
    drawable,
    open = $bindable<boolean>(false),
    onChange,
    onCancel,
    onOk,
  }: {
    drawable: Drawable<Geo, Params, Style> | null;
    open: boolean;
    onChange: (patch: { params?: Params; style?: Style }) => void;
    onCancel: () => void;
    onOk: () => void;
  } = $props();

  let tool = $derived(drawable ? getTool(drawable.type) : null);
</script>

<Dialog.Root
  {open}
  onOpenChange={(v) => {
    open = v;
    if (!v) onCancel();
  }}
>
  <Dialog.Content class="sm:max-w-md" showCloseButton={false}>
    {#if drawable && tool}
      {@const SettingsCmp = tool.Settings}
      <Dialog.Header>
        <Dialog.Title class="text-lg font-semibold">{tool.label}</Dialog.Title>
      </Dialog.Header>
      <div class="mt-2">
        <SettingsCmp
          {drawable}
          {onChange}
          onClose={onCancel}
        />
      </div>
      <ModalFooter {onCancel} {onOk} />
    {/if}
  </Dialog.Content>
</Dialog.Root>
