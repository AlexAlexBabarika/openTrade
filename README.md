# OpenTrade

A TradingView-like desktop trading application with a **Python FastAPI backend**, **Electron + TypeScript frontend**, and **Tauri** wrapper. Data sources: **yfinance** and **CSV** (polars). Unified OHLCV schema, WebSocket streaming, and optional SMA indicator.

## Architecture

```
[Tauri Wrapper]
   └── Electron App (UI) / or Tauri webview
          └── WebSocket client
                 ⇄
         FastAPI Python Backend
            ├── yfinance loader
            ├── CSV loader (polars)
            ├── data normalizer
            └── websocket broadcaster
```

## Prerequisites

- **Python 3.11+** with venv recommended
- **Node.js 18+** and npm
- **Rust** (for Tauri; install from https://rustup.rs)
- **Tauri CLI** (optional): `cargo install tauri-cli`

## Quick Start

### One command (backend + frontend)

From the project root:

```bash
./run.sh              # start backend + Vite frontend (open http://localhost:5173)
./run.sh --install    # install pip + npm deps, then start
./run.sh --electron   # start backend + Electron (Vite + Electron window)
```

The script starts the FastAPI backend in the background and the frontend in the foreground; pressing Ctrl+C stops both.

### 1. Backend (standalone)

Backend can run independently for development or production.

```bash
cd openTrade
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
# From project root so `backend` is a package
export PYTHONPATH="${PWD}"
python run_backend.py
```

Server: **http://127.0.0.1:8000**

- API docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

### 2. Frontend (dev in browser or Electron)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (ensure backend is running on 8000).

**Electron (dev):**

```bash
cd frontend
npm run electron:dev
```

Starts Vite and then Electron; backend must be running separately.

### 3. Tauri (desktop app: backend + frontend)

Tauri spawns the Python backend and loads the frontend; it kills the backend on exit.

```bash
# From project root
cd openTrade
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
cd tauri
cargo tauri build
```

Run the built app from `tauri/target/release/` or:

```bash
cargo tauri dev
```

For `tauri dev`, the config starts the frontend dev server; start the backend in another terminal (`python run_backend.py`) or rely on Tauri to spawn it (Tauri spawns backend from `run_backend.py` when the app starts).

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
- Column aliases: Date/Datetime/time → `timestamp`; Open/o → `open`; High/h → `high`; Low/l → `low`; Close/c → `close`; Volume/v → `volume`

## Project Layout

```
openTrade/
├── backend/
│   ├── app.py              # FastAPI app, routes, WebSocket
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
│   ├── electron/           # Electron main & preload
│   ├── src/                # TS, chart, WebSocket client
│   ├── index.html
│   └── package.json
├── tauri/                  # Tauri 2 app (spawns backend, loads frontend)
│   ├── src/
│   └── tauri.conf.json
├── run_backend.py          # Entry point for backend (used by Tauri)
└── README.md
```

## Features

- **yfinance**: load by symbol with period/interval; cached for WebSocket.
- **CSV**: upload via POST; polars loads and auto-detects date/OHLCV columns; normalized and cached.
- **WebSocket**: `/ws/stream/{symbol}` streams cached candles progressively.
- **SMA**: GET `/data/indicators/sma?symbol=...&period=20` returns candles plus SMA(20).
- **CSV preview**: POST `/data/csv/preview` with file for column names and first rows.
- **Frontend**: symbol input, timeframe/interval, data source (yfinance/CSV), Load / Stream WS / SMA(20), candlestick chart (Lightweight Charts), connection status, auto-reconnect on disconnect.

## Engineering Notes

- Backend is **independent** (run with `python run_backend.py` or `uvicorn backend.app:app`).
- No hardcoded CSV column names; normalization via `normalizer.py`.
- Pydantic for strict validation; type hints throughout.
- Async FastAPI; WebSocket streams data progressively.
- Tauri runs from project root so `run_backend.py` and `backend` are found; Python must be on PATH.
