<script lang="ts">
  import { untrack } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Dialog from '$lib/components/ui/dialog';

  let {
    open,
    onopenchange,
    title,
    description,
    initialValue = '',
    existingNames = [],
    placeholder = '',
    duplicateMessage = 'A value with this name already exists.',
    normalize = (v: string) => v,
    onsubmit,
  }: {
    open: boolean;
    onopenchange: (open: boolean) => void;
    title: string;
    description?: string;
    initialValue?: string;
    existingNames?: string[];
    placeholder?: string;
    duplicateMessage?: string;
    normalize?: (value: string) => string;
    onsubmit: (value: string) => void;
  } = $props();

  let value = $state('');

  $effect(() => {
    if (open) value = untrack(() => initialValue);
  });

  let trimmed = $derived(normalize(value.trim()));
  let isDuplicate = $derived(
    trimmed.length > 0 &&
      trimmed !== normalize(initialValue.trim()) &&
      existingNames.includes(trimmed),
  );
  let isValid = $derived(trimmed.length > 0 && !isDuplicate);

  function confirm() {
    if (!isValid) return;
    onsubmit(trimmed);
    onopenchange(false);
  }
</script>

<Dialog.Root {open} onOpenChange={onopenchange}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>{title}</Dialog.Title>
      {#if description}
        <Dialog.Description>{description}</Dialog.Description>
      {/if}
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
        <Button variant="outline" type="button" onclick={() => onopenchange(false)}>
          Cancel
        </Button>
        <Button type="submit" disabled={!isValid}>Save</Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
