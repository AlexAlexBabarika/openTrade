<script lang="ts">
  import { drawables } from './store.svelte';
  import { loadAll, saveAll } from './persistence';

  drawables.replaceAll(loadAll());

  $effect(() => {
    const items = drawables.items;
    const id = setTimeout(() => {
      saveAll(items);
    }, 500);
    return () => clearTimeout(id);
  });
</script>
