# Shared config (frontend + backend)

JSON here is imported by:

- **Frontend:** Vite alias `@shared` → this folder (`marketPeriods.ts`, `marketIntervals.ts`, `Header.svelte`).
- **Backend:** `backend/market/shared_config.py` loads paths under `openTrade/shared/`.

Edit **`market_periods.json`** / **`market_intervals.json`** to change dropdowns, allowed API values, and Twelve Data interval mapping (`twelvedata` + `twelvedataNative`).

After changing period deltas, restart the API so `shared_config` reloads.
