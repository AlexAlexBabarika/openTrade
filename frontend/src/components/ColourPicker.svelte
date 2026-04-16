<script lang="ts">
  import { cssColourToHsva, hsvaToHex, hsvaToRgba, type HSVA } from '../lib/colourUtils';

  let {
    colour = $bindable('#000000'),
    anchor,
    onclose,
  }: {
    colour: string;
    anchor: DOMRect;
    onclose: () => void;
  } = $props();

  const PRESETS = [
    '#ef4444', '#f97316', '#eab308', '#22c55e',
    '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
  ];

  const POPOVER_W = 256;
  const POPOVER_H = 320;
  const PAD = 16;
  const GRAD_W = 224;
  const GRAD_H = 150;
  const STRIP_H = 14;

  let hsva: HSVA = $state(cssColourToHsva(colour));
  let hexInput: string = $state(colour.startsWith('#') ? colour : hsvaToHex(cssColourToHsva(colour)));
  let popoverEl: HTMLDivElement | undefined = $state();

  // Position calculation
  let top = $derived.by(() => {
    const spaceBelow = window.innerHeight - anchor.bottom - 8;
    if (spaceBelow >= POPOVER_H + PAD) return anchor.bottom + 8;
    return anchor.top - POPOVER_H - 8;
  });

  let left = $derived.by(() => {
    let l = anchor.left;
    if (l + POPOVER_W > window.innerWidth - PAD) {
      l = window.innerWidth - POPOVER_W - PAD;
    }
    if (l < PAD) l = PAD;
    return l;
  });

  // Sync HSVA → colour prop + hex input
  function emitColour() {
    const hex = hsvaToHex(hsva);
    colour = hex;
    hexInput = hex;
  }

  type DragKind = 'grad' | 'hue' | 'alpha';
  let dragging = $state<DragKind | null>(null);

  function makeDrag(
    kind: DragKind,
    applyDelta: (rect: DOMRect, e: PointerEvent) => Partial<HSVA>,
  ) {
    function update(e: PointerEvent, rect: DOMRect) {
      hsva = { ...hsva, ...applyDelta(rect, e) };
      emitColour();
    }
    return {
      down(e: PointerEvent) {
        dragging = kind;
        const el = e.currentTarget as HTMLElement;
        el.setPointerCapture(e.pointerId);
        update(e, el.getBoundingClientRect());
      },
      move(e: PointerEvent) {
        if (dragging !== kind) return;
        update(e, (e.currentTarget as HTMLElement).getBoundingClientRect());
      },
      up() {
        if (dragging === kind) dragging = null;
      },
    };
  }

  const grad = makeDrag('grad', (rect, e) => {
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
    return { s: x / rect.width, v: 1 - y / rect.height };
  });

  const hue = makeDrag('hue', (rect, e) => {
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    return { h: (x / rect.width) * 360 };
  });

  const alpha = makeDrag('alpha', (rect, e) => {
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    return { a: x / rect.width };
  });

  // --- Hex input ---
  function handleHexInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    hexInput = val;
    if (/^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(val)) {
      hsva = cssColourToHsva(val);
      colour = val;
    }
  }

  // --- Preset click ---
  function pickPreset(hex: string) {
    hsva = cssColourToHsva(hex);
    emitColour();
  }

  // --- Click outside ---
  function handleWindowClick(e: MouseEvent) {
    if (popoverEl && !popoverEl.contains(e.target as Node)) {
      onclose();
    }
  }

  // --- Escape ---
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation();
      onclose();
    }
  }

  $effect(() => {
    window.addEventListener('pointerdown', handleWindowClick, true);
    window.addEventListener('keydown', handleKeydown);
    return () => {
      window.removeEventListener('pointerdown', handleWindowClick, true);
      window.removeEventListener('keydown', handleKeydown);
    };
  });

  // When an ancestor has a CSS `transform` (e.g. bits-ui Dialog.Content uses
  // translate(-50%, -50%)), `position: fixed` resolves against that ancestor's
  // padding box instead of the viewport. Recover the viewport coords of the
  // fixed-positioning origin so `anchor` (a viewport-coord DOMRect) still
  // places the popover correctly.
  let fixedOrigin = $state({ x: 0, y: 0 });

  function measureOrigin() {
    if (!popoverEl) return;
    const rect = popoverEl.getBoundingClientRect();
    const cs = getComputedStyle(popoverEl);
    const appliedTop = parseFloat(cs.top) || 0;
    const appliedLeft = parseFloat(cs.left) || 0;
    const originX = rect.left - appliedLeft;
    const originY = rect.top - appliedTop;
    // Tolerance avoids a reactive feedback loop when sub-pixel rounding
    // flips the measured origin back and forth across renders.
    if (
      Math.abs(originX - fixedOrigin.x) > 0.5 ||
      Math.abs(originY - fixedOrigin.y) > 0.5
    ) {
      fixedOrigin = { x: originX, y: originY };
    }
  }

  $effect(() => {
    if (!popoverEl) return;
    // Measure after the current frame so any entrance transform/animation on
    // the dialog ancestor has settled, otherwise the rect can be captured
    // mid-animation and yield the wrong origin.
    measureOrigin();
    const raf = requestAnimationFrame(measureOrigin);
    return () => cancelAnimationFrame(raf);
  });

  // Derived CSS values
  let hueColour = $derived(`hsl(${hsva.h}, 100%, 50%)`);
  let opaqueRgba = $derived(hsvaToRgba({ ...hsva, a: 1 }));
  let currentRgba = $derived(hsvaToRgba(hsva));
  let gradThumbLeft = $derived(hsva.s * 100);
  let gradThumbTop = $derived((1 - hsva.v) * 100);
  let hueThumbLeft = $derived((hsva.h / 360) * 100);
  let alphaThumbLeft = $derived(hsva.a * 100);
