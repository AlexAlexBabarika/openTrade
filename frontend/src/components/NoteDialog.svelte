<script lang="ts">
  import { untrack } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Dialog from '$lib/components/ui/dialog';

  let {
    open,
    onopenchange,
    mode,
    symbol,
    initialTitle = '',
    initialBody = '',
    onsubmit,
  }: {
    open: boolean;
    onopenchange: (open: boolean) => void;
    mode: 'create' | 'edit';
    symbol: string;
    initialTitle?: string;
    initialBody?: string;
    onsubmit: (title: string | undefined, body: string) => void;
  } = $props();

  let title = $state('');
  let body = $state('');

  $effect(() => {
    if (open) {
      title = untrack(() => initialTitle);
      body = untrack(() => initialBody);
    }
  });

  let bodyTrimmed = $derived(body.trim());
  let isValid = $derived(bodyTrimmed.length > 0);

  function confirm() {
    if (!isValid) return;
    const t = title.trim();
    onsubmit(t.length > 0 ? t : undefined, bodyTrimmed);
    onopenchange(false);
  }
</script>

<Dialog.Root {open} onOpenChange={onopenchange}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>
        {mode === 'create' ? 'New note' : 'Edit note'}
        {#if symbol}
          <span class="font-mono text-muted-foreground">— {symbol}</span>
        {/if}
      </Dialog.Title>
    </Dialog.Header>
    <form
      onsubmit={e => {
        e.preventDefault();
        confirm();
      }}
    >
      <Input
        bind:value={title}
        placeholder="Title (optional)"
        class="mt-2"
        autofocus
      />
      <textarea
        bind:value={body}
        placeholder="Write your note…"
        rows="5"
        class="mt-2 flex w-full min-w-0 resize-y rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30"
        onkeydown={e => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            confirm();
          }
        }}
      ></textarea>
      <Dialog.Footer class="mt-4">
        <Button
          variant="outline"
          type="button"
          onclick={() => onopenchange(false)}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={!isValid}>
          {mode === 'create' ? 'Save' : 'Update'}
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
