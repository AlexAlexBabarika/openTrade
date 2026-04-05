<script lang="ts">
  import { tick } from 'svelte';
  import CircleAlert from '@lucide/svelte/icons/circle-alert';
  import { Button } from '$lib/components/ui/button';
  import GlitchText from './GlitchText.svelte';

  let { message = $bindable<string | null>(null) }: { message: string | null } = $props();

  let dialogEl: HTMLDivElement | undefined = $state();

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

  function dismiss(): void {
    message = null;
  }

  function handleBackdropClick(e: MouseEvent): void {
    if (e.target === e.currentTarget) dismiss();
  }

  $effect(() => {
    if (!message) return;
    const onKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
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
    if (!message) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  });
</script>

{#if message}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    role="presentation"
    onclick={handleBackdropClick}
    onkeydown={(e) => {
      if (e.target !== e.currentTarget) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        dismiss();
      }
    }}
  >
    <div
      bind:this={dialogEl}
      class="relative w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="error-dialog-title"
      aria-describedby="error-dialog-desc"
    >
      <div class="mb-5 flex items-center justify-between gap-3">
        <h2 id="error-dialog-title" class="min-w-0 shrink text-lg font-semibold leading-none">
          <GlitchText text="Error" />
        </h2>
        <Button variant="destructive" class="shrink-0" onclick={dismiss}>Close</Button>
      </div>

      <div class="flex flex-col gap-4">
        <div
          class="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive flex gap-2 items-center"
        >
          <CircleAlert class="size-4 shrink-0" strokeWidth={2} aria-hidden="true" />
          <p id="error-dialog-desc" class="leading-relaxed">
            {message}
          </p>
        </div>
      </div>
    </div>
  </div>
{/if}