</script>

<div
  bind:this={popoverEl}
  class="fixed z-[60] rounded-lg border border-border bg-card p-4 shadow-xl"
  style="top: {top - fixedOrigin.y}px; left: {left - fixedOrigin.x}px; width: {POPOVER_W}px;"
  role="dialog"
  aria-label="Colour picker"
>
  <!-- Saturation / Brightness gradient -->
  <div
    class="relative rounded-md overflow-hidden cursor-crosshair touch-none"
    style="width: {GRAD_W}px; height: {GRAD_H}px; background: {hueColour};"
    role="presentation"
    onpointerdown={grad.down}
    onpointermove={grad.move}
    onpointerup={grad.up}
  >
    <div class="absolute inset-0" style="background: linear-gradient(to right, #fff, transparent);"></div>
    <div class="absolute inset-0" style="background: linear-gradient(to top, #000, transparent);"></div>
    <div
      class="absolute w-3.5 h-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-[0_0_3px_rgba(0,0,0,0.6)] pointer-events-none"
      style="left: {gradThumbLeft}%; top: {gradThumbTop}%;"
    ></div>
  </div>

  <!-- Hue strip -->
  <div
    class="relative mt-3 rounded cursor-pointer touch-none"
    style="width: {GRAD_W}px; height: {STRIP_H}px; background: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00);"
    role="slider"
    tabindex="0"
    aria-label="Hue"
    aria-valuenow={Math.round(hsva.h)}
    aria-valuemin={0}
    aria-valuemax={360}
    onpointerdown={hue.down}
    onpointermove={hue.move}
    onpointerup={hue.up}
  >
    <div
      class="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-2.5 h-4 rounded-sm border-2 border-white shadow-[0_0_3px_rgba(0,0,0,0.6)] pointer-events-none"
      style="left: {hueThumbLeft}%;"
    ></div>
  </div>

  <!-- Alpha strip -->
  <div
    class="relative mt-2 rounded cursor-pointer touch-none"
    style="width: {GRAD_W}px; height: {STRIP_H}px;"
    role="slider"
    tabindex="0"
    aria-label="Alpha"
    aria-valuenow={Math.round(hsva.a * 100)}
    aria-valuemin={0}
    aria-valuemax={100}
    onpointerdown={alpha.down}
    onpointermove={alpha.move}
    onpointerup={alpha.up}
  >
    <!-- Checkerboard background -->
    <div
      class="absolute inset-0 rounded"
      style="background-image: repeating-conic-gradient(#555 0% 25%, #333 0% 50%); background-size: 8px 8px;"
    ></div>
    <!-- Alpha gradient overlay -->
    <div
      class="absolute inset-0 rounded"
      style="background: linear-gradient(to right, transparent, {opaqueRgba});"
    ></div>
    <div
      class="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-2.5 h-4 rounded-sm border-2 border-white shadow-[0_0_3px_rgba(0,0,0,0.6)] pointer-events-none"
      style="left: {alphaThumbLeft}%;"
    ></div>
  </div>

  <!-- Quick-pick swatches -->
  <div class="flex gap-1.5 mt-3">
    {#each PRESETS as preset}
      <button
        type="button"
        class="w-5 h-5 rounded border border-border hover:border-foreground transition-colors cursor-pointer"
        style="background-color: {preset};"
        onclick={() => pickPreset(preset)}
        aria-label="Pick {preset}"
      ></button>
    {/each}
  </div>

  <!-- Hex input + preview -->
  <div class="flex items-center gap-2 mt-3">
    <div
      class="w-7 h-7 rounded border border-border flex-shrink-0"
      style="background-color: {currentRgba};"
    ></div>
    <input
      type="text"
      value={hexInput}
      oninput={handleHexInput}
      class="flex-1 rounded border border-border bg-background px-2 py-1 text-sm text-foreground font-mono"
      spellcheck="false"
      aria-label="Hex colour value"
    />
  </div>
</div>
