<script lang="ts">
  import type { SettingsProps } from '../../types';
  import type { RulerGeo, RulerParams, RulerStyle } from './tool';
  import ColorField from '../../ui/ColorField.svelte';
  import CheckboxField from '../../ui/CheckboxField.svelte';

  let {
    drawable,
    onChange,
  }: SettingsProps<RulerGeo, RulerParams, RulerStyle> = $props();

  // Mirror style into local bindable state so the inputs stay controlled
  // even as onChange re-propagates the value through the drawable prop.
  let upColor = $state(drawable.style.upColor);
  let downColor = $state(drawable.style.downColor);
  let showStats = $state(drawable.style.showStats);

  $effect(() => {
    upColor;
    downColor;
    showStats;
    onChange({ style: { upColor, downColor, showStats } });
  });
</script>

<div class="flex flex-col">
  <ColorField label="Up colour" bind:value={upColor} />
  <ColorField label="Down colour" bind:value={downColor} />
  <CheckboxField label="Show stats" bind:checked={showStats} />
</div>
