<script lang="ts">
  import type { Snippet } from 'svelte';
  import ColorBends from '$lib/features/chart/ColorBends.svelte';

  let {
    colors,
    title,
    rotation = 0,
    autoRotate = 0,
    showBends = true,
    children,
  }: {
    colors: string[];
    title?: string;
    rotation?: number;
    autoRotate?: number;
    showBends?: boolean;
    children?: Snippet;
  } = $props();
</script>

<div
  class="relative isolate overflow-hidden rounded-lg border border-border bg-foreground/5 p-6 aspect-square font-mono"
>
  {#if showBends}
    <div
      class="absolute inset-0 -z-10 overflow-hidden rounded-lg opacity-50 mix-blend-screen"
    >
      <ColorBends
        {colors}
        speed={0.00}
        intensity={0.55}
        noise={0.1}
        bandWidth={5}
        warpStrength={0.9}
        parallax={0.25}
        mouseInfluence={0.4}
        {autoRotate}
        {rotation}
      />
    </div>
    <div
      class="absolute inset-0 -z-10 overflow-hidden rounded-lg bg-gradient-to-br from-black/40 via-black/25 to-black/55"
    ></div>
  {/if}
  {#if children}
    {@render children()}
  {:else if title}
    <h3
      class="relative text-base font-medium tracking-tight drop-shadow-[0_1px_2px_rgba(0,0,0,0.6)]"
    >
      {title}
    </h3>
  {/if}
</div>
