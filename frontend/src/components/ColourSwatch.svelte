<script lang="ts">
  import ColourPicker from './ColourPicker.svelte';

  let {
    colour = $bindable('#000000'),
    label,
  }: {
    colour: string;
    label: string;
  } = $props();

  let open = $state(false);
  let btnEl: HTMLButtonElement | undefined = $state();

  function toggle() {
    open = !open;
  }

  function getAnchor(): DOMRect {
    return btnEl!.getBoundingClientRect();
  }
</script>

<button
  bind:this={btnEl}
  type="button"
  class="flex items-center gap-2 group"
  onclick={toggle}
  aria-label="Pick colour for {label}"
>
  <span
    class="block w-6 h-6 rounded border border-border group-hover:border-foreground transition-colors cursor-pointer"
    style="background-color: {colour};"
  ></span>
  <span class="text-xs text-muted-foreground">{label}</span>
</button>

{#if open}
  <ColourPicker
    bind:colour
    anchor={getAnchor()}
    onclose={() => (open = false)}
  />
{/if}
