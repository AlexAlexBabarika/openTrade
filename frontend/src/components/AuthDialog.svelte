<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { login, signup } from '$lib/auth';

  let {
    open = $bindable(false),
  }: {
    open: boolean;
  } = $props();

  let mode = $state<'login' | 'signup'>('login');
  let email = $state('');
  let password = $state('');
  let loading = $state(false);
  let error = $state<string | null>(null);
  let info = $state<string | null>(null);

  function reset() {
    email = '';
    password = '';
    loading = false;
    error = null;
    info = null;
  }

  function close() {
    open = false;
    reset();
  }

  function switchMode() {
    mode = mode === 'login' ? 'signup' : 'login';
    error = null;
    info = null;
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (!email.trim() || !password) return;

    loading = true;
    error = null;
    info = null;

    try {
      if (mode === 'login') {
        await login(email.trim(), password);
        close();
      } else {
        const result = await signup(email.trim(), password);
        if (result.pendingConfirmation) {
          info = result.message ?? 'Check your email to confirm, then log in.';
          mode = 'login';
          password = '';
        } else {
          close();
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Something went wrong';
    } finally {
      loading = false;
    }
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  >
    <div
      class="relative w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-lg"
      role="dialog"
      aria-modal="true"
      aria-label={mode === 'login' ? 'Sign in' : 'Create account'}
    >
      <h2 class="mb-4 text-lg font-semibold text-card-foreground">
        {mode === 'login' ? 'Sign in' : 'Create account'}
      </h2>

      {#if error}
        <div class="mb-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      {/if}

      {#if info}
        <div class="mb-3 rounded-md bg-primary/10 px-3 py-2 text-sm text-primary">
          {info}
        </div>
      {/if}

      <form onsubmit={handleSubmit} class="flex flex-col gap-4">
        <div class="flex flex-col gap-1.5">
          <Label for="auth-email">Email</Label>
          <Input
            id="auth-email"
            type="email"
            placeholder="you@example.com"
            bind:value={email}
            disabled={loading}
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <Label for="auth-password">Password</Label>
          <Input
            id="auth-password"
            type="password"
            placeholder={mode === 'signup' ? '6+ characters' : ''}
            bind:value={password}
            disabled={loading}
          />
        </div>

        <Button type="submit" disabled={loading || !email.trim() || !password}>
          {#if loading}
            {mode === 'login' ? 'Signing in...' : 'Creating account...'}
          {:else}
            {mode === 'login' ? 'Sign in' : 'Create account'}
          {/if}
        </Button>
      </form>

      <div class="mt-4 text-center text-sm text-muted-foreground">
        {#if mode === 'login'}
          Don't have an account?
          <button
            type="button"
            class="underline text-primary hover:text-primary/80"
            onclick={switchMode}
          >
            Sign up
          </button>
        {:else}
          Already have an account?
          <button
            type="button"
            class="underline text-primary hover:text-primary/80"
            onclick={switchMode}
          >
            Sign in
          </button>
        {/if}
      </div>

      <button
        type="button"
        class="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
        onclick={close}
        aria-label="Close"
      >
        &#x2715;
      </button>
    </div>
  </div>
{/if}
