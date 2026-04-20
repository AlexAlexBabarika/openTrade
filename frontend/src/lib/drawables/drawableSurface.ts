/** Chart shell → drawable overlay: pointer and keyboard routing. */
export type DrawableSurface = {
  handlePointerDown: (e: PointerEvent) => void;
  handlePointerMove: (e: PointerEvent) => void;
  handlePointerUp: (e: PointerEvent) => void;
  handleKeyDown: (e: KeyboardEvent) => void;
};
