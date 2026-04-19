<script lang="ts">
  import type { Snippet } from 'svelte';
  let {
    label,
    children,
    id,
  }: {
    label: string;
    children: Snippet;
    id?: string;
  } = $props();
</script>

<div class="flex items-center justify-between gap-4 py-1.5">
  <label for={id} class="text-sm text-muted-foreground">{label}</label>
  <div class="flex items-center gap-2">
    {@render children()}
  </div>
</div>
