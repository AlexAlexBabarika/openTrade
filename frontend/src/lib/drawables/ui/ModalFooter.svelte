<script lang="ts">
  import { Button } from '$lib/components/ui/button';

  let {
    onCancel,
    onOk,
  }: {
    onCancel: () => void;
    onOk: () => void;
  } = $props();
</script>

<div class="flex items-center justify-end gap-2 pt-4">
  <Button variant="ghost" onclick={onCancel}>Cancel</Button>
  <Button onclick={onOk}>Ok</Button>
</div>
