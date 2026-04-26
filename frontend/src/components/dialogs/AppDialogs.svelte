<script lang="ts">
  import TextPromptDialog from './TextPromptDialog.svelte';
  import SymbolSearchDialog from './SymbolSearchDialog.svelte';
  import PriorityConflictDialog from './PriorityConflictDialog.svelte';
  import NoteDialog from './NoteDialog.svelte';
  import { useAppDialogs } from './dialogsContext.svelte';
  import type { SymbolProviders } from '$lib/features/market/symbols';

  let {
    groupDialogInitial,
    groupDialogExistingNames,
    existingSymbols,
    onGroupDialogSubmit,
    onAddSymbolSubmit,
    onNoteSubmit,
    onResolveFlagConflictKeepExisting,
    onResolveFlagConflictSwitchGroup,
  }: {
    groupDialogInitial: string;
    groupDialogExistingNames: string[];
    existingSymbols: string[];
    onGroupDialogSubmit: (name: string) => void;
    onAddSymbolSubmit: (sym: string, providers: SymbolProviders | null) => void;
    onNoteSubmit: (title: string | undefined, body: string) => void;
    onResolveFlagConflictKeepExisting: () => void;
    onResolveFlagConflictSwitchGroup: (groupName: string) => void;
  } = $props();

  const dialogs = useAppDialogs();
</script>

<TextPromptDialog
  open={dialogs.groupDialogMode !== null}
  onopenchange={v => {
    if (!v) dialogs.closeGroupDialog();
  }}
  title={dialogs.groupDialogMode === 'rename' ? 'Rename group' : 'Add group'}
  placeholder="Group name"
  initialValue={groupDialogInitial}
  existingNames={groupDialogExistingNames}
  duplicateMessage="A group with this name already exists."
  onsubmit={onGroupDialogSubmit}
/>
<PriorityConflictDialog
  field={dialogs.flagConflict?.kind ?? 'priority'}
  open={dialogs.flagConflict !== null}
  onopenchange={v => {
    if (!v) dialogs.clearFlagConflict();
  }}
  conflict={dialogs.flagConflict
    ? {
        symbol: dialogs.flagConflict.conflict.symbol,
        existing:
          dialogs.flagConflict.kind === 'priority'
            ? dialogs.flagConflict.conflict.existingPriority
            : dialogs.flagConflict.conflict.existingStance,
        groups: dialogs.flagConflict.conflict.groups,
      }
    : null}
  onkeepexisting={onResolveFlagConflictKeepExisting}
  onswitchgroup={onResolveFlagConflictSwitchGroup}
/>
<SymbolSearchDialog
  open={dialogs.addSymbolDialogOpen}
  onopenchange={dialogs.setAddSymbolOpen}
  {existingSymbols}
  onsubmit={onAddSymbolSubmit}
/>
<NoteDialog
  open={dialogs.noteDialogState !== null}
  onopenchange={v => {
    if (!v) dialogs.closeNoteDialog();
  }}
  mode={dialogs.noteDialogState?.mode ?? 'create'}
  symbol={dialogs.noteDialogState?.symbol ?? ''}
  initialTitle={dialogs.noteDialogState?.note?.title ?? ''}
  initialBody={dialogs.noteDialogState?.note?.body ?? ''}
  onsubmit={onNoteSubmit}
/>
