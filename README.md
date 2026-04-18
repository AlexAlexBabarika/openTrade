# openTrade

A fully functional trading charter web-app created for financial instrument analysis, including: shares, crypto, ETFs, etc. using multiple data-sources.

## Core functionality

   1. Load OHLCV data (Open, High, Low, Close, Volume) from different sources:
      - YFinance — Yahoo Finance (stocks, ETFs, cryptocurrencies)
      - Binance — cryptocurrency pairs from Binance exchange
      - Twelve Data API — professional financial data
      - CSV files — upload custom data
   2. Display interactive charts:
      - Candlestick (Japanese candles)
      - Line charts
      - Volume histograms
      - Legend with price, date, and volume

---

## Architecture and Technologies

### **Backend** (Python/FastAPI)

  FastAPI server (asynchronous)

  ├── REST API for data loading

  ├── WebSocket for direct streaming

  ├── Authentication via Supabase

  ├── API key encryption

  ├── In-memory data caching

  └── Data providers:

      ├── yfinance (Python library)

      ├── python-binance (Binance API client)

      ├── requests (HTTP for Twelve Data)

      └── pandas (CSV parsing)

### **Frontend** (Svelte 5 / TypeScript)

  Svelte 5 components (SPA)

  ├── App.svelte — main container

  ├── Header.svelte — control panel

  ├── Chart.svelte — interactive chart (lightweight-charts)

  ├── AuthDialog.svelte — login/signup

  ├── ApiKeysModal.svelte — key management

  └── lib/ — utilities

      ├── api.ts — HTTP client

      ├── auth.ts — authentication state management

      ├── ws.ts — WebSocket client with auto-reconnect

      └── chart.ts — chart configuration

### **Database** (Supabase/PostgreSQL)

  Tables:

  ├── auth.users — built-in Supabase authentication

  ├── profiles — user profiles (auto-created)

  ├── api_keys — encrypted API keys

  ├── api_key_audit_log — operation history with keys

  ├── symbol — 50 samples of stocks, crypto, forex

  └── asset_type — enum of asset types

## Requirements for full functionality

1. *Supabase account*

   - database, auth and key encryption.

2. *API keys*

   - Twelve data for professional data.
   - Binance for crypto.

## TODO'S

### Architecture & Infrastructure

1. **Redis/External Cache** — Replace in-memory cache with Redis for multi-worker support. Current cache is per-process; if running multiple uvicorn workers, each has its own cache causing redundant API calls and inconsistent data.

2. **Persistent Data Storage** — Store historical OHLCV data in Supabase/PostgreSQL with TimescaleDB extension. Currently all market data is fetched fresh every time and only cached in memory (lost on restart).

3. **Distributed Rate Limiting** — Current rate limiter is per-process. Use Redis-based sliding window (or token bucket) for accurate rate limiting across multiple workers/containers.

4. **Background Task Queue** — Add Celery/ARQ for long-running data fetches. Currently all provider calls block a thread pool thread; heavy loads could exhaust the pool.

5. **API Versioning** — Add `/api/v1/` prefix for proper versioning. The deprecated `/data/yfinance/{symbol}` endpoint shows versioning is already a concern.

6. **Environment Configuration** — Use pydantic-settings for validated, typed configuration instead of scattered `os.environ.get()` calls.

7. **Structured Logging** — Add JSON structured logging with correlation IDs for request tracing.

8. **Health Check Enhancement** — The `/health` endpoint should check Supabase connectivity, not just return `{"status": "ok"}`.

### Security

9. **CORS Restriction** — `allow_origins=["*"]` is too permissive for production. Should be configurable via env var with specific allowed origins.

10. **WebSocket Authentication** — WebSocket endpoints have no auth. Anyone can connect and replay cached data. Add token-based auth on WS handshake.

11. **CSRF Protection** — The refresh token cookie uses `SameSite=lax` which helps, but explicit CSRF tokens would add defense-in-depth for state-changing operations.

12. **Input Sanitization** — Symbol inputs are `.strip()`ped but not validated against injection patterns. Add regex validation for symbol format.

13. **API Key Rotation Reminders** — Track key age and warn users when keys are old (e.g., >90 days).

### Data & Market Features

14. **Technical Indicators** — Add SMA, EMA, RSI, MACD, Bollinger Bands. The frontend already has `smaUrl()` in config.ts suggesting this was planned. Could be computed server-side or client-side using lightweight libraries.

15. **Real-Time Streaming** — Current WebSocket only replays cached data. Implement true real-time streaming using Binance WebSocket API (`wss://stream.binance.com`) or Twelve Data WebSocket for live price updates.

16. **Multi-Chart / Comparison** — Allow viewing multiple symbols side-by-side or overlaid on the same chart for comparison.

