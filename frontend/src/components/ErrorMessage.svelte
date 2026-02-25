<script lang="ts">
  let { message = null }: { message: string | null } = $props();
</script>

{#if message}
  <div class="error-message">{message}</div>
{/if}

<style>
  .error-message {
    padding: 1rem;
    color: var(--red);
    background: rgba(239, 83, 80, 0.1);
    border-radius: 6px;
    margin: 1rem;
  }
</style>
