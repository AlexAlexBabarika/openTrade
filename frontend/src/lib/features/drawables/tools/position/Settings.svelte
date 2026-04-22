<script lang="ts">
  import type { SettingsProps } from '../../types';
  import type { PositionGeo, PositionParams, PositionStyle } from './compute';
  import ColorField from '../../ui/ColorField.svelte';

  let { params: _params, style }: SettingsProps<
    PositionGeo,
    PositionParams,
    PositionStyle
  > = $props();
</script>

<div class="flex flex-col gap-1">
  <ColorField label="Target" bind:value={style.targetColor} />
  <ColorField label="Stop" bind:value={style.stopColor} />
</div>
