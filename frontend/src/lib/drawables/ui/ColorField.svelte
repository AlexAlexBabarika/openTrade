<script lang="ts">
  import Field from './Field.svelte';

  let {
    label,
    value = $bindable<string>('#000000'),
  }: {
    label: string;
    value: string;
  } = $props();

  const inputId = `color-${crypto.randomUUID()}`;

  // Convert any `rgb(...)` defaults the tool ships with to `#rrggbb` so
  // <input type="color"> can display them. Accepts hex untouched.
  function toHex(v: string): string {
    if (v.startsWith('#')) return v;
    const m = v.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/);
    if (!m) return '#000000';
    const hex = (n: string) =>
      Math.max(0, Math.min(255, parseInt(n, 10)))
        .toString(16)
        .padStart(2, '0');
    return `#${hex(m[1])}${hex(m[2])}${hex(m[3])}`;
  }

  let displayed = $derived(toHex(value));
</script>

<Field {label} id={inputId}>
  <input
    id={inputId}
    type="color"
    class="h-7 w-10 cursor-pointer rounded border border-border bg-transparent p-0"
    value={displayed}
    oninput={(e) => (value = (e.currentTarget as HTMLInputElement).value)}
  />
</Field>
