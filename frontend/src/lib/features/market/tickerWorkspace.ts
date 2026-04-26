import { apiJson } from '$lib/core/api';
import type { TickerGroup, FlaggedPriority, FlaggedStance } from './tickers';
import {
  isDefaultTickerWorkspaceState,
  normalizeGroupsList,
  resolveSelectedGroupName,
} from './tickers';

export type TickerWorkspacePayload = {
  groups: TickerGroup[];
  selectedGroup: string;
  selectedPriority: FlaggedPriority | null;
  selectedStance: FlaggedStance | null;
};

export type TickerWorkspaceApiResponse = {
  workspace: TickerWorkspacePayload;
  from_database: boolean;
  updated_at: string | null;
};

export async function fetchTickerWorkspace(): Promise<TickerWorkspaceApiResponse> {
  return apiJson<TickerWorkspaceApiResponse>(
    '/user/ticker-workspace',
    { method: 'GET' },
    true,
  );
}

export async function putTickerWorkspace(
  workspace: TickerWorkspacePayload,
): Promise<TickerWorkspaceApiResponse> {
  return apiJson<TickerWorkspaceApiResponse>(
    '/user/ticker-workspace',
    {
      method: 'PUT',
      body: JSON.stringify(workspace),
    },
    true,
  );
}

export function buildTickerWorkspacePayload(
  groups: TickerGroup[],
  selectedGroupName: string,
  selectedPriority: FlaggedPriority | null,
  selectedStance: FlaggedStance | null,
): TickerWorkspacePayload {
  return {
    groups,
    selectedGroup: selectedGroupName,
    selectedPriority,
    selectedStance,
  };
}

export interface TickerWorkspaceState {
  groups: TickerGroup[];
  selectedGroupName: string;
  selectedPriority: FlaggedPriority | null;
  selectedStance: FlaggedStance | null;
}

export function workspacePayloadToAppState(
  w: TickerWorkspacePayload,
): TickerWorkspaceState {
  const groups = normalizeGroupsList(w.groups);
  return {
    groups,
    selectedGroupName: resolveSelectedGroupName(groups, w.selectedGroup),
    selectedPriority: w.selectedPriority,
    selectedStance: w.selectedStance,
  };
}

// Hydrate the workspace for a freshly-signed-in user. Returns the remote state
// to apply, or `null` when the local state was pushed up because the server had
// nothing yet.
export async function syncWorkspaceOnSignIn(
  current: TickerWorkspaceState,
): Promise<TickerWorkspaceState | null> {
  const res = await fetchTickerWorkspace();
  if (res.from_database) {
    return workspacePayloadToAppState(res.workspace);
  }
  if (
    !isDefaultTickerWorkspaceState(
      current.groups,
      current.selectedGroupName,
      current.selectedPriority,
      current.selectedStance,
    )
  ) {
    await putTickerWorkspace(
      buildTickerWorkspacePayload(
        current.groups,
        current.selectedGroupName,
        current.selectedPriority,
        current.selectedStance,
      ),
    );
  }
  return null;
}
