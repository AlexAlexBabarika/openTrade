<script lang="ts">
  import type { SettingsProps } from '../../types';
  import type { PositionGeo, PositionParams, PositionStyle } from './compute';
  import ColorField from '../../ui/ColorField.svelte';
  import CheckboxField from '../../ui/CheckboxField.svelte';
  import NumberField from '../../ui/NumberField.svelte';

  let { params, style }: SettingsProps<PositionGeo, PositionParams, PositionStyle> =
    $props();
</script>

<div class="flex flex-col gap-1">
  <div class="text-xs text-muted-foreground mb-1">
    Sizing: leave at 0 to omit. Backend computes quantity when risk or balance +
    % is set.
  </div>
  <NumberField label="Account" bind:value={params.accountBalance} min={0} step={100} />
  <NumberField
    label="Risk %"
    bind:value={params.riskPercent}
    min={0}
    max={100}
    step={0.1}
  />
  <NumberField label="Risk $" bind:value={params.riskAmount} min={0} step={10} />
  <NumberField label="Quantity" bind:value={params.quantity} min={0} step={0.01} />
  <NumberField label="Leverage" bind:value={params.leverage} min={0.1} max={100} step={0.1} />
  <CheckboxField label="Show risk zone" bind:checked={style.showRiskZone} />
  <CheckboxField label="Show reward zone" bind:checked={style.showRewardZone} />
  <CheckboxField label="Show metrics" bind:checked={style.showMetrics} />
  <ColorField label="Risk fill" bind:value={style.riskFill} />
  <ColorField label="Reward fill" bind:value={style.rewardFill} />
  <ColorField label="Entry line" bind:value={style.entryColor} />
  <ColorField label="Stop line" bind:value={style.stopColor} />
  <ColorField label="Target line" bind:value={style.targetColor} />
</div>
