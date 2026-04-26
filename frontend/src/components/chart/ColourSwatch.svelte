<script lang="ts">
  import { Popover } from 'bits-ui';
  import ColourPicker from './ColourPicker.svelte';

  let {
    colour = $bindable('#000000'),
    label,
  }: {
    colour: string;
    label: string;
  } = $props();
</script>

<Popover.Root>
  <Popover.Trigger
    class="flex items-center gap-2 group outline-none"
    aria-label="Pick colour for {label}"
  >
    <span
      class="block w-6 h-6 rounded border border-border group-hover:border-foreground transition-colors cursor-pointer"
      style="background-color: {colour};"
    ></span>
    <span class="text-xs text-muted-foreground">{label}</span>
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Content
      sideOffset={8}
      class="z-[60] w-64 rounded-lg border border-border bg-card p-4 shadow-xl outline-none"
    >
      <ColourPicker bind:colour />
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
