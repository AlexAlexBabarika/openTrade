export type SafeLocalStorageGetOptions = {
  /** If set, parse failures are logged (callers that expect silent null omit this). */
  warnLabel?: string;
};

export function safeLocalStorageGet<T>(
  key: string,
  options?: SafeLocalStorageGetOptions,
): T | null {
  if (typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch (err) {
    if (options?.warnLabel !== undefined) {
      console.warn(options.warnLabel, err);
    }
    return null;
  }
}

export function safeLocalStorageSet(key: string, value: unknown): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn(`[opentrade] Failed to persist ${key}`, e);
  }
}
