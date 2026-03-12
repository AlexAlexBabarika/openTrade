import { get, writable } from 'svelte/store';
import {
  apiFetch,
  clearTokens,
  getAccessToken,
  readErrorMessage,
  setTokens,
} from './api';

export type AuthUser = {
  id: string;
  email: string | null;
};

type AuthSessionPayload = {
  access_token: string;
  refresh_token: string;
  expires_at: number | null;
  user: AuthUser;
};

type SignupPendingPayload = {
  message: string;
};

export type AuthState = {
  user: AuthUser | null;
  accessToken: string | null;
  loading: boolean;
  error: string | null;
};

const initialToken = getAccessToken();

export const authState = writable<AuthState>({
  user: null,
  accessToken: initialToken,
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
  setTokens(payload.access_token, payload.refresh_token);
  authState.set({
    user: payload.user,
    accessToken: payload.access_token,
    loading: false,
    error: null,
  });
}

function clearAuthState(): void {
  clearTokens();
  authState.set({
    user: null,
    accessToken: null,
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
    const response = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
    const payload = (await response.json()) as AuthSessionPayload;
    setAuthenticated(payload);
    return payload.user;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Login failed';
    setError(message);
    setLoading(false);
    throw error;
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
    throw error;
  }
}

export async function logout(): Promise<void> {
  const token = get(authState).accessToken;
  try {
    await apiFetch('/auth/logout', { method: 'POST' }, Boolean(token));
  } finally {
    clearAuthState();
  }
}

export async function fetchSession(): Promise<AuthUser | null> {
  const token = getAccessToken();
  if (!token) {
    clearAuthState();
    return null;
  }

  setLoading(true);
  setError(null);
  try {
    const response = await apiFetch('/auth/session', { method: 'GET' }, true);
    if (response.status === 401) {
      clearAuthState();
      return null;
    }
    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }
    const payload = (await response.json()) as { user: AuthUser };
    authState.set({
      user: payload.user,
      accessToken: token,
      loading: false,
      error: null,
    });
    return payload.user;
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to fetch session';
    setError(message);
    setLoading(false);
    throw error;
  }
}
