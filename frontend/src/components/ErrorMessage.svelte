<script lang="ts">
  let { message = null }: { message: string | null } = $props();
</script>

{#if message}
  <div class="p-4 text-red-500 bg-red-500/10 rounded-md mx-4 my-4">
    {message}
  </div>
{/if}
