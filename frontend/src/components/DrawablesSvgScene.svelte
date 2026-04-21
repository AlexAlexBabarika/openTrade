<script lang="ts">
  import {
    getTool,
    previewPlacementRendererProps,
    type CoordMap,
    type Drawable,
    type PlacementMachine,
    type ScreenPoint,
  } from '$lib/features/drawables';
  import type { BundledDrawable } from '$lib/features/drawables/bundledDrawable';

  let {
    coordMap,
    items,
    computedData,
    selectedId,
    placement,
    onPatchGeometry,
    onSelectDrawable,
    onAnchorPoint,
  }: {
    coordMap: CoordMap;
    items: readonly BundledDrawable[];
    computedData: Map<string, unknown>;
    selectedId: string | null;
    placement: {
      type: string;
      machine: PlacementMachine<unknown>;
      preview: Drawable | null;
    } | null;
    onPatchGeometry: (id: string, geometry: unknown) => void;
    onSelectDrawable: (id: string) => void;
    onAnchorPoint: (id: string, pt: ScreenPoint | null) => void;
  } = $props();
</script>

<svg
  class="absolute inset-0 w-full h-full z-10 pointer-events-none"
  style="overflow: visible;"
>
  {#each items as d (d.id)}
    {@const tool = getTool(d.type)}
    {#if tool}
      {@const RendererCmp = tool.Renderer}
      <RendererCmp
        drawable={d}
        data={computedData.get(d.id)}
        selected={selectedId === d.id}
        {coordMap}
        onGeometryChange={geo => onPatchGeometry(d.id, geo)}
        onRequestSelect={() => onSelectDrawable(d.id)}
        onAnchorPoint={pt => onAnchorPoint(d.id, pt)}
      />
    {/if}
  {/each}

  {#if placement?.preview}
    {@const previewTool = getTool(placement.type)}
    {#if previewTool}
      {@const PreviewCmp = previewTool.Renderer}
      <PreviewCmp
        {...previewPlacementRendererProps({
          drawable: placement.preview,
          data: undefined,
          coordMap,
        })}
      />
    {/if}
  {/if}
</svg>
