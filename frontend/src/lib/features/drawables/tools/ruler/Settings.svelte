<script lang="ts">
  import type { SettingsProps } from '../../types';
  import type { RulerGeo, RulerParams, RulerStyle } from './tool';
  import ColorField from '../../ui/ColorField.svelte';
  import CheckboxField from '../../ui/CheckboxField.svelte';

  let { style }: SettingsProps<RulerGeo, RulerParams, RulerStyle> = $props();
</script>

<div class="flex flex-col">
  <ColorField label="Up colour" bind:value={style.upColor} />
  <ColorField label="Down colour" bind:value={style.downColor} />
  <CheckboxField label="Show stats" bind:checked={style.showStats} />
</div>
