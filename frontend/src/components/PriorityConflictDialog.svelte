<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';
  import type { PriorityConflict, TickerPriority } from '$lib/features/market/tickers';

  let {
    open,
    onopenchange,
    conflict,
    desired,
    onkeepexisting,
    onswitchgroup,
  }: {
    open: boolean;
    onopenchange: (open: boolean) => void;
    conflict: PriorityConflict | null;
    desired: TickerPriority | null;
    onkeepexisting: () => void;
    onswitchgroup: (groupName: string) => void;
  } = $props();

  let otherGroup = $derived(conflict?.groups[0] ?? '');
</script>

<Dialog.Root {open} onOpenChange={onopenchange}>
  <Dialog.Content class="sm:max-w-md">
    {#if conflict && desired}
      <Dialog.Header>
        <Dialog.Title>Priority conflict</Dialog.Title>
        <Dialog.Description>
          <span class="font-semibold">{conflict.symbol}</span> already has
          priority
          <span class="capitalize font-semibold">
            "{conflict.existingPriority}"
          </span>
          in group
          <span class="font-semibold">"{otherGroup}"</span>. A ticker must carry
          the same priority across every group it belongs to.
        </Dialog.Description>
      </Dialog.Header>
      <div class="text-sm text-muted-foreground">
        You can either set <span class="capitalize font-semibold"
          >{conflict.existingPriority}</span
        >
        here too, or change {conflict.symbol}'s priority in
        <span class="font-semibold">{otherGroup}</span> first.
      </div>
      <Dialog.Footer class="mt-4 flex-col gap-2 sm:flex-row">
        <Button
          variant="outline"
          type="button"
          onclick={() => onopenchange(false)}
        >
          Cancel
        </Button>
        <Button
          variant="outline"
          type="button"
          onclick={() => onswitchgroup(otherGroup)}
        >
          Change in "{otherGroup}"
        </Button>
        <Button type="button" onclick={onkeepexisting}>
          Set "<span class="capitalize">{conflict.existingPriority}</span>" here
        </Button>
      </Dialog.Footer>
    {/if}
  </Dialog.Content>
</Dialog.Root>
