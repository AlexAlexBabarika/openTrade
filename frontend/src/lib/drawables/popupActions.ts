import type { DrawableTool, PopupAction } from './types';

export const DEFAULT_POPUP_ACTIONS: PopupAction[] = [
  { id: 'settings', label: 'Settings' },
  { id: 'delete', label: 'Delete' },
];

export function resolvePopupActions(tool: DrawableTool): PopupAction[] {
  return tool.popupActions ?? DEFAULT_POPUP_ACTIONS;
}
