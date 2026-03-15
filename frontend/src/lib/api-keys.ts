import { apiFetch, readErrorMessage } from './api';

export const API_KEY_PROVIDERS = [
  { value: 'twelvedata', label: 'Twelve Data' },
  { value: 'alphavantage', label: 'Alpha Vantage' },
  { value: 'massive', label: 'Massive' },
] as const;

export type ApiKeyProvider = (typeof API_KEY_PROVIDERS)[number]['value'];

export type ApiKeyInfo = {
  id: string;
  provider: ApiKeyProvider;
  key_prefix: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export async function listApiKeys(): Promise<ApiKeyInfo[]> {
  const res = await apiFetch('/user/api-keys', {}, true);
  if (!res.ok) throw new Error(await readErrorMessage(res));
  const data = (await res.json()) as { keys: ApiKeyInfo[] };
  return data.keys;
}

export async function createApiKey(
  provider: ApiKeyProvider,
  apiKey: string,
): Promise<ApiKeyInfo> {
  const res = await apiFetch(
    '/user/api-keys',
    {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey }),
    },
    true,
  );
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return (await res.json()) as ApiKeyInfo;
}

export async function updateApiKey(
  provider: ApiKeyProvider,
  apiKey: string,
): Promise<ApiKeyInfo> {
  const res = await apiFetch(
    `/user/api-keys/${provider}`,
    {
      method: 'PUT',
      body: JSON.stringify({ api_key: apiKey }),
    },
    true,
  );
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return (await res.json()) as ApiKeyInfo;
}

export async function deleteApiKey(provider: ApiKeyProvider): Promise<void> {
  const res = await apiFetch(
    `/user/api-keys/${provider}`,
    { method: 'DELETE' },
    true,
  );
  if (!res.ok) throw new Error(await readErrorMessage(res));
}