17. **Drawing Tools** — Add trendlines, horizontal lines, Fibonacci retracement, support/resistance zones on the chart using lightweight-charts markers and lines.

18. **Watchlists** — Let users save favorite symbols as watchlists, persisted in Supabase. The seed data already has 50 symbols ready to use.

19. **Symbol Search / Autocomplete** — The `symbol` table from seed.sql isn't currently used. Build a search endpoint that queries it for symbol lookup with autocomplete.

20. **Asset Type Filtering** — Use the `asset_type` enum to let users filter symbols by category (stocks, crypto, forex, etc.).

21. **Chart Annotations / Notes** — Allow users to add text annotations at specific timestamps, persisted in Supabase.

22. **Price Alerts** — Let users set price alerts (above/below threshold). Could use WebSocket or push notifications.

23. **Export Data** — Add CSV/JSON export of displayed chart data.

24. **More Data Providers** — Add Alpha Vantage (already in API key enum but no loader), CoinGecko, Polygon.io, Interactive Brokers.

### Frontend UI/UX

25. **Dark/Light Theme Toggle** — The chart already syncs themes via MutationObserver, but there's no visible toggle button. Add one to the Header.

26. **Responsive / Mobile Layout** — The Header wraps on small screens but isn't optimized for mobile. Add a hamburger menu or collapsible toolbar.

27. **Chart Type Selector** — Allow switching between candlestick, line, area, and bar chart types.

28. **Fullscreen Chart Mode** — Toggle to hide the header and maximize chart area.

29. **Keyboard Shortcuts** — Add hotkeys for common actions (e.g., R to reload, S to stream, number keys for periods).

30. **Loading Skeleton** — Replace the simple spinner with skeleton/shimmer loading states for better perceived performance.

31. **Toast Notifications** — Replace the full-screen error modal with less intrusive toast notifications for non-critical errors. Keep the modal for critical/blocking errors only.

32. **Persistent Settings** — Save user preferences (default symbol, period, interval, provider, autoRefresh) to localStorage or Supabase profiles.

33. **Chart Timezone Selection** — Everything is UTC. Add option to display in user's local timezone.

34. **Volume Profile** — Add volume-at-price histogram on the price axis.

35. **Minimap/Overview** — Add a small overview chart below the main chart for quick navigation of long time ranges.

### Testing & Quality

36. **Backend Tests** — No Python tests exist. Add pytest tests for:
    - Normalizer edge cases (various date formats, missing columns)
    - Encryption round-trip
    - Rate limiter behavior
    - Route integration tests with TestClient

37. **Frontend Tests** — vitest is configured but no test files exist. Add tests for:
    - `api.ts` (URL resolution, error parsing)
    - `auth.ts` (login/logout flow)
    - `chartAdapters.ts` (data conversion)
    - Component smoke tests

38. **E2E Tests** — Add Playwright tests for critical user flows (load chart, sign in, manage API keys).

39. **API Documentation** — FastAPI auto-generates OpenAPI docs but they could be enhanced with more examples and response schemas.

### DevOps & Operations

40. **Monitoring / Observability** — Add Prometheus metrics (request latency, cache hit rate, provider error rate) and Grafana dashboards.

41. **Docker Compose Enhancement** — Add Redis, Supabase, and optional PgAdmin services to docker-compose for full local development.

42. **CD Pipeline** — Add automated deployment workflow (e.g., to Railway, Fly.io, or AWS).

43. **Database Migrations CI** — Run Supabase migrations in CI to catch schema issues early.

### Performance

44. **Response Compression** — Add gzip/brotli middleware for API responses (large candle arrays can be significantly compressed).

45. **Candle Data Pagination** — For very long periods, return paginated candle data instead of one large payload.

46. **WebSocket Binary Protocol** — Use MessagePack or Protocol Buffers instead of JSON for WebSocket messages to reduce bandwidth.

47. **Frontend Code Splitting** — Lazy-load the chart library and auth dialogs to reduce initial bundle size.

48. **Service Worker / PWA** — Cache static assets and enable offline viewing of previously loaded charts.

### Business Features

49. **Portfolio Tracking** — Let users add holdings (symbol + quantity + cost basis) and track portfolio value over time.

50. **Paper Trading** — Simulated trading with virtual funds using real-time data.

51. **Backtesting Engine** — Let users define simple trading strategies (e.g., moving average crossover) and backtest them against historical data.

52. **News Integration** — Show relevant news headlines alongside chart data (via NewsAPI or similar).

53. **Social Features** — Share chart snapshots or trade ideas with other users.

54. **Multi-Language Support** — i18n for the frontend to support non-English users.
