import type { DrawablesStoreApi } from './store.svelte';

/** Injected drawable commands for `LeftToolbar` (avoids importing the `drawables` singleton). */
export type DrawableToolbarCommands = {
  removeAllForSymbol(symbol: string): void;
};

export function toolbarCommandsFromStore(
  store: Pick<DrawablesStoreApi, 'removeAllForSymbol'>,
): DrawableToolbarCommands {
  return {
    removeAllForSymbol: symbol => store.removeAllForSymbol(symbol),
  };
}
