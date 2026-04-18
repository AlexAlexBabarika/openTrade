<!-- frontend/src/lib/drawables/tools/ruler/Settings.svelte -->
<script lang="ts">
  import type { SettingsProps } from '../../types';
  import type { RulerGeo, RulerParams, RulerStyle } from './tool';

  // Phase 1 stub. Real settings land in Phase 2.
  let {
    drawable: _drawable,
    onChange: _onChange,
    onClose: _onClose,
  }: SettingsProps<RulerGeo, RulerParams, RulerStyle> = $props();
</script>

<div></div>
