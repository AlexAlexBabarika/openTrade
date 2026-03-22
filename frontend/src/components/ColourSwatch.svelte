<!-- frontend/src/components/ColourSwatch.svelte -->
<script lang="ts">
  let {
    colour = $bindable('#000000'),
    label,
  }: {
    colour: string;
    label: string;
  } = $props();

  let inputEl: HTMLInputElement | undefined = $state();

  /** Extract hex RGB from any CSS colour string for the native picker */
  function toHex6(c: string): string {
    // Handle #RRGGBBAA or #RRGGBB
    if (c.startsWith('#')) {
      const hex = c.slice(1);
      if (hex.length >= 6) return '#' + hex.slice(0, 6);
    }
    // Handle rgb()/rgba() — parse via canvas
    const ctx = document.createElement('canvas').getContext('2d');
    if (ctx) {
      ctx.fillStyle = c;
      return ctx.fillStyle; // returns #rrggbb
    }
    return '#000000';
  }

  /** Get alpha suffix from original colour (if any) */
  function getAlphaSuffix(c: string): string {
    if (c.startsWith('#') && c.length === 9) {
      return c.slice(7, 9);
    }
    return '';
  }

  function handleInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    const alpha = getAlphaSuffix(colour);
    colour = val + alpha;
  }
</script>

<button
  type="button"
  class="flex items-center gap-2 group"
  onclick={() => inputEl?.click()}
  aria-label="Pick colour for {label}"
>
  <span
    class="block w-6 h-6 rounded border border-border group-hover:border-foreground transition-colors cursor-pointer"
    style="background-color: {colour};"
  ></span>
  <span class="text-xs text-muted-foreground">{label}</span>
  <input
    bind:this={inputEl}
    type="color"
    value={toHex6(colour)}
    oninput={handleInput}
    class="sr-only"
    tabindex={-1}
  />
</button>
