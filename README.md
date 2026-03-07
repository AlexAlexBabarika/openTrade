# OpenTrade

A TradingView-style web trading application with a **Python FastAPI backend** and **TypeScript frontend**. Data sources: **yfinance** and **CSV** (polars). Unified OHLCV schema, WebSocket streaming, and optional SMA indicator.

## Architecture

```
Browser (any modern browser)
   └── Vite-built SPA (TypeScript + Lightweight Charts)
          └── fetch / WebSocket
                 ⇄
         FastAPI Python Backend (Uvicorn)
            ├── yfinance loader
            ├── CSV loader (polars)
            ├── data normalizer
            └── WebSocket broadcaster
```

## Prerequisites

- **Python 3.11+** with venv recommended
- **Node.js 18+** and npm

## Quick Start

### One command (backend + frontend)

From the project root:

```bash
./run.sh              # start backend + Vite frontend (open http://localhost:5173)
./run.sh --install    # install pip + npm deps, then start
```

The script starts the FastAPI backend in the background and the frontend in the foreground; pressing Ctrl+C stops both.

### 1. Backend (standalone)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
export PYTHONPATH="${PWD}"
python run_backend.py
```

Server: **http://127.0.0.1:8000**

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### 2. Frontend (dev)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (ensure backend is running on 8000). The Vite dev server proxies `/data`, `/ws`, and `/health` to the backend automatically.

### 3. Production build

```bash
cd frontend && npm run build
python run_backend.py
```

FastAPI serves the built frontend from `frontend/dist/` as static files. The entire app is available at http://127.0.0.1:8000.

### 4. Docker

```bash
docker compose up --build    # everything on http://localhost:8000
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/data/yfinance/{symbol}` | OHLCV from yfinance (query: `period`, `interval`) |
| POST | `/data/csv` | Upload CSV (form: `file`, query: `symbol`) |
| POST | `/data/csv/preview` | Preview CSV columns and first rows (form: `file`, `max_rows`) |
| GET | `/data/indicators/sma` | Candles + SMA(period) for symbol |
| WS | `/ws/stream/{symbol}` | Stream OHLCV candles (uses cached data) |

## Unified OHLCV Schema

All data is normalized to:

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-01-01T15:30:00Z",
  "open": 123.45,
  "high": 130.12,
  "low": 120.10,
  "close": 128.99,
  "volume": 12345678
}
```

- Timestamps: UTC, ISO8601
- Column aliases: Date/Datetime/time -> `timestamp`; Open/o -> `open`; High/h -> `high`; Low/l -> `low`; Close/c -> `close`; Volume/v -> `volume`

## Project Layout

```
openTrade/
├── backend/
│   ├── app.py              # FastAPI app, routes, WebSocket, static file serving
│   ├── models.py           # Pydantic OHLCV models
│   ├── normalizer.py       # Column normalization, UTC timestamps
│   ├── cache.py            # In-memory OHLCV cache
│   ├── websocket.py        # WebSocket broadcaster
│   ├── indicators.py       # e.g. SMA
│   ├── data_sources/
│   │   ├── yfinance_loader.py
│   │   └── csv_loader.py   # polars, auto-detect columns
│   └── requirements.txt
├── frontend/
│   ├── src/                # TypeScript, chart, WebSocket client
│   ├── public/             # Static assets (fonts, etc.)
│   ├── index.html
│   ├── vite.config.ts      # Vite config with API proxy
│   └── package.json
├── run_backend.py          # Entry point for backend
├── run.sh                  # Start backend + frontend in one command
├── Dockerfile              # Multi-stage build (Node + Python)
├── docker-compose.yml      # Single-service compose
└── README.md
```

## Features

- **yfinance**: load by symbol with period/interval; cached for WebSocket.
- **CSV**: upload via POST; polars loads and auto-detects date/OHLCV columns; normalized and cached.
- **WebSocket**: `/ws/stream/{symbol}` streams cached candles progressively.
- **SMA**: GET `/data/indicators/sma?symbol=...&period=20` returns candles plus SMA(20).
- **CSV preview**: POST `/data/csv/preview` with file for column names and first rows.
- **Frontend**: symbol input, timeframe/interval, data source (yfinance/CSV), Load / Stream WS, candlestick + volume chart (Lightweight Charts), legend with price/volume/date, connection status, auto-reconnect, responsive resize.

## Deployment

**Option A — Single unit (recommended):** Build the frontend, then run the backend. FastAPI serves the SPA as static files.

```bash
cd frontend && npm run build && cd ..
python run_backend.py
```

**Option B — Split:** Deploy `frontend/dist/` to Vercel/Netlify/Cloudflare Pages. Deploy the Python backend to Railway/Render/Fly.io. Set `window.__API_BASE__` to the backend URL in the hosting config.

**Docker:** `docker compose up --build` runs everything on port 8000.

## Engineering Notes

- Backend is **independent** (run with `python run_backend.py` or `uvicorn backend.app:app`).
- No hardcoded CSV column names; normalization via `normalizer.py`.
- Pydantic for strict validation; type hints throughout.
- Async FastAPI; WebSocket streams data progressively.
- CORS is configured to allow all origins for development flexibility.
- Frontend uses no native APIs; runs in any modern browser.
