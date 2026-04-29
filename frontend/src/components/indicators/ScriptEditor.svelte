<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { python } from '@codemirror/lang-python';
  import { EditorState } from '@codemirror/state';
  import {
    EditorView,
    keymap,
    lineNumbers,
    highlightActiveLineGutter,
    highlightActiveLine,
    drawSelection,
  } from '@codemirror/view';
  import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
  import { searchKeymap } from '@codemirror/search';
  import {
    bracketMatching,
    indentOnInput,
    syntaxHighlighting,
    HighlightStyle,
  } from '@codemirror/language';
  import { tags as t } from '@lezer/highlight';

  let {
    value = $bindable(''),
    onRun,
    onSave,
  }: {
    value: string;
    onRun?: () => void;
    onSave?: () => void;
  } = $props();

  let host = $state<HTMLDivElement | null>(null);
  let view: EditorView | null = null;
  let updatingFromOutside = false;

  // Tokyo-night-ish palette tuned to the app's existing chrome. Uses
  // CSS variables for the chrome (background, gutter) so the editor swaps
  // automatically with theme; syntax tokens use a fixed palette so Python
  // reads consistently in either theme.
  const highlight = HighlightStyle.define([
    { tag: t.keyword, color: '#c792ea', fontStyle: 'italic' },
    { tag: [t.name, t.deleted, t.character, t.macroName], color: '#e8e6f0' },
    { tag: [t.function(t.variableName), t.labelName], color: '#82aaff' },
    {
      tag: [t.color, t.constant(t.name), t.standard(t.name)],
      color: '#f78c6c',
    },
    { tag: [t.definition(t.name), t.separator], color: '#e8e6f0' },
    {
      tag: [t.typeName, t.className, t.number, t.changed, t.annotation, t.modifier, t.self, t.namespace],
      color: '#ffcb6b',
    },
    {
      tag: [t.operator, t.operatorKeyword, t.url, t.escape, t.regexp, t.link, t.special(t.string)],
      color: '#89ddff',
    },
    { tag: [t.meta, t.comment], color: '#637085', fontStyle: 'italic' },
    { tag: t.strong, fontWeight: 'bold' },
    { tag: t.emphasis, fontStyle: 'italic' },
    { tag: t.link, color: '#82aaff', textDecoration: 'underline' },
    { tag: t.heading, fontWeight: 'bold', color: '#82aaff' },
    { tag: [t.atom, t.bool, t.special(t.variableName)], color: '#f78c6c' },
    { tag: [t.processingInstruction, t.string, t.inserted], color: '#c3e88d' },
    { tag: t.invalid, color: '#ff5370' },
  ]);

  const editorTheme = EditorView.theme(
    {
      '&': {
        height: '100%',
        background: 'transparent',
        color: 'oklch(var(--foreground))',
        fontSize: '13px',
        fontFamily: '"Space Mono", ui-monospace, SFMono-Regular, monospace',
      },
      '.cm-scroller': {
        fontFamily: 'inherit',
        lineHeight: '1.55',
        padding: '14px 0 60px',
      },
      '.cm-content': {
        caretColor: 'oklch(var(--primary))',
        padding: '0',
      },
      '.cm-cursor, .cm-dropCursor': {
        borderLeft: '2px solid oklch(var(--primary))',
      },
      '&.cm-focused': { outline: 'none' },
      '&.cm-focused .cm-selectionBackground, ::selection, .cm-selectionBackground':
        {
          background:
            'color-mix(in oklab, oklch(var(--primary)) 22%, transparent) !important',
        },
      '.cm-gutters': {
        background: 'transparent',
        color: 'color-mix(in oklab, oklch(var(--foreground)) 28%, transparent)',
        border: 'none',
        borderRight:
          '1px dashed color-mix(in oklab, oklch(var(--border)) 90%, transparent)',
        paddingRight: '10px',
        paddingLeft: '14px',
        fontVariantNumeric: 'tabular-nums',
        userSelect: 'none',
      },
      '.cm-activeLineGutter': {
        background: 'transparent',
        color: 'oklch(var(--foreground))',
      },
      '.cm-activeLine': {
        background:
          'color-mix(in oklab, oklch(var(--foreground)) 4%, transparent)',
      },
      '.cm-lineNumbers .cm-gutterElement': { padding: '0 8px 0 0' },
      '.cm-matchingBracket': {
        background:
          'color-mix(in oklab, oklch(var(--primary)) 18%, transparent)',
        outline:
          '1px solid color-mix(in oklab, oklch(var(--primary)) 55%, transparent)',
      },
    },
    { dark: true },
  );

  const updateListener = EditorView.updateListener.of(u => {
    if (u.docChanged && !updatingFromOutside) {
      value = u.state.doc.toString();
    }
  });

  function makeState(doc: string): EditorState {
    return EditorState.create({
      doc,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightActiveLine(),
        history(),
        drawSelection(),
        bracketMatching(),
        indentOnInput(),
        syntaxHighlighting(highlight),
        python(),
        editorTheme,
        keymap.of([
          {
            key: 'Mod-Enter',
            run: () => {
              onRun?.();
              return true;
            },
          },
          {
            key: 'Mod-s',
            preventDefault: true,
            run: () => {
              onSave?.();
              return true;
            },
          },
          ...defaultKeymap,
          ...historyKeymap,
          ...searchKeymap,
        ]),
        updateListener,
      ],
    });
  }

  onMount(() => {
    if (!host) return;
    view = new EditorView({ state: makeState(value), parent: host });
  });

  onDestroy(() => {
    view?.destroy();
    view = null;
  });

  // Sync external value changes (e.g. opening a different script) into the editor.
  $effect(() => {
    const v = value;
    if (!view) return;
    if (view.state.doc.toString() === v) return;
    updatingFromOutside = true;
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: v },
    });
    updatingFromOutside = false;
  });
</script>

<div class="editor-shell">
  <div class="editor-grid" aria-hidden="true"></div>
  <div bind:this={host} class="editor-host"></div>
</div>

<style>
  .editor-shell {
    position: relative;
    height: 100%;
    width: 100%;
    overflow: hidden;
    background: color-mix(in oklab, oklch(var(--background)) 92%, black 8%);
  }
  :global(.light) .editor-shell {
    background: color-mix(in oklab, oklch(var(--background)) 96%, black 4%);
  }
  /* Subtle dot grid evokes engineering paper without competing with code. */
  .editor-grid {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: radial-gradient(
      color-mix(in oklab, oklch(var(--foreground)) 8%, transparent) 1px,
      transparent 1px
    );
    background-size: 22px 22px;
    background-position: 14px 14px;
    opacity: 0.45;
    mask-image: linear-gradient(180deg, black 0, black 70%, transparent);
  }
  .editor-host {
    position: absolute;
    inset: 0;
  }
  .editor-host :global(.cm-editor) {
    height: 100%;
  }
</style>
