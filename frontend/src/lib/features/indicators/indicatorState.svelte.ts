import {
  createScript,
  deleteScript,
  executeScript,
  listScripts,
  updateScript,
  type ExecuteParams,
  type RunResult,
  type ScriptInfo,
} from './scripts';

const STARTER_CODE = `# A simple SMA(20) overlay.
# 'price' is the close series; 'display' is the result collector.
sma = price.rolling(20).mean()
display.line(sma, title="SMA20")
`;

export class IndicatorState {
  scripts = $state<ScriptInfo[]>([]);
  loading = $state(false);
  loadError = $state<string | null>(null);

  activeId = $state<string | null>(null);
  draftName = $state('Untitled');
  draftCode = $state(STARTER_CODE);
  dirty = $state(false);

  isRunning = $state(false);
  isSaving = $state(false);
  runError = $state<string | null>(null);
  saveError = $state<string | null>(null);
  lastResult = $state<RunResult | null>(null);

  active = $derived.by(() =>
    this.activeId
      ? (this.scripts.find(s => s.id === this.activeId) ?? null)
      : null,
  );

  async refresh(): Promise<void> {
    this.loading = true;
    this.loadError = null;
    try {
      this.scripts = await listScripts();
    } catch (err) {
      this.loadError =
        err instanceof Error ? err.message : 'Failed to load scripts';
    } finally {
      this.loading = false;
    }
  }

  newDraft(): void {
    this.activeId = null;
    this.draftName = 'Untitled';
    this.draftCode = STARTER_CODE;
    this.dirty = false;
    this.runError = null;
    this.saveError = null;
    this.lastResult = null;
  }

  openScript(id: string): void {
    const s = this.scripts.find(x => x.id === id);
    if (!s) return;
    this.activeId = id;
    this.draftName = s.name;
    this.draftCode = s.code;
    this.dirty = false;
    this.runError = null;
    this.saveError = null;
    this.lastResult = null;
  }

  setName(name: string): void {
    if (this.draftName === name) return;
    this.draftName = name;
    this.dirty = true;
  }

  setCode(code: string): void {
    if (this.draftCode === code) return;
    this.draftCode = code;
    this.dirty = true;
  }

  async save(): Promise<ScriptInfo | null> {
    const name = this.draftName.trim();
    if (!name) {
      this.saveError = 'Name is required';
      return null;
    }
    this.isSaving = true;
    this.saveError = null;
    try {
      let saved: ScriptInfo;
      if (this.activeId) {
        saved = await updateScript(this.activeId, {
          name,
          code: this.draftCode,
        });
      } else {
        saved = await createScript(name, this.draftCode);
      }
      const idx = this.scripts.findIndex(s => s.id === saved.id);
      if (idx >= 0) this.scripts[idx] = saved;
      else this.scripts = [saved, ...this.scripts];
      this.activeId = saved.id;
      this.dirty = false;
      return saved;
    } catch (err) {
      this.saveError = err instanceof Error ? err.message : 'Failed to save';
      return null;
    } finally {
      this.isSaving = false;
    }
  }

  async delete(id: string): Promise<void> {
    await deleteScript(id);
    this.scripts = this.scripts.filter(s => s.id !== id);
    if (this.activeId === id) this.newDraft();
  }

  async run(
    ctx: Omit<ExecuteParams, 'code' | 'script_id'>,
  ): Promise<RunResult | null> {
    this.isRunning = true;
    this.runError = null;
    this.lastResult = null;
    try {
      const params: ExecuteParams = { ...ctx };
      if (this.activeId && !this.dirty) {
        params.script_id = this.activeId;
      } else {
        params.code = this.draftCode;
      }
      const res = await executeScript(params);
      this.lastResult = res;
      return res;
    } catch (err) {
      this.runError = err instanceof Error ? err.message : 'Run failed';
      return null;
    } finally {
      this.isRunning = false;
    }
  }
}
