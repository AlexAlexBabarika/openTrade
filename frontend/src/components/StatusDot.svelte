<script lang="ts">
  import type { ConnectionStatus } from '../lib/ws';

  let { status = 'disconnected' }: { status: ConnectionStatus } = $props();

  const labels: Record<ConnectionStatus, string> = {
    connecting: 'Connecting…',
    connected: 'Connected',
    disconnected: 'Disconnected',
    error: 'Error',
  };

  const dotColor: Record<ConnectionStatus, string> = {
    connecting: 'bg-text-muted',
    connected: 'bg-green',
    disconnected: 'bg-text-muted',
    error: 'bg-red',
  };
</script>

<span class="text-xs text-text-muted flex items-center gap-1.5">
  <span class="w-2 h-2 rounded-full {dotColor[status]}"></span>
  {labels[status]}
</span>
