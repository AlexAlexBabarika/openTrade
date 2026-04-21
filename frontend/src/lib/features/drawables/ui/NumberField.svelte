<script lang="ts">
  import Field from './Field.svelte';

  let {
    label,
    value = $bindable<number>(0),
    min,
    max,
    step,
  }: {
    label: string;
    value: number;
    min?: number;
    max?: number;
    step?: number;
  } = $props();

  const inputId = `num-${crypto.randomUUID()}`;
</script>

<Field {label} id={inputId}>
  <input
    id={inputId}
    type="number"
    class="h-7 w-20 rounded border border-border bg-transparent px-2 text-sm text-right outline-none focus:border-ring"
    {min}
    {max}
    {step}
    value={value}
    oninput={(e) => {
      const n = Number((e.currentTarget as HTMLInputElement).value);
      if (!Number.isNaN(n)) value = n;
    }}
  />
</Field>
