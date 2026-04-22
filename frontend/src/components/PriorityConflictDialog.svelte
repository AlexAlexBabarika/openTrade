<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';

  type TagConflictField = 'priority' | 'stance';

  let {
    open,
    onopenchange,
    field,
    conflict,
    onkeepexisting,
    onswitchgroup,
  }: {
    open: boolean;
    onopenchange: (open: boolean) => void;
    field: TagConflictField;
    conflict: { symbol: string; existing: string; groups: string[] } | null;
    onkeepexisting: () => void;
    onswitchgroup: (groupName: string) => void;
  } = $props();

  let otherGroup = $derived(conflict?.groups[0] ?? '');
  let title = $derived(
    field === 'priority' ? 'Priority conflict' : 'Stance conflict',
  );
  let noun = $derived(field === 'priority' ? 'priority' : 'stance');
</script>

<Dialog.Root {open} onOpenChange={onopenchange}>
  <Dialog.Content class="sm:max-w-md">
    {#if conflict}
      <Dialog.Header>
        <Dialog.Title>{title}</Dialog.Title>
        <Dialog.Description>
          <span class="font-semibold">{conflict.symbol}</span> already has
          {noun}
          <span class="capitalize font-semibold">
            "{conflict.existing}"
          </span>
          in group
          <span class="font-semibold">"{otherGroup}"</span>. A ticker must carry
          the same {noun} across every group it belongs to.
        </Dialog.Description>
      </Dialog.Header>
      <div class="text-sm text-muted-foreground">
        You can either set <span class="capitalize font-semibold"
          >{conflict.existing}</span
        >
        here too, or change {conflict.symbol}'s {noun} in
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
          Set "<span class="capitalize">{conflict.existing}</span>" here
        </Button>
      </Dialog.Footer>
    {/if}
  </Dialog.Content>
</Dialog.Root>
