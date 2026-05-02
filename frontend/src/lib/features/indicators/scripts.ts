import { apiFetch, apiJson, readErrorMessage } from '$lib/core/api';
import type { MarketDataProviderValue } from '$lib/features/market/marketDataProviders';

export type ScriptOutputPoint = { time: number; value: number };

export type ScriptOutput =
  | {
      type: 'overlay';
      data: ScriptOutputPoint[];
      color: string | null;
      title: string;
      line_width: number;
      line_style: string;
    }
  | {
      type: 'pane';
      data: ScriptOutputPoint[];
      color: string | null;
      title: string;
      height: number | null;
      pane_id: string | null;
    }
  | {
      type: 'markers';
      data: { time: number }[];
      shape: string;
      position: string;
      color: string | null;
      text: string | null;
    }
  | { type: 'table'; columns: string[]; rows: unknown[][] }
  | { type: 'text'; text: string; level: 'info' | 'warn' | 'error' }
  | {
      type: 'histogram';
      data: { time: number; value: number; color?: string | null }[];
      pane_id: string | null;
      title: string;
    };

export type RunStatus = 'ok' | 'error' | 'timeout' | 'killed';

export type RunResult = {
  status: RunStatus;
  outputs: ScriptOutput[];
  stdout: string;
  stderr: string;
  elapsed_ms: number;
};

export type ScriptInfo = {
  id: string;
  name: string;
  code: string;
  created_at: string;
  updated_at: string;
};

export async function listScripts(): Promise<ScriptInfo[]> {
  const data = await apiJson<{ scripts: ScriptInfo[] }>('/scripts', {}, true);
  return data.scripts;
}

export function createScript(name: string, code: string): Promise<ScriptInfo> {
  return apiJson<ScriptInfo>(
    '/scripts',
    { method: 'POST', body: JSON.stringify({ name, code }) },
    true,
  );
}

export function updateScript(
  id: string,
  patch: { name?: string; code?: string },
): Promise<ScriptInfo> {
  return apiJson<ScriptInfo>(
    `/scripts/${id}`,
    { method: 'PUT', body: JSON.stringify(patch) },
    true,
  );
}

export async function deleteScript(id: string): Promise<void> {
  const res = await apiFetch(`/scripts/${id}`, { method: 'DELETE' }, true);
  if (!res.ok && res.status !== 404)
    throw new Error(await readErrorMessage(res));
}

export type ExecuteParams = {
  code?: string;
  script_id?: string;
  symbol: string;
  provider: MarketDataProviderValue;
  period: string;
  interval: string;
  timeout_s?: number;
};

export function executeScript(params: ExecuteParams): Promise<RunResult> {
  return apiJson<RunResult>(
    '/scripts/execute',
    { method: 'POST', body: JSON.stringify(params) },
    true,
  );
}
