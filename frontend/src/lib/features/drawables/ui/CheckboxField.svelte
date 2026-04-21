<script lang="ts">
  import { Checkbox } from '$lib/components/ui/checkbox';
  import Field from './Field.svelte';

  let {
    label,
    checked = $bindable<boolean>(false),
  }: {
    label: string;
    checked: boolean;
  } = $props();

  const inputId = `cb-${crypto.randomUUID()}`;
</script>

<Field {label} id={inputId}>
  <Checkbox id={inputId} bind:checked />
</Field>
