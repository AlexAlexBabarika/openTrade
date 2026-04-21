<script lang="ts">
  let {
    x,
    y,
    width,
    height,
    drawableId,
    ariaLabel,
    onPointerDown,
    mode = 'fill' as 'fill' | 'stroke',
    strokeHitWidth = 10,
  }: {
    x: number;
    y: number;
    width: number;
    height: number;
    drawableId: string;
    ariaLabel: string;
    onPointerDown: (e: PointerEvent) => void;
    mode?: 'fill' | 'stroke';
    strokeHitWidth?: number;
  } = $props();
</script>

<rect
  {x}
  {y}
  {width}
  {height}
  fill="transparent"
  stroke="transparent"
  stroke-width={mode === 'stroke' ? strokeHitWidth : 0}
  pointer-events={mode === 'stroke' ? 'stroke' : 'auto'}
  data-drawable-id={drawableId}
  role="button"
  tabindex="-1"
  aria-label={ariaLabel}
  onpointerdown={onPointerDown}
  style:cursor="pointer"
/>
