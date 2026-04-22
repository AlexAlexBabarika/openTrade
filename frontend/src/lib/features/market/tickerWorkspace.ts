import { apiJson } from '$lib/core/api';
import type { TickerGroup, FlaggedPriority, FlaggedStance } from './tickers';
import { normalizeGroupsList, resolveSelectedGroupName } from './tickers';

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

export function workspacePayloadToAppState(w: TickerWorkspacePayload): {
  groups: TickerGroup[];
  selectedGroupName: string;
  selectedPriority: FlaggedPriority | null;
  selectedStance: FlaggedStance | null;
} {
  const groups = normalizeGroupsList(w.groups);
  return {
    groups,
    selectedGroupName: resolveSelectedGroupName(groups, w.selectedGroup),
    selectedPriority: w.selectedPriority,
    selectedStance: w.selectedStance,
  };
}
