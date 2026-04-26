<script lang="ts">
  import CircleAlert from '@lucide/svelte/icons/circle-alert';
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';
  import GlitchText from './GlitchText.svelte';

  let {
    message = $bindable<string | null>(null),
  }: {
    message: string | null;
  } = $props();
</script>

<Dialog.Root
  open={message !== null}
  onOpenChange={v => {
    if (!v) message = null;
  }}
>
  <Dialog.Content class="sm:max-w-md" showCloseButton={false}>
    <Dialog.Header>
      <div class="flex items-center justify-between gap-3">
        <Dialog.Title class="min-w-0 shrink text-lg font-semibold leading-none">
          <GlitchText text="Error" />
        </Dialog.Title>
        <Button
          variant="destructive"
          class="shrink-0"
          onclick={() => (message = null)}
        >
          Close
        </Button>
      </div>
    </Dialog.Header>

    <div
      class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive flex gap-2 items-center"
    >
      <CircleAlert class="size-4 shrink-0" strokeWidth={2} aria-hidden="true" />
      <p class="leading-relaxed">{message}</p>
    </div>
  </Dialog.Content>
</Dialog.Root>
