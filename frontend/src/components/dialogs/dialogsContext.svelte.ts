import { getContext, setContext } from 'svelte';
import type {
  PriorityConflict,
  StanceConflict,
  TickerPriority,
  TickerStance,
} from '$lib/features/market/tickers';
import type { TickerNote } from '$lib/features/notes/notes';

export type GroupDialogMode = 'add' | 'rename';

export type NoteDialogState = {
  mode: 'create' | 'edit';
  symbol: string;
  note?: TickerNote;
};

export type FlagConflictState =
  | {
      kind: 'priority';
      symbol: string;
      desired: TickerPriority;
      conflict: PriorityConflict;
    }
  | {
      kind: 'stance';
      symbol: string;
      desired: TickerStance;
      conflict: StanceConflict;
    };

export class AppDialogsState {
  groupDialogMode = $state<GroupDialogMode | null>(null);
  addSymbolDialogOpen = $state(false);
  noteDialogState = $state<NoteDialogState | null>(null);
  flagConflict = $state<FlagConflictState | null>(null);

  openAddGroup = (): void => {
    this.groupDialogMode = 'add';
  };
  openRenameGroup = (): void => {
    this.groupDialogMode = 'rename';
  };
  closeGroupDialog = (): void => {
    this.groupDialogMode = null;
  };

  openAddSymbol = (): void => {
    this.addSymbolDialogOpen = true;
  };
  setAddSymbolOpen = (v: boolean): void => {
    this.addSymbolDialogOpen = v;
  };

  openAddNote = (symbol: string): void => {
    this.noteDialogState = { mode: 'create', symbol };
  };
  openEditNote = (note: TickerNote): void => {
    this.noteDialogState = { mode: 'edit', symbol: note.symbol, note };
  };
  closeNoteDialog = (): void => {
    this.noteDialogState = null;
  };

  showFlagConflict = (state: FlagConflictState): void => {
    this.flagConflict = state;
  };
  clearFlagConflict = (): void => {
    this.flagConflict = null;
  };
}

const KEY = Symbol('appDialogs');

export function provideAppDialogs(state: AppDialogsState): void {
  setContext(KEY, state);
}

export function useAppDialogs(): AppDialogsState {
  const ctx = getContext<AppDialogsState | undefined>(KEY);
  if (!ctx) throw new Error('AppDialogs context not provided');
  return ctx;
}
