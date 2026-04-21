import { writable } from 'svelte/store';
import {
  apiFetch,
  apiJson,
  clearAccessToken,
  getAccessToken,
  readErrorMessage,
  setAccessToken,
} from '$lib/core/api';

export type AuthUser = {
  id: string;
  email: string | null;
};

type AuthSessionPayload = {
  access_token: string;
  expires_at: number | null;
  user: AuthUser;
};

type SignupPendingPayload = {
  message: string;
};

export type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
};

export const authState = writable<AuthState>({
  user: null,
  loading: false,
  error: null,
});

function setLoading(loading: boolean): void {
  authState.update(prev => ({ ...prev, loading }));
}

function setError(error: string | null): void {
  authState.update(prev => ({ ...prev, error }));
}

function setAuthenticated(payload: AuthSessionPayload): void {
  setAccessToken(payload.access_token);
  authState.set({
    user: payload.user,
    loading: false,
    error: null,
  });
}

function clearAuthState(): void {
  clearAccessToken();
  authState.set({
    user: null,
    loading: false,
    error: null,
  });
}

export async function login(
  email: string,
  password: string,
): Promise<AuthUser> {
  setLoading(true);
  setError(null);
  try {
    const payload = await apiJson<AuthSessionPayload>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setAuthenticated(payload);
    return payload.user;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Login failed';
    setError(message);
    setLoading(false);
    throw new Error(message);
  }
}

export async function signup(
  email: string,
  password: string,
): Promise<{
  user: AuthUser | null;
  pendingConfirmation: boolean;
  message?: string;
}> {
  setLoading(true);
  setError(null);
  try {
    const response = await apiFetch('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    if (response.status === 202) {
      const payload = (await response.json()) as SignupPendingPayload;
      authState.update(prev => ({ ...prev, loading: false }));
      return {
        user: null,
        pendingConfirmation: true,
        message: payload.message,
      };
    }

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const payload = (await response.json()) as AuthSessionPayload;
    setAuthenticated(payload);
    return { user: payload.user, pendingConfirmation: false };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Signup failed';
    setError(message);
    setLoading(false);
    throw new Error(message);
  }
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  try {
    await apiFetch('/auth/logout', { method: 'POST' }, Boolean(token));
  } finally {
    clearAuthState();
  }
}

/**
 * Attempt to restore a session using the HttpOnly refresh_token cookie.
 * Called on app startup / page reload. The cookie is sent automatically
 * by the browser (same-origin), so no JS token handling is needed.
 */
export async function fetchSession(): Promise<AuthUser | null> {
  setLoading(true);
  setError(null);
  try {
    const response = await apiFetch('/auth/refresh', { method: 'POST' });
    if (response.status === 401) {
      clearAuthState();
      return null;
    }
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
    const payload = (await response.json()) as AuthSessionPayload;
    setAuthenticated(payload);
    return payload.user;
  } catch (error) {
    clearAuthState();
    return null;
  }
}
