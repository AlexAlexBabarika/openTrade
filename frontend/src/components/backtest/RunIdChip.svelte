<script lang="ts">
  import { truncateRunId } from '$lib/features/runs/format';

  let { runId, onCompare }: { runId: string; onCompare?: () => void } = $props();

  let copied = $state(false);
  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(runId);
      copied = true;
      setTimeout(() => (copied = false), 1200);
    } catch {
      /* clipboard unavailable */
    }
  }
</script>

<span class="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground">
  <button type="button" title={runId} onclick={copy} class="hover:text-foreground">
    run {truncateRunId(runId)}{copied ? ' ✓' : ''}
  </button>
  {#if onCompare}
    <button type="button" class="underline hover:text-foreground" onclick={onCompare}>compare…</button>
  {/if}
</span>
