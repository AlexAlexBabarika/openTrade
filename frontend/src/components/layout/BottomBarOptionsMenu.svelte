<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';

  let open = $state(false);
</script>

<Button variant="outline" size="sm" onclick={() => (open = true)}>
  Options
</Button>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Options</Dialog.Title>
    </Dialog.Header>
    <div class="flex flex-col gap-4"></div>
  </Dialog.Content>
</Dialog.Root>
