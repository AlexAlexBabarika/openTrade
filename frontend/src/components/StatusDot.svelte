<script lang="ts">
  import type { ConnectionStatus } from '../lib/ws';

  let { status = 'disconnected' }: { status: ConnectionStatus } = $props();

  const labels: Record<ConnectionStatus, string> = {
    connecting: 'Connecting…',
    connected: 'Connected',
    disconnected: 'Disconnected',
    error: 'Error',
  };
</script>

<span class="status">
  <span
    class="status-dot"
    class:connected={status === 'connected'}
    class:error={status === 'error'}
  ></span>
  {labels[status]}
</span>

<style>
  .status {
    font-size: 0.8rem;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
  }

  .status-dot.connected {
    background: var(--green);
  }

  .status-dot.error {
    background: var(--red);
  }
</style>
