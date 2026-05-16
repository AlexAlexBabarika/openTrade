<script lang="ts">
  import * as Dialog from '$lib/components/ui/dialog';
  import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';

  let open = $state(false);
</script>

<button
  type="button"
  class="ot-workbench-ghost"
  onclick={() => (open = true)}
  title="More options"
>
  <SlidersHorizontal class="h-3 w-3" />
  <span>more</span>
</button>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Options</Dialog.Title>
    </Dialog.Header>
    <div class="flex flex-col gap-4"></div>
  </Dialog.Content>
</Dialog.Root>
