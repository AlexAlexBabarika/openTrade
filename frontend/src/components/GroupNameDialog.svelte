<script lang="ts">
  import { untrack } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Dialog from '$lib/components/ui/dialog';

  let {
    open = $bindable(false),
    title,
    initialValue = '',
    existingNames = [],
    placeholder = 'Group name',
    duplicateMessage = 'A group with this name already exists.',
    onsubmit,
  }: {
    open: boolean;
    title: string;
    initialValue?: string;
    existingNames?: string[];
    placeholder?: string;
    duplicateMessage?: string;
    onsubmit: (name: string) => void;
  } = $props();

  let value = $state('');

  $effect(() => {
    if (open) value = untrack(() => initialValue);
  });

  let trimmed = $derived(value.trim());
  let isDuplicate = $derived(
    trimmed.length > 0 &&
      trimmed !== initialValue.trim() &&
      existingNames.includes(trimmed),
  );
  let isValid = $derived(trimmed.length > 0 && !isDuplicate);

  function confirm() {
    if (!isValid) return;
    onsubmit(trimmed);
    open = false;
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>{title}</Dialog.Title>
    </Dialog.Header>
    <form
      onsubmit={e => {
        e.preventDefault();
        confirm();
      }}
    >
      <Input
        bind:value
        {placeholder}
        class="mt-2"
        autofocus
      />
      {#if isDuplicate}
        <p class="mt-2 text-xs text-destructive">{duplicateMessage}</p>
      {/if}
      <Dialog.Footer class="mt-4">
        <Button variant="outline" type="button" onclick={() => (open = false)}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isValid}>Save</Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
