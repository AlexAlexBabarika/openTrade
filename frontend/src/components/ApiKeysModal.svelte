<script lang="ts">
  import { tick } from 'svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import * as Select from '$lib/components/ui/select';
  import {
    API_KEY_PROVIDERS,
    listApiKeys,
    createApiKey,
    updateApiKey,
    type ApiKeyProvider,
    type ApiKeyInfo,
  } from '$lib/api-keys';

  let {
    open = $bindable(false),
  }: {
    open: boolean;
  } = $props();

  let dialogEl: HTMLDivElement | undefined = $state();

  let selectedProvider = $state<ApiKeyProvider | undefined>(undefined);
  let apiKeyInput = $state('');
  let showKey = $state(false);
  let loading = $state(false);
  let fetchingKeys = $state(false);
  let error = $state<string | null>(null);
  let success = $state<string | null>(null);

  let existingKeys = $state<ApiKeyInfo[]>([]);

  let currentKeyInfo = $derived(
    selectedProvider
      ? existingKeys.find((k) => k.provider === selectedProvider) ?? null
      : null,
  );
  let hasExistingKey = $derived(currentKeyInfo !== null);
  let canSubmit = $derived(apiKeyInput.trim().length > 0 && !loading);

  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function getFocusableElements(container: HTMLElement): HTMLElement[] {
    return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
  }

  function trapFocus(e: KeyboardEvent) {
    if (e.key !== 'Tab' || !dialogEl) return;
    const target = e.target as Node;
    if (!dialogEl.contains(target)) return;
    const focusable = getFocusableElements(dialogEl);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  $effect(() => {
    if (!open) return;
    const onKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
      trapFocus(e);
    };
    window.addEventListener('keydown', onKeydown);
    tick().then(() => {
      const first = dialogEl && getFocusableElements(dialogEl)[0];
      first?.focus();
    });
    return () => window.removeEventListener('keydown', onKeydown);
  });

  $effect(() => {
    if (open) {
      loadExistingKeys();
    }
  });

  $effect(() => {
    if (selectedProvider !== undefined) {
      apiKeyInput = '';
      showKey = false;
      error = null;
      success = null;
    }
  });

  async function loadExistingKeys() {
    fetchingKeys = true;
    try {
      existingKeys = await listApiKeys();
    } catch {
      existingKeys = [];
    } finally {
      fetchingKeys = false;
    }
  }

  function reset() {
    selectedProvider = undefined;
    apiKeyInput = '';
    showKey = false;
    loading = false;
    fetchingKeys = false;
    error = null;
    success = null;
    existingKeys = [];
  }

  function close() {
    open = false;
    reset();
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  async function handleSave() {
    if (!selectedProvider || !apiKeyInput.trim()) return;
    loading = true;
    error = null;
    success = null;

    try {
      if (hasExistingKey) {
        await updateApiKey(selectedProvider, apiKeyInput.trim());
      } else {
        await createApiKey(selectedProvider, apiKeyInput.trim());
      }
      success = hasExistingKey ? 'Updated' : 'Saved';
      apiKeyInput = '';
      showKey = false;
      await loadExistingKeys();
      setTimeout(() => {
        success = null;
      }, 2000);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to save';
    } finally {
      loading = false;
    }
  }

  function providerLabel(value: string): string {
    return API_KEY_PROVIDERS.find((p) => p.value === value)?.label ?? value;
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    role="presentation"
    onclick={handleBackdropClick}
    onkeydown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        close();
      }
    }}
  >
    <div
      bind:this={dialogEl}
      class="relative w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg"
      role="dialog"
      aria-modal="true"
      aria-label="Manage API Keys"
    >
      <button
        type="button"
        class="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
        onclick={close}
        aria-label="Close"
      >
        &#x2715;
      </button>

      <h2 class="mb-5 text-lg font-semibold text-card-foreground">
        Manage API Keys
      </h2>

      <div class="flex flex-col gap-4">
        <!-- Provider select -->
        <div class="flex flex-col gap-1.5">
          <Select.Root
            type="single"
            bind:value={selectedProvider}
          >
            <Select.Trigger
              class="w-full"
              aria-label="Select API provider"
            >
              {#if selectedProvider}
                {providerLabel(selectedProvider)}
              {:else}
                <span class="text-muted-foreground">Select API provider</span>
              {/if}
            </Select.Trigger>
            <Select.Content>
              {#each API_KEY_PROVIDERS as provider}
                <Select.Item value={provider.value}>
                  <div class="flex items-center justify-between w-full gap-2">
                    <span>{provider.label}</span>
                    {#if existingKeys.find((k) => k.provider === provider.value)}
                      <span class="text-xs text-muted-foreground ml-2">configured</span>
                    {/if}
                  </div>
                </Select.Item>
              {/each}
            </Select.Content>
          </Select.Root>
        </div>

        <!-- Key input + action button -->
        <div class="flex flex-col gap-1.5">
          <div class="flex gap-2">
            <div class="relative flex-1">
              <Input
                type={showKey ? 'text' : 'password'}
                placeholder={selectedProvider
                  ? hasExistingKey
                    ? '••••••••••••••••'
                    : 'Enter API key'
                  : 'Select a provider first'}
                bind:value={apiKeyInput}
                disabled={!selectedProvider || loading}
                aria-label="API key"
                class="pr-10"
              />
              {#if selectedProvider}
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors text-xs select-none"
                  onclick={() => (showKey = !showKey)}
                  aria-label={showKey ? 'Hide API key' : 'Show API key'}
                  tabindex={-1}
                >
                  {showKey ? 'Hide' : 'Show'}
                </button>
              {/if}
            </div>

            <Button
              disabled={!canSubmit}
              onclick={handleSave}
              variant={hasExistingKey ? 'outline' : 'default'}
              class={hasExistingKey
                ? 'border-amber-500/50 text-amber-600 hover:bg-amber-500/10 hover:text-amber-600 dark:text-amber-400 dark:hover:text-amber-400 min-w-[80px]'
                : 'min-w-[80px]'}
              aria-label={hasExistingKey ? 'Update API key' : 'Save API key'}
            >
              {#if loading}
                <svg
                  class="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  ></path>
                </svg>
              {:else if success}
                <span class="text-emerald-500">✓ {success}</span>
              {:else if hasExistingKey}
                Update
              {:else}
                Save
              {/if}
            </Button>
          </div>

          {#if hasExistingKey && currentKeyInfo?.key_prefix}
            <p class="text-xs text-muted-foreground">
              Current key: <span class="font-mono">{currentKeyInfo.key_prefix}</span>
            </p>
          {/if}
        </div>

        <!-- Error / success messages -->
        {#if error}
          <div class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        {/if}

        <!-- Existing keys summary -->
        {#if existingKeys.length > 0}
          <div class="border-t border-border pt-3 mt-1">
            <p class="text-xs text-muted-foreground mb-2 font-medium">Configured keys</p>
            <div class="flex flex-col gap-1">
              {#each existingKeys as key}
                <div class="flex items-center justify-between text-sm">
                  <span class="text-card-foreground">{providerLabel(key.provider)}</span>
                  <span class="font-mono text-xs text-muted-foreground">
                    {key.key_prefix ?? '•••'}
                  </span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if fetchingKeys}
          <p class="text-xs text-muted-foreground text-center">Loading keys…</p>
        {/if}
      </div>
    </div>
  </div>
{/if}
