import { API_BASE } from './config';

/**
 * In-memory access token. Never persisted to localStorage/sessionStorage
 * so it cannot be stolen by XSS reading storage APIs.
 * The refresh token lives in an HttpOnly cookie managed by the backend.
 */
let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

export function clearAccessToken(): void {
  _accessToken = null;
}

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  if (path.startsWith('/')) {
    return `${API_BASE}${path}`;
  }
  return `${API_BASE}/${path}`;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  withAuth = false,
): Promise<Response> {
  const url = resolveUrl(path);
  const headers = new Headers(init.headers ?? {});
  headers.set('Accept', 'application/json');

  const hasBody = init.body !== undefined && init.body !== null;
  if (
    hasBody &&
    !headers.has('Content-Type') &&
    !(init.body instanceof FormData)
  ) {
    headers.set('Content-Type', 'application/json');
  }

  if (withAuth) {
    const token = getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  return fetch(url, { ...init, headers });
}

export async function readErrorMessage(response: Response): Promise<string> {
  try {
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      if (typeof data?.detail === 'string') return data.detail;
      if (typeof data?.message === 'string') return data.message;
    }
    const text = await response.text();
    return text || `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}
