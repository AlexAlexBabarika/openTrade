<script lang="ts">
  let {
    show = false,
    title = '',
    price = '',
    date = '',
    volume = '',
    textColour = undefined as string | undefined,
  }: {
    show?: boolean;
    title: string;
    price: string;
    date: string;
    volume: string;
    textColour?: string;
  } = $props();
</script>

{#if show}
  <div
    class="absolute left-4 top-4 z-10 text-sm font-light pointer-events-none font-mono leading-[18px]"
    style:color={textColour}
  >
    <div class="text-2xl my-1 font-medium">{title}</div>
    <div class="text-[22px] my-1 font-semibold font-mono">{price}</div>
    <div style:opacity="0.7" class="font-mono">{date}</div>
    <div style:opacity="0.7" class="font-mono">Volume: {volume}</div>
  </div>
{/if}
